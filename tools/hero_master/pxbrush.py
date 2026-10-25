"""pxbrush — растровый «художественный» движок для мастер-спрайтов Rogalik.

Отличие от прежнего формового рендерера (`tools/res_study/form_render.py`):

* ТАМ: SDF-формы складывались, а *свет вычислялся* из поля нормалей
  (цилиндрическая модель), затем рампы заливались автоматически. Художник
  задавал только геометрию, тон получался сам — отсюда «полосы» и отсутствие
  лепки формы.
* ЗДЕСЬ: каждый мазок (stroke) — это отдельное решение художника:
  траектория, толщина, сужение, МАТЕРИАЛ и ЯВНО НАЗНАЧЕННЫЙ ТОН рампы.
  Рисунок собирается слоями, как кистью: масса в тени → средний тон →
  свет → блик → швы и контур. Свет не вычисляется: он расставляется.

Технические свойства, важные для пиксель-арта:

* покрытие бинарное (0 или 255 alpha) — сглаживания нет по построению;
* координаты задаются в «единицах высоты фигуры» (доли H), поэтому одна и та же
  конструкция даёт согласованные спрайты разной высоты (96/48) и разные позы;
* палитра — фиксированные рампы материалов со сдвигом оттенка, не более 40 цветов.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

# --------------------------------------------------------------------------
# Палитра: рампы материалов (тёмный → светлый). Сдвиг оттенка внутри рампы
# сделан руками: в тени кожа уходит в холодный багровый, в свету — в тёплый.
# --------------------------------------------------------------------------

RAMPS: dict[str, list[str]] = {
    "skin": ["#2A1719", "#5A332C", "#8D5A46", "#B98163", "#D9A884"],
    "hair": ["#1B1209", "#342310", "#513417", "#714A27", "#9A6C3E"],
    "cloth": ["#141319", "#21202A", "#2F2E3A", "#403F4D", "#555463"],
    "red": ["#2B0A0D", "#521316", "#7F1F1C", "#AA3325", "#D2542F"],
    "wrap": ["#171310", "#2B221A", "#43352A", "#5C4838"],
    "dark": ["#0C080A", "#171219", "#251E27"],
    "rim": ["#7F8EA8", "#A3B0C4"],
}

# Служебные цвета (не рампы): контур и свечение.
OUTLINE = "#120C10"
TRANSPARENT = -1


def hex_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def build_lut() -> tuple[dict[str, int], list[tuple[int, int, int]]]:
    """Плоский список цветов; тон материала адресуется как (mat, index)."""
    palette: list[tuple[int, int, int]] = []
    index: dict[str, int] = {}
    for mat, ramp in RAMPS.items():
        for step, hx in enumerate(ramp):
            index[f"{mat}{step}"] = len(palette)
            palette.append(hex_rgb(hx))
    index["outline"] = len(palette)
    palette.append(hex_rgb(OUTLINE))
    return index, palette


LUT, PALETTE = build_lut()


def T(mat: str, step: int) -> int:
    """Индекс цвета: материал + номер тона в рампе (с зажимом в границы)."""
    ramp = RAMPS[mat]
    step = max(0, min(len(ramp) - 1, int(step)))
    return LUT[f"{mat}{step}"]


def OUTLINE_TONE() -> int:
    """Индекс цвета контура (не рампа: один служебный цвет)."""
    return LUT["outline"]


# --------------------------------------------------------------------------
# Геометрия
# --------------------------------------------------------------------------


def _polyline_distance(
    xs: np.ndarray, ys: np.ndarray,
    points: list[tuple[float, float]], widths: list[float],
) -> np.ndarray:
    """min по сегментам (расстояние - локальный радиус). Отрицательно = внутри."""
    best = np.full(xs.shape, 1e9, dtype=np.float64)
    count = len(points)
    for i in range(count - 1):
        ax, ay = points[i]
        bx, by = points[i + 1]
        w0, w1 = widths[i], widths[i + 1]
        vx, vy = bx - ax, by - ay
        length2 = vx * vx + vy * vy
        if length2 == 0.0:
            t = np.zeros(xs.shape)
            dist = np.hypot(xs - ax, ys - ay)
        else:
            t = np.clip(((xs - ax) * vx + (ys - ay) * vy) / length2, 0.0, 1.0)
            px = ax + t * vx
            py = ay + t * vy
            dist = np.hypot(xs - px, ys - py)
        field = dist - (w0 + (w1 - w0) * t)
        best = np.minimum(best, field)
    return best


def _even_odd(xs: np.ndarray, ys: np.ndarray, poly: list[tuple[float, float]]) -> np.ndarray:
    """Заливка многоугольника (правило чётности) по центрам пикселей."""
    inside = np.zeros(xs.shape, dtype=bool)
    count = len(poly)
    for i in range(count):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % count]
        if ay == by:
            continue
        cond = ((ay > ys) != (by > ys))
        with np.errstate(divide="ignore", invalid="ignore"):
            xcross = (bx - ax) * (ys - ay) / (by - ay) + ax
        inside ^= cond & (xs < xcross)
    return inside


# --------------------------------------------------------------------------
# Холст
# --------------------------------------------------------------------------


@dataclass
class Canvas:
    """Индексный холст: -1 = прозрачно, остальное — индекс палитры."""

    width: int
    height: int
    scale: float                      # высота фигуры в пикселях (H)
    canvas_x0: float = 0.0            # мировой x левого края холста
    canvas_y0: float = 0.0            # мировой y верхнего края холста
    grid: np.ndarray = field(init=False)
    strokes: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.grid = np.full((self.height, self.width), TRANSPARENT, dtype=np.int16)

    # -- координаты -------------------------------------------------------
    @property
    def cx(self) -> float:
        """Центр фигуры по X в пикселях холста."""
        return self.width * 0.5

    def px(self, xu: float) -> float:
        """x в единицах H (0 = центр фигуры) → пиксель холста."""
        return self.cx + xu * self.scale

    def py(self, yu: float) -> float:
        """y в единицах H (0 = верх фигуры) → пиксель холста."""
        return yu * self.scale

    def _axes(self, pad: int = 0) -> tuple[np.ndarray, np.ndarray]:
        ys, xs = np.mgrid[0:self.height, 0:self.width]
        return xs.astype(np.float64), ys.astype(np.float64)

    # -- примитивы --------------------------------------------------------
    def stroke(
        self,
        points: list[tuple[float, float]],
        width: float | tuple[float, float] | list[float],
        tone: int,
        material: str = "skin",
        only_over: int | None = None,
    ) -> None:
        """Мазок по траектории: толщина задаётся в пикселях.

        points — список (xu, yu) в единицах H, thickness — пиксели (число или
        список длины len(points), позволяющий сужать мазок к концу).
        only_over — рисовать только поверх уже закрашенных пикселей
        (так делаются блики и швы, не выходящие за силуэт).
        """
        xs, ys = self._axes()
        pts = [(self.px(x), self.py(y)) for x, y in points]
        if isinstance(width, (int, float)):
            widths = [float(width) * 0.5] * len(pts)
        else:
            widths = [float(w) * 0.5 for w in width]
        field = _polyline_distance(xs, ys, pts, widths)
        mask = field < 0.0
        if only_over is not None and only_over >= 0:
            mask &= self.grid >= 0
        self.grid[mask] = tone
        self.strokes += 1

    def blob(
        self,
        center: tuple[float, float],
        rx: float,
        ry: float,
        tone: int,
        rot: float = 0.0,
        only_over: int | None = None,
    ) -> None:
        """Эллипс: rx, ry — полуоси в пикселях."""
        xs, ys = self._axes()
        cx, cy = self.px(center[0]), self.py(center[1])
        dx, dy = xs - cx, ys - cy
        if rot:
            c, s = math.cos(rot), math.sin(rot)
            dx, dy = dx * c + dy * s, -dx * s + dy * c
        mask = (dx / rx) ** 2 + (dy / ry) ** 2 <= 1.0
        if only_over is not None and only_over >= 0:
            mask &= self.grid >= 0
        self.grid[mask] = tone
        self.strokes += 1

    def oval(
        self,
        center: tuple[float, float],
        width: float,
        height: float,
        tone: int,
        rot: float = 0.0,
        only_over: int | None = None,
    ) -> None:
        """Эллипс, заданный ГАБАРИТОМ в пикселях (как толщина мазка)."""
        self.blob(center, width * 0.5, height * 0.5, tone, rot, only_over)

    def poly(
        self,
        points: list[tuple[float, float]],
        tone: int,
        only_over: int | None = None,
    ) -> None:
        xs, ys = self._axes()
        pts = [(self.px(x), self.py(y)) for x, y in points]
        mask = _even_odd(xs, ys, pts)
        if only_over is not None and only_over >= 0:
            mask &= self.grid >= 0
        self.grid[mask] = tone
        self.strokes += 1

    # -- финальные проходы -----------------------------------------------
    def outline(self, tone: int, thickness: int = 1) -> None:
        """Контур снаружи силуэта (заполняется только прозрачное)."""
        body = self.grid >= 0
        grown = body.copy()
        for _ in range(thickness):
            nxt = grown.copy()
            nxt[1:, :] |= grown[:-1, :]
            nxt[:-1, :] |= grown[1:, :]
            nxt[:, 1:] |= grown[:, :-1]
            nxt[:, :-1] |= grown[:, 1:]
            grown = nxt
        edge = grown & ~body
        self.grid[edge] = tone
        self.strokes += 1

    def inner_shadow_edge(self, tone: int, material_mask: np.ndarray) -> None:
        """1 px тени по внутреннему нижнему краю выбранной области."""
        m = material_mask & (self.grid >= 0)
        below = np.zeros_like(m)
        below[:-1, :] = ~m[1:, :]
        edge = m & below
        self.grid[edge & (self.grid >= 0)] = tone
        self.strokes += 1

    # -- результат --------------------------------------------------------
    def to_image(self) -> Image.Image:
        rgba = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        body = self.grid >= 0
        for idx, (r, g, b) in enumerate(PALETTE):
            hit = self.grid == idx
            if not hit.any():
                continue
            rgba[hit] = (r, g, b, 255)
        rgba[~body] = (0, 0, 0, 0)
        return Image.fromarray(rgba, mode="RGBA")

    def colors_used(self) -> int:
        return int(len(np.unique(self.grid[self.grid >= 0])))

    def report(self) -> dict:
        """Метрики, которые нужны технической проверке мастер-ассета."""
        body = self.grid >= 0
        rows = np.where(body.any(axis=1))[0]
        cols = np.where(body.any(axis=0))[0]
        semi = 0
        image = np.array(self.to_image())
        alpha = image[:, :, 3]
        semi = int(((alpha > 0) & (alpha < 255)).sum())
        return {
            "canvas": [self.width, self.height],
            "scale_h": self.scale,
            "strokes": self.strokes,
            "colors": self.colors_used(),
            "opaque_px": int(body.sum()),
            "semi_transparent_px": semi,
            "bbox": [int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())]
            if body.any() else None,
            "figure_height_px": int(rows.max() - rows.min() + 1) if body.any() else 0,
            "feet_row": int(rows.max()) if body.any() else -1,
        }
