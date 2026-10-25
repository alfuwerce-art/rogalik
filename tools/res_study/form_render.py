"""Формовый рендерер пиксель-арта для Rogalik (исследование разрешений, 3.1c).

Почему не прямоугольники. Прежний способ (`tools/stage3_hero/author_hero.py`)
рисовал героя прямоугольниками и таблицами пикселей: получались плоские
прямоугольные формы без анатомии и без объёма. Здесь другой подход:

1. Каждая часть тела — аналитическая SDF-форма (капсула с переменным радиусом,
   эллипс, скруглённый прямоугольник). Формы объединяются в силуэт.
2. Объём получается из поля расстояний: нормаль поверхности берётся как
   градиент SDF, поэтому любая форма автоматически затеняется как округлый
   объём (свет слева-сверху, холодный отражённый свет справа-снизу).
3. Свет квантуется в рампу материала из 5–7 цветов со сдвигом оттенка:
   тени уходят в холодный фиолетово-синий, свет — в тёплый; это и даёт
   «живописный» пиксель-арт вместо трёх плоских тонов.
4. Материалы различаются рампой и текстурой: кожа, волосы, тёмная ткань
   штанов, багряная ткань пояса и повязки, льняные обмотки, кожа ремней.
5. Поверх формы кладутся осмысленные акценты: складки, разделение мышц,
   пряди волос, рваный низ штанов, швы обмоток, шрамы.

Рендер идёт без сглаживания: покрытие считается по 4×4 подвыборкам и
переводится в жёсткий порог, поэтому на выходе честная пиксельная сетка с
alpha строго 0/255 и ограниченной палитрой.

Модуль используется авторами ассетов `author_hero.py` и `author_scene.py`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

# --- свет ------------------------------------------------------------------

KEY = np.array([-0.46, -0.66, 0.60])       # тёплый ключевой: сверху-слева-спереди
KEY /= np.linalg.norm(KEY)
BOUNCE = np.array([0.60, 0.38, 0.28])      # холодный отражённый: снизу-справа
BOUNCE /= np.linalg.norm(BOUNCE)
SS = 4                                      # подвыборок на пиксель по каждой оси
DITHER_DEFAULT = True                       # упорядоченный дизеринг на границах рампы


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


# --- палитры ---------------------------------------------------------------
# Рампа: 0 — самая глубокая тень, последняя — самый яркий свет.
# Тени смещены в холодный фиолетово-синий, свет — в тёплый жёлто-охристый.

RAMPS: dict[str, list[str]] = {
    "skin": ["#2B2028", "#4A3136", "#6E4640", "#8F5C46", "#AE7452", "#C9926A", "#E0AF85"],
    "skin_deep": ["#1E1720", "#33222A", "#452C31", "#57383A"],
    "hair": ["#0F0D0C", "#1C1613", "#2C2119", "#40301F", "#574128", "#735737", "#8F7048"],
    "pants": ["#12100E", "#1B1815", "#262119", "#332C20", "#423829", "#524534"],
    "red_cloth": ["#250E14", "#3C121C", "#571A24", "#73242A", "#8E302F", "#A84338"],
    "linen": ["#211F1B", "#302D26", "#413D33", "#544E40", "#68604E", "#7D735E"],
    "leather": ["#171310", "#241C16", "#33261C", "#433225", "#54402D"],
    "stone": ["#20242B", "#2E333B", "#3F454E", "#545B65", "#6B727C", "#868D96"],
    "wood": ["#191310", "#251B15", "#34251B", "#463222", "#5A422C", "#70553A"],
    "wood_light": ["#2A1F16", "#3B2B1E", "#4E3A27", "#634C32", "#7A603F"],
    "dirt": ["#181513", "#221D18", "#2E271F", "#3B3226", "#4A3F2E", "#5A4C37"],
    "straw": ["#3A2F1C", "#4E4025", "#63522F", "#7A663A", "#916F42"],
    "outline": ["#0B0A0D"],
    "flame": ["#4A1C0C", "#7A3410", "#B45A16", "#E08A20", "#F7C157", "#FFF0C2"],
    "water": ["#0E1420", "#141C2B", "#1C2738", "#26344A", "#33445E"],
    "metal": ["#1A1C20", "#282B30", "#3A3E45", "#4F545C", "#696F78"],
}

MAT_RAMPS = RAMPS  # удобное имя


def ramp_rgb(name: str) -> np.ndarray:
    return np.array([hex_to_rgb(c) for c in RAMPS[name]], dtype=np.float32)


# --- SDF-примитивы (в пиксельных единицах, отрицательно внутри) ------------


def sdf_capsule(x: np.ndarray, y: np.ndarray, ax: float, ay: float, bx: float, by: float,
                ra: float, rb: float | None = None) -> np.ndarray:
    """Капсула/усечённый конус: органичные конечности, пряди, складки."""
    if rb is None:
        rb = ra
    pax, pay = x - ax, y - ay
    bax, bay = bx - ax, by - ay
    denom = bax * bax + bay * bay
    if denom < 1e-9:
        t = np.zeros_like(x)
    else:
        t = np.clip((pax * bax + pay * bay) / denom, 0.0, 1.0)
    dx = pax - bax * t
    dy = pay - bay * t
    r = ra + (rb - ra) * t
    return np.sqrt(dx * dx + dy * dy) - r


def sdf_ellipse(x: np.ndarray, y: np.ndarray, cx: float, cy: float, rx: float, ry: float,
                rot: float = 0.0) -> np.ndarray:
    """Эллипс (SDF-приближение): голова, торс, мышцы, камни."""
    cos_r, sin_r = math.cos(-rot), math.sin(-rot)
    px = (x - cx) * cos_r - (y - cy) * sin_r
    py = (x - cx) * sin_r + (y - cy) * cos_r
    k0 = np.sqrt((px / rx) ** 2 + (py / ry) ** 2)
    k1 = np.sqrt((px / (rx * rx)) ** 2 + (py / (ry * ry)) ** 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        sdf = np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -min(rx, ry))
    return sdf


def sdf_round_box(x: np.ndarray, y: np.ndarray, cx: float, cy: float, hw: float, hh: float,
                  r: float = 0.0) -> np.ndarray:
    """Скруглённый прямоугольник: архитектура, настил, створки."""
    qx = np.abs(x - cx) - (hw - r)
    qy = np.abs(y - cy) - (hh - r)
    outside = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2)
    inside = np.minimum(np.maximum(qx, qy), 0)
    return outside + inside - r


def sdf_poly(x: np.ndarray, y: np.ndarray, points: list[tuple[float, float]]) -> np.ndarray:
    """Простой многоугольник (чётность + расстояние до рёбер): крыши, срубы."""
    sd = np.full_like(x, 1e9)
    sign = np.zeros_like(x)
    n = len(points)
    for i in range(n):
        ax, ay = points[i]
        bx, by = points[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        wx, wy = x - ax, y - ay
        denom = ex * ex + ey * ey
        t = np.clip((wx * ex + wy * ey) / max(denom, 1e-9), 0.0, 1.0)
        dx = wx - ex * t
        dy = wy - ey * t
        sd = np.minimum(sd, dx * dx + dy * dy)
        cond = ((ay > y) != (by > y)) & (x < (bx - ax) * (y - ay) / ((by - ay) + 1e-12) + ax)
        sign = np.where(cond, -sign + 1, sign)
    return np.sqrt(sd) * np.where(sign > 0, -1.0, 1.0)


def union(*fields: np.ndarray) -> np.ndarray:
    out = fields[0]
    for other in fields[1:]:
        out = np.minimum(out, other)
    return out


def smooth_union(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """Мягкое объединение: тело читается как одна органичная форма."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


