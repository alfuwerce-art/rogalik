"""Автор игрового силуэта героя (Этап 3, задачи 3.1 → 3.1a → 3.1b).

Что делает
----------
Рисует героя 48 px по утверждённому референсу (D7, HERO_REFERENCE.md) в четырёх
направлениях и двух кадрах `idle`, собирает лист-источник PNG и строит из него
настоящий проект Pixelorama `.pxo` через пайплайн (`tools/pixel_pipeline/pxo.py`).
Дальше `.pxo` экспортируется **самим Pixelorama CLI**
(`python -m pixel_pipeline.cli export`), и уже этот экспорт идёт в игру.

Версия 3.1b (художественная калибровка, задача 3.1b)
----------------------------------------------------
Что изменено относительно 3.1a и зачем:

* **Светотень вместо ровной заливки.** Введены четыре тона кожи и отдельный
  контровой блик: торс, руки и лицо читаются объёмно, а не как плоское пятно.
* **Материалы разведены по светлоте.** Обмотки рук и голеней стали темнее кожи
  (в 3.1a они были светлее и ноги читались как «белые носки»), штаны — тёмный
  серо-бурый, кушак — багряный с бликом.
* **Повязка усилена.** Три ряда вместо двух, яркая верхняя кромка, тёмный низ,
  узел и два сужающихся конца; на затылке — узел с двумя лентами.
* **Силуэт атлетичнее.** Плечи 20 px, талия 8 px, бёдра 12 px; руки отделены
  зазором в 1 px, который заполняет внутренний контур; голени тоньше бёдер.
* **Волосы — масса с рисунком**, а не «шлем»: неровный контур, пряди, локоны,
  светлая полоса сверху и тёмная под массой.
* Опорная точка и геометрия кадра не изменились: 32x48, стопы на y=46, контур
  в y=47; кадр `idle` B — тот же рисунок со сдвигом головы и шеи на 1 px.

Почему рисунок задан таблицами пикселей
--------------------------------------
Спрайт такого размера нельзя получить масштабированием живописного референса:
уменьшение 1536x1024 даёт мыло, а не пиксель-арт. Поэтому силуэт собран из явно
заданных горизонтальных пробегов и точечных деталей. Никакого шума, случайности
и авто-даунскейла: каждый пиксель задан вручную.

Соглашения
----------
* кадр 32x48, герой 48 px по высоте (D16), опорная точка — середина стоп;
* части тела разделяются прозрачным зазором 1 px: контур, дорисованный наружу
  (`outline_outward`), заполняет его тёмным и работает внутренней обводкой;
* нижняя строка кадра — подошва контура; она одинакова во всех восьми кадрах;
* свет условно сверху-слева: блик на левой/верхней кромке, тень на правой/нижней.

Раскладка 48 px по вертикали:
    y0..9   голова (волосы, повязка, лицо)      10 рядов
    y10     шея                                  1
    y11..13 плечи и дельтовидные                 3
    y14..19 грудная клетка                       6
    y20..23 талия и пресс                        4
    y24..26 кушак                                3
    y27..33 бёдра (свободные штаны)              7
    y34..38 штанины и рваный край                5
    y39..44 обмотки голеней                      6
    y45..46 босые стопы                          2
    y47     нижняя строка контура                1

Горизонталь кадра 32 px, центр между x15 и x16:
    руки        x5..8 (левая)  и x23..26 (правая)
    плечи       x6..25   (20 px)
    грудь       x10..21  (12 px)
    талия       x12..19  (8 px)
    кушак       x11..20
    бёдра       x10..21  (12 px)
    штанины     x10..14 и x17..21
    голени      x11..14 и x17..20
    стопы       x8..14  и x17..23

Статус результата: `ASSET_DRAFT` — рабочий ассет, художественная приёмка за
владельцем. Это не `PROXY_TECHNICAL` (рисуется по референсу, а не заглушка) и не
`ASSET_APPROVED` (решение принимает только владелец).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

FRAME_W = 32
FRAME_H = 48
HERO_HEIGHT = 48
DIRECTIONS = ("down", "up", "left", "right")
IDLE_FRAMES = 2
ART_REVISION = "3.1b"

# Палитра: тёмная кожа + серо-бурые ткани + красный акцент
# (PIXEL_ART_STYLE_GUIDE §4, HERO_REFERENCE §«Палитра»).
# Материалы разведены по светлоте: кожа теплее и светлее обмоток, обмотки
# светлее штанов, багрянец — единственный насыщенный акцент.
PALETTE = {
    "outline": "#0f0d0c",
    "skin_rim": "#e2b184",
    "skin_hi": "#cf9d6d",
    "skin": "#ab7647",
    "skin_mid": "#8a5b33",
    "skin_dark": "#5d3c1f",
    "hair_hi": "#7a6244",
    "hair": "#4c3b2a",
    "hair_dark": "#2a2017",
    "red_hi": "#cf5147",
    "red": "#a02f2c",
    "red_dark": "#5d2130",
    "pants_hi": "#403b33",
    "pants": "#2f2b26",
    "pants_dark": "#1d1a17",
    "wrap_hi": "#7a6a50",
    "wrap": "#5d5140",
    "wrap_dark": "#3a3226",
}


def rgba(key: str) -> tuple[int, int, int, int]:
    value = PALETTE[key].lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)


class Canvas:
    """Полотно с явными пикселями: только прямые записи, без сглаживания."""

    def __init__(self, width: int = FRAME_W, height: int = FRAME_H) -> None:
        self.width = width
        self.height = height
        self.pixels: dict[tuple[int, int], str] = {}

    def put(self, x: int, y: int, key: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[(x, y)] = key

    def erase(self, x: int, y: int) -> None:
        self.pixels.pop((x, y), None)

    def span(self, y: int, x0: int, x1: int, key: str) -> None:
        for x in range(x0, x1 + 1):
            self.put(x, y, key)

    def spans(self, rows: list[tuple[int, int, int]], key: str) -> None:
        for y, x0, x1 in rows:
            self.span(y, x0, x1, key)

    def column(self, x: int, y0: int, y1: int, key: str) -> None:
        for y in range(y0, y1 + 1):
            self.put(x, y, key)

    def get(self, x: int, y: int) -> str | None:
        return self.pixels.get((x, y))

    def outline_outward(self, key: str = "outline") -> None:
        """Контур на 1 px наружу: рисунок не съедается и работает внутренней обводкой."""
        border: dict[tuple[int, int], str] = {}
        for (x, y) in self.pixels:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if (nx, ny) not in self.pixels:
                    border[(nx, ny)] = key
        self.pixels.update(border)

    def shifted_head(self, max_y: int, dy: int) -> "Canvas":
        """Копия со сдвигом головы и шеи (дыхание) при неподвижных плечах и ногах."""
        result = Canvas(self.width, self.height)
        for (x, y), key in self.pixels.items():
            result.put(x, y + dy if y <= max_y else y, key)
        return result

    def to_image(self) -> Image.Image:
        image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        for (x, y), key in self.pixels.items():
            image.putpixel((x, y), rgba(key))
        return image


# ---------------------------------------------------------------------------
# Общие части тела
# ---------------------------------------------------------------------------


def draw_legs(c: Canvas) -> None:
    """Штаны, обмотки голеней и босые стопы — одинаково спереди и сзади."""
    # Бёдра: свободные штаны, чуть шире бёдер, с тенью в глубине.
    c.spans([(y, 10, 21) for y in range(27, 34)], "pants")
    # Объём: светлая кромка слева, тень справа и в складках.
    c.spans([(27, 11, 13), (28, 11, 13), (29, 11, 12)], "pants_hi")
    c.column(21, 27, 33, "pants_dark")
    c.column(20, 29, 33, "pants_dark")
    c.column(10, 30, 33, "pants_dark")
    c.spans([(29, 15, 16), (30, 14, 15), (31, 15, 16)], "pants_dark")
    c.spans([(31, 12, 13), (32, 12, 14)], "pants_hi")
    # Штанины: между ними тень, у каждой — светлая левая кромка.
    c.spans([(y, 10, 14) for y in range(34, 39)], "pants")
    c.spans([(y, 17, 21) for y in range(34, 39)], "pants")
    c.column(14, 34, 38, "pants_dark")
    c.column(17, 34, 38, "pants_dark")
    c.column(21, 34, 38, "pants_dark")
    c.spans([(34, 10, 11), (35, 10, 11), (36, 11, 12)], "pants_hi")
    c.spans([(34, 17, 18), (35, 17, 18)], "pants_hi")
    # Рваный край: зубцы разной длины вместо линейки.
    for x in (9, 12, 19, 22):
        c.erase(x, 38)
    c.span(38, 10, 11, "pants_dark")
    c.span(38, 20, 21, "pants_dark")
    c.span(38, 17, 18, "pants_dark")

    # Обмотки голеней: полосы ткани темнее кожи (в 3.1a они были светлее).
    c.spans([(y, 11, 14) for y in range(39, 45)], "wrap")
    c.spans([(y, 17, 20) for y in range(39, 45)], "wrap")
    for y in (39, 41, 43):
        c.spans([(y, 11, 14), (y, 17, 20)], "wrap_hi")
    c.spans([(40, 11, 14), (40, 17, 20)], "wrap_dark")
    c.column(14, 39, 44, "wrap_dark")
    c.column(17, 39, 44, "wrap_dark")
    # Хвостик обмотки, свисающий на левой голени.
    c.spans([(43, 10, 10), (44, 10, 11)], "wrap_hi")

    # Босые стопы: шире голени, пальцы обозначены тенью.
    c.spans([(45, 9, 14), (46, 8, 14)], "skin")
    c.spans([(45, 17, 22), (46, 17, 23)], "skin")
    c.span(45, 10, 13, "skin_hi")
    c.span(45, 18, 21, "skin_hi")
    c.span(46, 9, 13, "skin_mid")
    c.span(46, 18, 22, "skin_mid")
    for x in (10, 12, 18, 20):
        c.put(x, 46, "skin_dark")


def draw_arms(c: Canvas) -> None:
    """Руки: дельтовидная, плечо, предплечье в обмотке, кисть.

    Руки отстоят от корпуса на 1 px (зазор заполняет контур): это даёт
    внутреннюю обводку и не даёт массе «слипнуться» с торсом. Ширина руки 4 px:
    на 48 px трёхпиксельная рука читалась как палка.
    """
    # Дельтовидные — часть плечевого пояса.
    c.spans([(11, 5, 9), (11, 22, 26)], "skin")
    c.spans([(12, 5, 9), (12, 22, 26)], "skin")
    c.spans([(11, 6, 9), (11, 22, 25)], "skin_hi")
    c.column(9, 12, 19, "skin_mid")
    c.column(22, 12, 19, "skin_dark")
    # Плечо и предплечье.
    c.spans([(y, 5, 8) for y in range(13, 20)], "skin")
    c.spans([(y, 23, 26) for y in range(13, 20)], "skin")
    c.column(5, 12, 19, "skin_hi")
    c.column(26, 13, 19, "skin_dark")
    c.column(25, 13, 19, "skin_mid")
    c.column(8, 15, 19, "skin_mid")
    c.spans([(14, 5, 6), (15, 5, 6)], "skin_rim")
    # Локоть: строка между плечом и обмоткой, чтобы рука читалась по членениям.
    c.spans([(19, 5, 8), (19, 23, 26)], "skin_mid")
    c.spans([(20, 5, 8), (20, 23, 26)], "skin_dark")
    # Предплечья в обмотках: темнее кожи.
    c.spans([(y, 5, 8) for y in range(21, 26)], "wrap")
    c.spans([(y, 23, 26) for y in range(21, 26)], "wrap")
    c.column(5, 21, 25, "wrap_hi")
    c.column(26, 21, 25, "wrap_dark")
    c.spans([(22, 5, 8), (22, 23, 26)], "wrap_hi")
    c.spans([(24, 5, 8), (24, 23, 26)], "wrap_dark")
    c.column(8, 21, 25, "wrap_dark")
    c.column(23, 21, 25, "wrap_dark")
    # Кисти.
    c.spans([(26, 5, 8), (27, 5, 8)], "skin_mid")
    c.spans([(26, 23, 26), (27, 23, 26)], "skin_mid")
    c.put(5, 26, "skin")
    c.put(26, 26, "skin")
    c.put(6, 27, "skin_dark")
    c.put(25, 27, "skin_dark")


def draw_sash(c: Canvas) -> None:
    """Красный кушак: три ряда с бликом сверху и тенью снизу, как на референсе."""
    c.spans([(24, 11, 20), (25, 11, 20), (26, 11, 20)], "red")
    c.span(24, 12, 19, "red_hi")
    c.span(25, 11, 20, "red")
    c.span(26, 11, 20, "red_dark")
    c.put(11, 24, "red_dark")
    c.put(20, 24, "red_dark")
    c.put(20, 25, "red_dark")


def draw_torso(c: Canvas, *, back: bool) -> None:
    """Плечи, грудная клетка и талия: светотень вместо ровной заливки."""
    # Плечевой пояс: скос от шеи к дельтовидным, широкий, но не «вешалка».
    c.span(10, 9, 22, "skin_mid")
    c.span(11, 6, 25, "skin")
    c.span(12, 7, 24, "skin")
    c.span(10, 10, 13, "skin")
    c.span(10, 18, 21, "skin")
    c.span(12, 10, 14, "skin_hi")
    c.span(12, 18, 21, "skin_hi")

    # Грудная клетка и талия: сужение к талии задано пробегами, а не тенью.
    c.spans([(y, 10, 21) for y in range(13, 17)], "skin")
    c.spans([(y, 10, 20) for y in range(17, 19)], "skin")
    c.spans([(y, 11, 20) for y in range(19, 21)], "skin")
    c.spans([(y, 11, 19) for y in range(21, 22)], "skin")
    c.spans([(y, 12, 19) for y in range(22, 24)], "skin")
    # Свет: левая половина светлее, правая уходит в тень.
    c.column(10, 13, 19, "skin_hi")
    c.column(11, 13, 18, "skin_hi")
    c.column(21, 13, 22, "skin_dark")
    c.column(20, 15, 22, "skin_mid")

    if back:
        # Спина: лопатки, позвоночная борозда, тени по бокам.
        c.spans([(14, 12, 14), (14, 18, 20)], "skin_hi")
        c.spans([(15, 12, 14), (15, 18, 20)], "skin")
        c.column(15, 16, 22, "skin_mid")
        c.column(16, 16, 22, "skin_dark")
        c.spans([(18, 12, 13), (18, 18, 19)], "skin_hi")
        c.spans([(19, 11, 12), (19, 19, 20)], "skin_mid")
        c.spans([(20, 13, 18)], "skin_mid")
        c.span(21, 14, 17, "skin_dark")
    else:
        # Грудь: две массы с тенью под ними и короткой бороздой по центру.
        c.spans([(14, 12, 15), (14, 17, 20)], "skin_hi")
        c.spans([(15, 12, 15), (15, 17, 20)], "skin_hi")
        c.column(15, 16, 18, "skin_mid")
        c.column(16, 16, 18, "skin_dark")
        c.spans([(16, 11, 12), (16, 20, 21)], "skin_mid")
        c.spans([(17, 11, 14), (17, 18, 21)], "skin_mid")
        c.span(18, 13, 18, "skin_mid")
        # Пресс: короткие поперечные линии, а не сплошная сетка.
        c.spans([(20, 13, 18), (22, 13, 18)], "skin_mid")
        c.put(16, 20, "skin_dark")
        c.put(16, 22, "skin_dark")
    # Ключицы и ямка у шеи.
    c.spans([(12, 11, 14), (12, 17, 20)], "skin_rim")
    c.put(15, 12, "skin_dark")
    c.put(16, 12, "skin_dark")


# ---------------------------------------------------------------------------
# Вид спереди (down)
# ---------------------------------------------------------------------------

DOWN_HAIR = [
    (0, 13, 18),
    (1, 12, 19),
    (2, 10, 21),
    (3, 9, 21),
    (4, 9, 21),
    (5, 9, 21),
    (6, 9, 21),
    (7, 9, 21),
    (8, 10, 20),
    (9, 11, 20),
]


def draw_down() -> Canvas:
    c = Canvas()
    # --- Волосы: масса с рисунком прядей, локоны по краям ---
    c.spans(DOWN_HAIR, "hair")
    c.spans([(1, 13, 16), (2, 11, 14), (3, 10, 12), (4, 10, 11)], "hair_hi")
    c.spans([(1, 17, 18), (2, 18, 19)], "hair_hi")
    c.column(16, 1, 3, "hair_dark")
    c.column(20, 2, 5, "hair_dark")
    c.spans([(5, 10, 10), (6, 10, 10), (7, 11, 11)], "hair_dark")
    c.spans([(5, 20, 20), (6, 21, 21), (7, 21, 21)], "hair_dark")
    # Локоны, выходящие за массу: силуэт перестаёт быть «шлемом».
    c.put(8, 3, "hair")
    c.put(8, 4, "hair_dark")
    c.put(22, 5, "hair")
    c.put(22, 6, "hair_dark")
    # Неровные кончики прядей у шеи.
    for x in (11, 14, 19, 21):
        c.erase(x, 9)
    c.put(12, 9, "hair_dark")
    c.put(20, 9, "hair_dark")

    # --- Лицо: видна только нижняя половина, глаза закрыты повязкой ---
    c.spans([(4, 11, 20), (5, 11, 20), (6, 11, 20)], "skin")
    c.spans([(7, 11, 20), (8, 12, 19)], "skin")
    c.column(11, 7, 8, "skin_mid")
    c.column(20, 7, 8, "skin_mid")
    c.span(7, 12, 19, "skin_hi")
    c.put(15, 7, "skin_mid")
    c.put(16, 7, "skin_mid")
    c.span(8, 15, 16, "skin_dark")

    # --- Красная повязка: три ряда, яркая кромка, узел и два конца ---
    c.spans([(4, 10, 21), (5, 10, 21), (6, 10, 21)], "red")
    c.span(4, 11, 20, "red_hi")
    c.span(4, 10, 10, "red_dark")
    c.span(6, 10, 21, "red_dark")
    c.span(5, 15, 16, "red_hi")
    # Узел на виске (справа от нас) и два сужающихся конца ткани.
    c.spans([(4, 22, 23), (5, 22, 23)], "red")
    c.put(23, 4, "red_hi")
    c.put(23, 5, "red_dark")
    c.spans([(3, 24, 26)], "red")
    c.put(27, 2, "red")
    c.put(27, 3, "red_dark")
    c.spans([(6, 24, 25)], "red_dark")
    c.put(26, 7, "red_dark")
    # Свисающая с затылка лента (видна и спереди как акцент у плеча).
    c.spans([(8, 9, 9), (9, 9, 9), (10, 9, 9)], "red_dark")

    # --- Шея ---
    c.span(9, 14, 17, "skin_mid")
    c.span(10, 14, 17, "skin_dark")

    draw_torso(c, back=False)
    draw_arms(c)
    draw_sash(c)
    draw_legs(c)

    # Кушак: узел спереди слева и два свисающих конца.
    c.spans([(27, 11, 12), (28, 11, 11), (29, 11, 11), (30, 11, 11), (31, 10, 11)], "red")
    c.put(12, 27, "red_hi")
    c.put(10, 31, "red_dark")
    c.spans([(27, 14, 15), (28, 14, 14), (29, 14, 14)], "red_dark")

    c.outline_outward()
    return c


# ---------------------------------------------------------------------------
# Вид сзади (up)
# ---------------------------------------------------------------------------

UP_HAIR = [
    (0, 13, 18),
    (1, 12, 19),
    (2, 10, 21),
    (3, 9, 21),
    (4, 9, 21),
    (5, 9, 21),
    (6, 9, 21),
    (7, 9, 21),
    (8, 9, 21),
    (9, 10, 20),
]


def draw_up() -> Canvas:
    c = Canvas()
    # --- Затылок: волосы закрывают голову целиком ---
    c.spans(UP_HAIR, "hair")
    c.spans([(1, 13, 16), (2, 11, 14), (3, 10, 12), (4, 10, 11)], "hair_hi")
    c.spans([(5, 10, 10), (6, 10, 10)], "hair_hi")
    c.spans([(2, 16, 16), (3, 17, 17), (4, 18, 18)], "hair_dark")
    c.spans([(6, 11, 11), (7, 11, 11), (8, 12, 12)], "hair_dark")
    c.spans([(6, 19, 19), (7, 20, 20), (8, 20, 20)], "hair_dark")
    c.put(8, 3, "hair")
    c.put(22, 5, "hair")
    # Неровные кончики: часть пикселей нижнего ряда убрана.
    for x in (11, 13, 15, 18, 20):
        c.erase(x, 9)
    c.put(12, 9, "hair_dark")
    c.put(14, 9, "hair")
    c.put(19, 9, "hair_dark")

    # --- Узел повязки на затылке и две ленты ---
    c.spans([(4, 13, 19), (5, 13, 19)], "red")
    c.span(4, 14, 18, "red_hi")
    c.span(5, 13, 19, "red_dark")
    c.spans([(6, 14, 15)], "red")
    c.spans([(6, 13, 13), (7, 13, 13), (8, 12, 12), (9, 12, 12), (10, 12, 12)], "red")
    c.spans([(6, 18, 18), (7, 18, 18), (8, 19, 19), (9, 19, 19), (10, 19, 19)], "red")
    c.put(12, 10, "red_dark")
    c.put(19, 10, "red_dark")
    c.put(13, 7, "red_hi")
    c.put(19, 7, "red_hi")

    # --- Шея и плечи ---
    c.span(9, 14, 17, "skin_mid")
    c.span(10, 14, 17, "skin_dark")
    draw_torso(c, back=True)
    draw_arms(c)
    draw_sash(c)
    draw_legs(c)

    # Узел кушака сзади с двумя концами.
    c.spans([(27, 17, 18), (28, 17, 18), (29, 18, 19), (30, 19, 20)], "red")
    c.put(17, 27, "red_hi")
    c.put(20, 30, "red_dark")

    c.outline_outward()
    return c


# ---------------------------------------------------------------------------
# Вид в профиль (left)
# ---------------------------------------------------------------------------
#
# Боковых видов на утверждённом референсе нет: это рабочая художественная
# интерпретация до просмотра владельцем (см. STAGE_03.md §8).

LEFT_HAIR = [
    (0, 13, 18),
    (1, 11, 19),
    (2, 10, 20),
    (3, 9, 21),
    (4, 9, 21),
    (5, 9, 21),
    (6, 14, 21),
    (7, 14, 21),
    (8, 14, 20),
    (9, 15, 19),
]


def draw_left() -> Canvas:
    c = Canvas()
    # --- Волосы: спереди прядь на лицо, сзади объёмная масса ниже уха ---
    c.spans(LEFT_HAIR, "hair")
    c.spans([(1, 12, 16), (2, 11, 14), (3, 10, 12)], "hair_hi")
    c.spans([(4, 20, 21), (5, 20, 21), (6, 20, 21)], "hair_dark")
    c.put(19, 8, "hair_dark")
    c.put(21, 3, "hair")
    c.put(15, 9, "hair_dark")

    # --- Профиль: лоб закрыт повязкой, видны нос, губы, подбородок ---
    c.spans([(6, 8, 14), (7, 9, 14), (8, 10, 14)], "skin")
    c.put(8, 6, "skin_hi")
    c.put(8, 7, "skin_hi")
    c.put(10, 8, "skin_mid")
    c.put(14, 6, "skin_mid")
    c.put(14, 8, "skin_mid")

    # --- Повязка: через глаз, узел у виска, конец уходит назад ---
    c.spans([(4, 10, 21), (5, 10, 21), (6, 10, 20)], "red")
    c.span(4, 11, 20, "red_hi")
    c.span(5, 10, 21, "red_dark")
    c.spans([(4, 22, 23), (5, 22, 23)], "red")
    c.put(23, 4, "red_hi")
    c.put(23, 5, "red_dark")
    c.spans([(3, 24, 25)], "red")
    c.put(26, 2, "red_dark")
    c.spans([(6, 23, 24)], "red_dark")

    # --- Шея и плечо в профиль ---
    c.span(9, 12, 15, "skin_mid")
    c.span(10, 12, 16, "skin_dark")
    c.span(11, 11, 19, "skin")
    c.span(12, 10, 20, "skin")
    c.span(13, 10, 20, "skin")
    c.span(12, 11, 18, "skin_hi")
    c.span(10, 13, 15, "skin")

    # --- Торс в профиль: грудь слева (лицом влево), спина справа ---
    c.spans([(y, 11, 21) for y in range(14, 19)], "skin")
    c.spans([(y, 12, 20) for y in range(19, 24)], "skin")
    c.spans([(y, 12, 19) for y in range(24, 25)], "skin")
    c.column(11, 14, 18, "skin_hi")
    c.column(12, 14, 17, "skin_hi")
    c.column(21, 14, 22, "skin_dark")
    c.column(20, 16, 23, "skin_mid")
    c.put(13, 17, "skin_dark")
    c.span(18, 13, 18, "skin_mid")

    # --- Кушак рисуется до руки: кисть должна остаться поверх пояса ---
    c.spans([(24, 12, 20), (25, 11, 20), (26, 11, 20)], "red")
    c.span(24, 12, 19, "red_hi")
    c.span(26, 11, 20, "red_dark")

    # --- Ближняя рука висит перед корпусом: её передняя кромка — край силуэта ---
    c.column(12, 13, 28, "skin_dark")  # тень-разделитель между рукой и корпусом
    c.spans([(y, 8, 11) for y in range(13, 20)], "skin")
    c.column(8, 13, 19, "skin_hi")
    c.column(11, 13, 19, "skin_mid")
    c.spans([(20, 8, 11)], "skin_dark")
    c.spans([(y, 8, 11) for y in range(21, 26)], "wrap")
    c.span(21, 8, 11, "wrap_hi")
    c.column(11, 21, 25, "wrap_dark")
    c.span(23, 8, 11, "wrap_dark")
    c.spans([(26, 8, 11), (27, 8, 11)], "skin_mid")
    c.put(8, 26, "skin")

    # --- Кушак: свисающий спереди конец ---
    c.spans([(27, 10, 11), (28, 10, 11), (29, 9, 10)], "red")
    c.put(9, 29, "red_dark")

    # --- Свободные штаны в профиль ---
    c.spans([(y, 10, 21) for y in range(28, 34)], "pants")
    c.spans([(y, 10, 20) for y in range(34, 39)], "pants")
    c.span(28, 11, 14, "pants_hi")
    c.span(29, 11, 13, "pants_hi")
    c.column(21, 28, 33, "pants_dark")
    c.column(20, 30, 33, "pants_dark")
    c.column(10, 31, 38, "pants_dark")
    c.column(15, 34, 38, "pants_dark")
    c.column(16, 34, 38, "pants_dark")
    c.erase(10, 38)
    c.erase(20, 38)
    c.span(38, 11, 19, "pants_dark")

    # --- Передняя и задняя голень (в обмотках), стопы ---
    c.spans([(y, 11, 14) for y in range(39, 45)], "wrap")
    c.spans([(y, 17, 20) for y in range(39, 45)], "wrap")
    for y in (39, 41, 43):
        c.spans([(y, 11, 14), (y, 17, 20)], "wrap_hi")
    c.spans([(40, 11, 14), (40, 17, 20)], "wrap_dark")
    c.column(14, 39, 44, "wrap_dark")
    c.column(20, 39, 44, "wrap_dark")
    # Передняя стопа выдвинута вперёд (влево) — читается направление.
    c.spans([(45, 8, 14), (46, 7, 14)], "skin")
    c.spans([(45, 17, 20), (46, 17, 21)], "skin_mid")
    c.span(45, 9, 13, "skin_hi")
    c.span(46, 8, 13, "skin_mid")
    c.put(10, 46, "skin_dark")
    c.put(18, 46, "skin_dark")

    # Контровой блик на передних кромках руки и стопы: набор цветов кадра
    # совпадает с фронтальным видом (проверка `palette_consistency`) и объём
    # читается сильнее. Ставится последним, чтобы его не перекрыли.
    c.put(8, 13, "skin_rim")
    c.put(8, 14, "skin_rim")
    c.put(8, 45, "skin_rim")

    c.outline_outward()
    return c


def mirrored(canvas: Canvas) -> Canvas:
    """Правый профиль — зеркало левого: пиксели остаются целыми, без интерполяции."""
    result = Canvas(canvas.width, canvas.height)
    for (x, y), key in canvas.pixels.items():
        result.put(canvas.width - 1 - x, y, key)
    return result


def build_frames() -> dict[str, list[Canvas]]:
    down = draw_down()
    up = draw_up()
    left = draw_left()
    right = mirrored(left)
    frames: dict[str, list[Canvas]] = {}
    # idle B: вдох — голова и шея опускаются на 1 px,
    # стопы и штаны остаются на месте (опорная точка не «прыгает»).
    for name, canvas in (("down", down), ("up", up), ("left", left), ("right", right)):
        frames[name] = [canvas, canvas.shifted_head(max_y=10, dy=1)]
    return frames


def compose_sheet(frames: dict[str, list[Canvas]]) -> Image.Image:
    """Лист-источник: 4 направления в колонках, 2 кадра idle в строках."""
    sheet = Image.new("RGBA", (FRAME_W * len(DIRECTIONS), FRAME_H * IDLE_FRAMES), (0, 0, 0, 0))
    for column, name in enumerate(DIRECTIONS):
        for row, canvas in enumerate(frames[name]):
            sheet.paste(canvas.to_image(), (column * FRAME_W, row * FRAME_H))
    return sheet


def frame_sequence(frames: dict[str, list[Canvas]]) -> list[Image.Image]:
    """Порядок кадров `.pxo`: down A, down B, up A, up B, left A, left B, right A, right B."""
    sequence: list[Image.Image] = []
    for name in DIRECTIONS:
        for canvas in frames[name]:
            sequence.append(canvas.to_image())
    return sequence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="tools/stage3_hero/source", help="каталог листа-источника")
    parser.add_argument("--project", default=None, help="куда записать .pxo (по умолчанию рядом)")
    parser.add_argument("--json", default=None, help="записать отчёт о сборке сюда")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = build_frames()
    sheet = compose_sheet(frames)
    sheet_path = out_dir / "hero_idle_48_source.png"
    sheet.save(sheet_path)

    # Настоящий проект Pixelorama собирается пайплайном, а не «похожим писателем PNG».
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pixel_pipeline import pxo as pxo_mod  # noqa: E402

    project = Path(args.project) if args.project else out_dir / "hero_idle_48.pxo"
    tags = [
        pxo_mod.frame_tag(f"idle_{name}", index * IDLE_FRAMES, index * IDLE_FRAMES + IDLE_FRAMES - 1)
        for index, name in enumerate(DIRECTIONS)
    ]
    pxo_mod.build_pxo(project, frame_sequence(frames), fps=6.0, layer_name="Hero", tags=tags)

    report = {
        "art_revision": ART_REVISION,
        "sheet": str(sheet_path),
        "sheet_size": list(sheet.size),
        "project": str(project),
        "frames": len(DIRECTIONS) * IDLE_FRAMES,
        "frame_size": [FRAME_W, FRAME_H],
        "directions": list(DIRECTIONS),
        "status": "ASSET_DRAFT",
        "palette": PALETTE,
    }
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
