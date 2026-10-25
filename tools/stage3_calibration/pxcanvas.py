"""Пиксельные примитивы для художественной калибровки (Этап 3, задача 3.1b).

Задача калибровки — показать внутри Godot такой кадр, который заметно ближе к
утверждённому look-референсу `assets/references/gameplay/gameplay_look_reference.png`,
чем прототип Этапа 2, и при этом остаётся честным игровым пиксель-артом на сетке
D16 (тайл 24 px).

Почему рисунок снова задан кодом с явными координатами
-------------------------------------------------------
Уменьшение живописного референса 1672x941 даёт мыло, а не пиксель-арт. Поэтому
каждый ассет собирается из примитивов (прямоугольники, пробеги, линии, эллипсы,
дизеринг по матрице Байера) на точной пиксельной сетке. Случайность
детерминирована (`random.Random(seed)`), поэтому повторная сборка даёт тот же
файл байт в байт.

Что важно для калибровки
------------------------
* **Значение важнее детали.** На 24 px тайле читается форма и светотень, а не
  микродеталь; поэтому в каждом ассете заданы крупные световые и теневые массы,
  а мелкие пятна добавлены дозированно.
* **Дизеринг, а не градиент.** Переходы света делаются матрицей Байера 4x4 —
  это признак пиксель-арта, и он не размывается при целочисленном масштабе.
* **Прозрачность только 0 или 255** у спрайтов: полупрозрачные пиксели есть
  лишь у световых/туманных текстур (`glow_radial`, `fog_layer`, `vignette`).

Палитра согласована с ART_DIRECTION.md §«Материалы и палитра»: ночной синий,
холодный сланец, пепельно-серый, старое золото, тёмный багрянец, слоновая кость
+ локальные тёплые огни и выветрившийся белый камень.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

RGBA = tuple[int, int, int, int]


def hex_rgba(value: str, alpha: int = 255) -> RGBA:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


# Палитра калибровочного кадра. Имена — по материалам, а не по объектам:
# один и тот же `stone_l` работает и в часовне, и в фундаменте избы.
PAL: dict[str, RGBA] = {
    # холодная ночь
    "ink": hex_rgba("#0b0e13"),
    "night": hex_rgba("#151a23"),
    "night_b": hex_rgba("#1d2531"),
    "slate_d": hex_rgba("#28303a"),
    "slate": hex_rgba("#39424c"),
    "slate_l": hex_rgba("#4a545f"),
    "fog_cold": hex_rgba("#8fa3bd"),
    # тёплый огонь
    "amber_d": hex_rgba("#79461d"),
    "amber": hex_rgba("#bd772c"),
    "fire": hex_rgba("#efa347"),
    "fire_l": hex_rgba("#ffd48c"),
    "fire_w": hex_rgba("#fff0cf"),
    # золото / латунь
    "gold_d": hex_rgba("#6d5a3f"),
    "gold": hex_rgba("#aa9068"),
    "gold_l": hex_rgba("#c8b083"),
    # камень
    "stone_d": hex_rgba("#34383e"),
    "stone": hex_rgba("#4f545b"),
    "stone_l": hex_rgba("#6d737b"),
    "stone_ll": hex_rgba("#8d939a"),
    "mortar": hex_rgba("#2b2e33"),
    # выветрившийся белый камень
    "white_d": hex_rgba("#7d7a70"),
    "white": hex_rgba("#9d9a8e"),
    "white_l": hex_rgba("#bdb8a8"),
    "white_ll": hex_rgba("#d3cdba"),
    "ivory": hex_rgba("#c6c1b5"),
    # дерево
    "wood_d": hex_rgba("#211a13"),
    "wood": hex_rgba("#3a2d22"),
    "wood_m": hex_rgba("#4b3a2b"),
    "wood_l": hex_rgba("#66503a"),
    "wood_ll": hex_rgba("#816647"),
    # земля и вода: узкий диапазон тонов — на 24 px широкий разброс читается
    # как шум, а не как земля
    "earth_d": hex_rgba("#28221b"),
    "earth": hex_rgba("#2e2720"),
    "earth_m": hex_rgba("#332c24"),
    "earth_l": hex_rgba("#3a3228"),
    "earth_ll": hex_rgba("#463c30"),
    "straw": hex_rgba("#6b5b3d"),
    "water": hex_rgba("#121822"),
    "water_l": hex_rgba("#202b38"),
    "water_ll": hex_rgba("#33414f"),
    # мох
    "moss_d": hex_rgba("#232c26"),
    "moss": hex_rgba("#334036"),
    "moss_l": hex_rgba("#47563f"),
    # багрянец
    "crimson_d": hex_rgba("#37141d"),
    "crimson": hex_rgba("#6c2739"),
    "crimson_l": hex_rgba("#8e2f45"),
    "crimson_hi": hex_rgba("#b4424e"),
    # прочее
    "iron": hex_rgba("#33363c"),
    "iron_l": hex_rgba("#5a5e66"),
}

CLEAR: RGBA = (0, 0, 0, 0)

# Матрица Байера 4x4: дизеринг света и полутонов без градиентов и размытия.
BAYER4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def bayer(x: int, y: int) -> int:
    return BAYER4[y % 4][x % 4]


class Canvas:
    """Полотно с явными пикселями: только прямые записи, без сглаживания."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.px: dict[tuple[int, int], RGBA] = {}

    # --- запись ---------------------------------------------------------

    def put(self, x: int, y: int, color: RGBA) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.px[(x, y)] = color

    def erase(self, x: int, y: int) -> None:
        self.px.pop((x, y), None)

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: RGBA) -> None:
        """Заливка прямоугольника включительно по обеим границам."""
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, color)

    def hline(self, y: int, x0: int, x1: int, color: RGBA) -> None:
        self.rect(x0, y, x1, y, color)

    def vline(self, x: int, y0: int, y1: int, color: RGBA) -> None:
        self.rect(x, y0, x, y1, color)

    def fill(self, color: RGBA) -> None:
        self.rect(0, 0, self.width - 1, self.height - 1, color)

    def composite(self, other: "Canvas", ox: int = 0, oy: int = 0) -> None:
        """Наложение другого полотна: непрозрачные пиксели перекрывают нижние."""
        for (x, y), color in other.px.items():
            if color[3] == 0:
                continue
            self.put(x + ox, y + oy, color)

    # --- формы ----------------------------------------------------------

    def line(self, x0: int, y0: int, x1: int, y1: int, color: RGBA) -> None:
        """Алгоритм Брезенхема: ветви, трещины, лучи."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.put(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def thick_line(self, x0: int, y0: int, x1: int, y1: int, width: int, color: RGBA) -> None:
        for offset in range(width):
            self.line(x0, y0 + offset, x1, y1 + offset, color)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, color: RGBA) -> None:
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                dx = (x - cx) / max(rx, 0.001)
                dy = (y - cy) / max(ry, 0.001)
                if dx * dx + dy * dy <= 1.0:
                    self.put(x, y, color)

    def taper(self, x_at, half_width_at, y0: int, y1: int, color: RGBA, step: int = 1) -> None:
        """Вертикальная форма с переменным центром и шириной: ствол, столб, корень."""
        for y in range(y0, y1 + 1, step):
            cx = x_at(y)
            half = half_width_at(y)
            for x in range(int(round(cx - half)), int(round(cx + half)) + 1):
                self.put(x, y, color)

    # --- свет и фактура -------------------------------------------------

    def dither_rect(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        base: RGBA,
        accent: RGBA,
        density: float,
        rng: random.Random,
    ) -> None:
        """Плотный дизеринг внутри прямоугольника: `density` — доля акцентных пикселей."""
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if (x, y) in self.px and self.px[(x, y)][3] == 0:
                    continue
                self.put(x, y, accent if rng.random() < density else base)

    def bayer_fill(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        dark: RGBA,
        light: RGBA,
        level_of,
    ) -> None:
        """Полутон по матрице Байера: `level_of(x, y)` возвращает 0..16."""
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, light if bayer(x, y) < level_of(x, y) else dark)

    def outline(self, color: RGBA) -> None:
        """Контур в 1 px наружу от непрозрачных пикселей."""
        border: dict[tuple[int, int], RGBA] = {}
        for (x, y) in self.px:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if (nx, ny) not in self.px:
                    border[(nx, ny)] = color
        self.px.update(border)

    def shadow_under(self, x0: int, x1: int, y: int, color: RGBA, spread: int = 0) -> None:
        """Контактная тень под объектом: тёмная эллиптическая полоса."""
        for x in range(x0, x1 + 1):
            edge = min(x - x0, x1 - x)
            half = max(1, spread - edge // 3)
            for dy in range(0, half + 1):
                self.put(x, y + dy, color)

    def copy(self) -> "Canvas":
        result = Canvas(self.width, self.height)
        result.px.update(self.px)
        return result

    def flip_h(self) -> "Canvas":
        result = Canvas(self.width, self.height)
        for (x, y), color in self.px.items():
            result.put(self.width - 1 - x, y, color)
        return result

    def image(self) -> Image.Image:
        image = Image.new("RGBA", (self.width, self.height), CLEAR)
        for (x, y), color in self.px.items():
            image.putpixel((x, y), color)
        return image

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.image().save(path)
        return path


# --- вспомогательные генераторы ---------------------------------------------


def shade_rows(
    canvas: Canvas,
    x0: int,
    x1: int,
    y0: int,
    y1: int,
    colors: list[RGBA],
    seam_every: int = 0,
    seam_color: RGBA | None = None,
) -> None:
    """Горизонтальные полосы с переменным тоном: брёвна, доски, каменные ряды.

    `colors` задаёт тон каждой полосы снизу вверх (последний — самый светлый).
    `seam_every` рисует тёмный шов каждые N строк — граница между брёвнами.
    """
    height = y1 - y0 + 1
    band = max(1, height // len(colors))
    for index, color in enumerate(colors):
        top = y0 + index * band
        bottom = y0 + (index + 1) * band - 1 if index < len(colors) - 1 else y1
        canvas.rect(x0, top, x1, min(bottom, y1), color)
    if seam_color is not None and seam_every > 0:
        y = y1
        while y >= y0:
            canvas.hline(y, x0, x1, seam_color)
            y -= seam_every


def glow_radial(
    size: int,
    color: RGBA,
    max_alpha: float,
    power: float = 1.9,
    steps: int = 18,
    core: float = 0.18,
) -> Image.Image:
    """Радиальное свечение с дизерингом: маска для PointLight2D и запечённых пятен.

    Полупрозрачность здесь разрешена: это текстура света, а не спрайт.
    """
    image = Image.new("RGBA", (size, size), CLEAR)
    cx = cy = (size - 1) / 2.0
    radius = size / 2.0
    inner = radius * core
    r_channel, g_channel, b_channel, _ = color
    for y in range(size):
        for x in range(size):
            distance = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if distance > radius:
                continue
            t = 1.0 - (distance / radius)
            value = min(1.0, (t ** power) * (1.0 + core))
            if distance < inner:
                value = 1.0
            quantized = value * steps
            if quantized - int(quantized) > (bayer(x, y) + 0.5) / 16.0:
                quantized = int(quantized) + 1
            alpha = int(max(0.0, min(1.0, quantized / steps)) * max_alpha)
            if alpha <= 0:
                continue
            image.putpixel((x, y), (r_channel, g_channel, b_channel, alpha))
    return image


def fog_layer(width: int, height: int, seed: int, max_alpha: int = 34) -> Image.Image:
    """Клочья тумана: несколько перекрывающихся дизеренных масс с мягким краем."""
    image = Image.new("RGBA", (width, height), CLEAR)
    rng = random.Random(seed)
    blobs: list[tuple[float, float, float, float]] = []
    for _ in range(7):
        blobs.append(
            (
                rng.uniform(width * 0.12, width * 0.88),
                rng.uniform(height * 0.25, height * 0.80),
                rng.uniform(width * 0.16, width * 0.34),
                rng.uniform(height * 0.10, height * 0.22),
            )
        )
    for y in range(height):
        for x in range(width):
            density = 0.0
            for bx, by, rx, ry in blobs:
                dx = (x - bx) / rx
                dy = (y - by) / ry
                d2 = dx * dx + dy * dy
                if d2 >= 1.0:
                    continue
                density += (1.0 - d2) ** 1.4
            density = min(1.0, density * 0.55)
            if density <= 0.02:
                continue
            threshold = (bayer(x, y) + 0.5) / 16.0
            stepped = int(density * 8)
            if density * 8 - stepped > threshold:
                stepped += 1
            alpha = int(max_alpha * stepped / 8)
            if alpha <= 0:
                continue
            image.putpixel((x, y), (166, 186, 214, alpha))
    return image


def contact_shadow(width: int, height: int, max_alpha: int = 170) -> Image.Image:
    """Контактная тень под героем: тёмный эллипс с дизеренным краем.

    Полупрозрачность разрешена: это не спрайт, а мягкая тень в арт-пространстве.
    """
    image = Image.new("RGBA", (width, height), CLEAR)
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
    rx, ry = width / 2.0 - 0.5, height / 2.0 - 0.5
    for y in range(height):
        for x in range(width):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d >= 1.0:
                continue
            density = (1.0 - d) ** 0.75
            stepped = int(density * 8)
            if density * 8 - stepped > (bayer(x, y) + 0.5) / 16.0:
                stepped += 1
            alpha = int(max_alpha * stepped / 8)
            if alpha > 0:
                image.putpixel((x, y), (7, 8, 12, alpha))
    return image


def vignette(width: int, height: int, max_alpha: int = 150, inner: float = 0.42) -> Image.Image:
    """Затемнение по краям кадра: держит взгляд в центре, как в look-референсе."""
    image = Image.new("RGBA", (width, height), CLEAR)
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
    max_distance = (cx * cx + cy * cy) ** 0.5
    for y in range(height):
        for x in range(width):
            distance = ((x - cx) ** 2 + ((y - cy) * 1.12) ** 2) ** 0.5 / max_distance
            t = (distance - inner) / max(0.0001, 1.0 - inner)
            t = max(0.0, min(1.0, t))
            value = t ** 1.5
            alpha = int(value * max_alpha)
            if alpha <= 0:
                continue
            threshold = (bayer(x, y) + 0.5) / 16.0
            if (alpha / 255.0) * 16 - int((alpha / 255.0) * 16) > threshold:
                alpha = int(((int((alpha / 255.0) * 16) + 1) / 16) * 255)
            image.putpixel((x, y), (9, 11, 17, alpha))
    return image