# --- холст -----------------------------------------------------------------


@dataclass
class Canvas:
    width: int
    height: int
    color: np.ndarray = field(init=False)
    alpha: np.ndarray = field(init=False)
    used: list[tuple[int, int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.color = np.zeros((self.height, self.width, 3), dtype=np.float32)
        self.alpha = np.zeros((self.height, self.width), dtype=bool)

    # сетки координат
    def grid(self, ss: int = 1) -> tuple[np.ndarray, np.ndarray]:
        ys = (np.arange(self.height * ss) + 0.5) / ss
        xs = (np.arange(self.width * ss) + 0.5) / ss
        return np.meshgrid(xs, ys)

    def coverage(self, sdf_fn) -> np.ndarray:
        """Покрытие с подвыборками: доля подпикселей внутри формы."""
        gx, gy = self.grid(SS)
        inside = (sdf_fn(gx, gy) <= 0.0).astype(np.float32)
        return inside.reshape(self.height, SS, self.width, SS).mean(axis=(1, 3))

    def shade(self, sdf: np.ndarray, ramp: str, *, ambient: float = 0.26,
              bounce: float = 0.18, radius: float = 999.0, roundness: float = 1.0,
              dither: bool | None = None,
              contrast: float = 0.95, bias: float = 0.0, level: int | None = None,
              texture=None, mask: np.ndarray | None = None) -> np.ndarray:
        """Квантованный по рампе цвет поверхности для готового SDF-поля.

        Объём считается как на цилиндре радиуса `radius`: у края силуэта
        нормаль уходит вбок, у середины формы смотрит в камеру. Это даёт
        настоящую светотень («круглое» тело), а не плоскую заливку.
        `roundness` < 1 делает форму более плоской (например, грудные мышцы).
        """
        gy, gx = np.gradient(sdf)
        depth = np.clip(-sdf, 0.0, None)
        # sin(угол наклона нормали): 0 в середине формы, 1 на краю силуэта
        s = np.clip(1.0 - depth / max(radius, 1e-6), 0.0, 1.0) * roundness
        gn = np.sqrt(gx * gx + gy * gy) + 1e-9
        nx = (gx / gn) * s
        ny = (gy / gn) * s
        nzz = np.sqrt(np.clip(1.0 - s * s, 0.0, 1.0))
        lam = np.clip(nx * KEY[0] + ny * KEY[1] + nzz * KEY[2], 0.0, 1.0)
        lam2 = np.clip(nx * BOUNCE[0] + ny * BOUNCE[1] + nzz * BOUNCE[2], 0.0, 1.0)
        t = ambient + (1.0 - ambient) * lam * contrast + bounce * lam2 + bias
        t = np.clip(t, 0.08, 1.0)
        colors = ramp_rgb(ramp)
        steps = len(colors) - 1
        if level is not None:
            idx = np.full(sdf.shape, int(np.clip(level, 0, steps)), dtype=np.int32)
            rgb = colors[idx]
            return np.where(mask[..., None], rgb, 0.0) if mask is not None else rgb
        pos = t * steps
        idx = np.floor(pos)
        frac = pos - idx
        if DITHER_DEFAULT if dither is None else dither:
            bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
                             dtype=np.float32) / 16.0
            tile = np.tile(bayer, (self.height // 4 + 1, self.width // 4 + 1))[: self.height, : self.width]
            idx = idx + (frac > tile)
        idx = np.clip(idx, 0, steps).astype(np.int32)
        if texture is not None:
            idx = np.clip(idx + texture(self), 0, steps)
        rgb = colors[idx]
        if mask is not None:
            rgb = np.where(mask[..., None], rgb, 0.0)
        return rgb

    # --- операции рисования ------------------------------------------------

    def paint(self, sdf_fn, ramp: str, *, flat_value: str | None = None,
              **shade_kwargs) -> None:
        """Кладёт форму (функцию SDF) на холст поверх уже нарисованного.

        Покрытие считается по подвыборкам (жёсткий порог 0.5 → чистые пиксели),
        цвет — по квантованной рампе материала.
        """
        cover = self.coverage(sdf_fn)
        gx, gy = self.grid(1)
        sdf = sdf_fn(gx, gy)
        sel = cover >= 0.5
        if flat_value is not None:
            base = np.array(hex_to_rgb(flat_value), dtype=np.float32)
            rgb = np.broadcast_to(base, (self.height, self.width, 3)).copy()
        else:
            rgb = self.shade(sdf, ramp, mask=sel, **shade_kwargs)
        self.color[sel] = rgb[sel]
        self.alpha[sel] = True

    def paint_layer(self, sdf: np.ndarray, ramp: str, *, flat_value: str | None = None,
                    **shade_kwargs) -> None:
        """Кладёт форму по готовому SDF-полю (1×), покрытие — порог по самому полю."""
        sel = sdf <= 0.0
        if flat_value is not None:
            base = np.array(hex_to_rgb(flat_value), dtype=np.float32)
            rgb = np.broadcast_to(base, (self.height, self.width, 3)).copy()
        else:
            rgb = self.shade(sdf, ramp, mask=sel, **shade_kwargs)
        self.color[sel] = rgb[sel]
        self.alpha[sel] = True

    def outline(self, color: str = "outline", width: float = 1.0) -> None:
        """Тёмный контур по внешней границе силуэта.

        Контур ставится только в области, достижимой от края изображения, поэтому
        просветы между рукой и корпусом не заливаются тёмным и не превращаются в
        «жилет». Внутренние полости не обводятся вовсе.
        """
        a = self.alpha
        free = ~a
        seed = np.zeros_like(a)
        seed[0, :] = free[0, :]
        seed[-1, :] = free[-1, :]
        seed[:, 0] = free[:, 0]
        seed[:, -1] = free[:, -1]
        reach = seed.copy()
        for _ in range(self.width + self.height):
            pad = np.pad(reach, 1, mode="constant", constant_values=False)
            grown = (reach | pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] |
                     pad[1:-1, 2:]) & free
            if np.array_equal(grown, reach):
                break
            reach = grown
        ring = a.copy()
        for _ in range(max(1, math.ceil(width))):
            pad = np.pad(ring, 1, mode="constant", constant_values=False)
            ring = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:] |
                    pad[1:-1, 1:-1])
        ring = ring & reach & ~a
        base = np.array(hex_to_rgb(RAMPS[color][0]), dtype=np.float32)
        self.color[ring] = base
        self.alpha[ring] = True

    # --- вывод -------------------------------------------------------------

    def to_image(self) -> Image.Image:
        rgba = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        rgba[..., :3] = np.clip(self.color, 0, 255).astype(np.uint8)
        rgba[..., 3] = np.where(self.alpha, 255, 0).astype(np.uint8)
        return Image.fromarray(rgba, mode="RGBA")

    def palette(self) -> list[tuple[int, int, int]]:
        idx = np.argwhere(self.alpha)
        seen: set[tuple[int, int, int]] = set()
        for y, x in idx:
            seen.add(tuple(int(v) for v in self.color[y, x]))  # type: ignore[arg-type]
        return sorted(seen)


# --- детерминированный шум ------------------------------------------------


def hash_noise(x: np.ndarray, y: np.ndarray, seed: int = 1337) -> np.ndarray:
    v = np.sin(x * 12.9898 + y * 78.233 + seed * 0.618) * 43758.5453
    return (v - np.floor(v)).astype(np.float32)


def value_noise(x: np.ndarray, y: np.ndarray, scale: float, seed: int = 7) -> np.ndarray:
    """Гладкий шум по сетке: структура земли, камня, дерева."""
    xs = x / scale
    ys = y / scale
    xi, yi = np.floor(xs), np.floor(ys)
    xf, yf = xs - xi, ys - yi
    xf = xf * xf * (3 - 2 * xf)
    yf = yf * yf * (3 - 2 * yf)

    def corner(cx, cy):
        return hash_noise(cx, cy, seed)

    n00 = corner(xi, yi)
    n10 = corner(xi + 1, yi)
    n01 = corner(xi, yi + 1)
    n11 = corner(xi + 1, yi + 1)
    nx0 = n00 + (n10 - n00) * xf
    nx1 = n01 + (n11 - n01) * xf
    return nx0 + (nx1 - nx0) * yf
