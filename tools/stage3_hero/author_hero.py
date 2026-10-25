"""Автор игрового силуэта героя (Этап 3, задачи 3.1 и 3.1a).

Что делает
----------
Рисует героя 48 px по утверждённому референсу (D7, HERO_REFERENCE.md) в четырёх
направлениях и двух кадрах `idle`, собирает лист-источник PNG и строит из него
настоящий проект Pixelorama `.pxo` через пайплайн (`tools/pixel_pipeline/pxo.py`).
Дальше `.pxo` экспортируется **самим Pixelorama CLI**
(`python -m pixel_pipeline.cli export`), и уже этот экспорт идёт в игру.

Версия 3.1a (художественная доработка)
--------------------------------------
Перекомпонованы пропорции: голова уменьшена с 13 до 9 рядов, плечи расширены до
18 px (V-образный силуэт), талия сужена до 8 px, руки и ноги стали толще, штаны —
свободнее и с рваным краем. Волосы получили неровный контур, пряди и выступающие
локоны; у повязки появился узел на виске и два сужающихся конца; на затылке —
узел и свисающая ткань. Боковые виды перерисованы под новую анатомию.

Почему рисунок задан таблицами пикселей
---------------------------------------
Спрайт такого размера нельзя получить масштабированием живописного референса:
уменьшение 1536x1024 даёт мыло, а не пиксель-арт. Поэтому силуэт собран из явно
заданных горизонтальных пробегов и точечных деталей. Никакого шума, случайности
и авто-даунскейла: каждый пиксель задан вручную.

Соглашения
----------
* кадр 32x48, герой 48 px по высоте (D16), опорная точка — середина стоп;
* части тела разделяются прозрачным зазором в 1–2 px: контур, который
  дорисовывается наружу (`outline_outward`), заполняет его тёмным и работает как
  внутренняя обводка конечности;
* нижняя строка кадра — подошва контура; она одинакова во всех восьми кадрах;
* кадр `idle` B — тот же рисунок со сдвигом головы и шеи на 1 px (вдох);
  стопы, штаны и опорная точка не двигаются;
* свет условно сверху-слева: блик на левой/верхней кромке, тень на правой/нижней.

Раскладка 48 px по вертикали:
    y0..9   голова (волосы, повязка, лицо)     10 рядов
    y10     шея                                 1
    y11..13 плечи и дельтовидные                3
    y14..19 грудная клетка                      6
    y20..24 талия и пресс                       5
    y25..26 кушак                               2
    y27..33 бёдра (свободные штаны)             7
    y34..38 штанины и рваный край               5
    y39..44 обмотки голеней                     6
    y45..46 босые стопы                         2
    y47     нижняя строка контура               1

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
ART_REVISION = "3.1a"

# Палитра: тёмная кожа + серо-бурые ткани + красный акцент
# (PIXEL_ART_STYLE_GUIDE §4, HERO_REFERENCE §«Палитра»).
# Материалы разведены по светлоте: обмотки светлее кожи, волосы светлее штанов.
PALETTE = {
    "outline": "#141110",
    "skin": "#b98a63",
    "skin_hi": "#d3a67e",
    "skin_mid": "#9c6f4c",
    "skin_dark": "#78513a",
    "hair": "#5a4530",
    "hair_hi": "#7c6340",
    "hair_dark": "#352919",
    "red": "#9e3a33",
    "red_hi": "#bf5a4a",
    "red_dark": "#6c2739",
    "pants": "#2f2c27",
    "pants_hi": "#3f3b34",
    "pants_dark": "#1f1d1a",
    "wrap": "#7b7263",
    "wrap_hi": "#948a78",
    "wrap_dark": "#574f43",
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

    def outline_outward(self, key: str = "outline") -> None:
        """Контур на 1 px наружу: рисунок не съедается и работает как внутренняя обводка."""
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


# --- общая раскладка спереди/сзади ------------------------------------------
#
# Горизонталь кадра 32 px, центр между x15 и x16:
#   руки        x7..9   и x22..24   (зазор x10 / x21 заполняет контур)
#   грудь       x11..20  (10 px)
#   талия       x12..19  (8 px) — заметное сужение
#   кушак       x11..20
#   бёдра       x10..21  (12 px) — свободные штаны
#   штанины     x10..14 и x17..21
#   голени      x11..14 и x17..20
#   стопы       x8..14  и x17..23

CHEST = [(y, 11, 20) for y in range(14, 20)]
WAIST = [(y, 12, 19) for y in range(20, 24)]
PANTS_HIPS = [(y, 10, 21) for y in range(27, 34)]
PANTS_LEG_L = [(y, 10, 14) for y in range(34, 39)]
PANTS_LEG_R = [(y, 17, 21) for y in range(34, 39)]
SHIN_L = [(y, 11, 14) for y in range(39, 45)]
SHIN_R = [(y, 17, 20) for y in range(39, 45)]
FOOT_L = [(45, 9, 14), (46, 8, 14)]
FOOT_R = [(45, 17, 22), (46, 17, 23)]


def draw_legs(c: Canvas) -> None:
    """Штаны, обмотки голеней и босые стопы — одинаково спереди и сзади."""
    # Свободные штаны: широкие бёдра, затем штанины.
    c.spans(PANTS_HIPS, "pants")
    c.spans(PANTS_LEG_L, "pants")
    c.spans(PANTS_LEG_R, "pants")
    # Складки ткани: диагональные потёртости и тень в глубине, без ровных полос.
    c.spans([(27, 11, 12), (28, 10, 11), (29, 10, 10)], "pants_hi")
    c.spans([(30, 13, 14), (31, 14, 15)], "pants_hi")
    c.spans([(28, 19, 20), (29, 20, 21)], "pants_dark")
    c.column(21, 27, 33, "pants_dark")
    c.column(10, 31, 33, "pants_dark")
    c.span(33, 15, 16, "pants_dark")
    # Штанины: внутренние швы и объём.
    c.column(14, 34, 38, "pants_dark")
    c.column(17, 34, 38, "pants_dark")
    c.spans([(35, 10, 11), (36, 10, 11), (37, 11, 12)], "pants_hi")
    c.spans([(34, 20, 21), (35, 20, 21)], "pants_dark")
    c.spans([(37, 13, 14), (38, 18, 19)], "pants_hi")
    # Рваный край: зубцы разной длины вместо линейки.
    for x in (9, 11, 13, 18, 20, 22):
        c.erase(x, 38)
    c.span(38, 10, 12, "pants_dark")
    c.span(38, 19, 21, "pants_dark")

    # Обмотки голеней: полосы ткани.
    c.spans(SHIN_L, "wrap")
    c.spans(SHIN_R, "wrap")
    for y in (39, 41, 43):
        c.spans([(y, 11, 14), (y, 17, 20)], "wrap_hi")
    c.spans([(40, 11, 14), (40, 17, 20)], "wrap_dark")
    c.spans([(44, 11, 14), (44, 17, 20)], "wrap_dark")

    # Босые стопы: шире голени, пальцы обозначены тенью.
    c.spans(FOOT_L, "skin")
    c.spans(FOOT_R, "skin")
    c.span(45, 10, 13, "skin_hi")
    c.span(45, 18, 21, "skin_hi")
    c.span(46, 9, 14, "skin_mid")
    c.span(46, 17, 22, "skin_mid")
    c.put(11, 46, "skin_dark")
    c.put(13, 46, "skin_dark")
    c.put(18, 46, "skin_dark")
    c.put(20, 46, "skin_dark")


def draw_arms(c: Canvas) -> None:
    """Руки: дельтовидная, плечо, предплечье в обмотке, кисть.

    Руки следуют сужению талии: на уровне груди они шире и отстоят от корпуса,
    на уровне талии сдвигаются внутрь на 1 px. Зазор заполняет контур — он читается
    как тень между рукой и корпусом, а не как ремень.
    """
    # Плечо и предплечье на уровне груди.
    c.spans([(y, 7, 9) for y in range(14, 20)], "skin")
    c.spans([(y, 22, 24) for y in range(14, 20)], "skin")
    c.column(7, 14, 26, "skin_hi")
    c.column(24, 14, 26, "skin_dark")
    c.column(23, 14, 19, "skin_mid")
    c.column(9, 17, 19, "skin_mid")
    # Локоть: строка между плечом и обмоткой, чтобы рука читалась по членениям.
    c.spans([(19, 7, 9), (19, 22, 24)], "skin_mid")
    # Предплечья сдвинуты внутрь вслед за талией.
    c.spans([(y, 8, 10) for y in range(20, 25)], "wrap")
    c.spans([(y, 21, 23) for y in range(20, 25)], "wrap")
    c.column(8, 20, 24, "wrap_hi")
    c.column(23, 20, 24, "wrap_dark")
    c.spans([(20, 8, 10), (20, 21, 23)], "wrap_hi")
    c.spans([(22, 8, 10), (22, 21, 23)], "wrap_dark")
    c.spans([(24, 8, 10), (24, 21, 23)], "wrap_dark")
    # Кисти.
    c.spans([(25, 8, 10), (26, 8, 10)], "skin_mid")
    c.spans([(25, 21, 23), (26, 21, 23)], "skin_mid")
    c.put(8, 25, "skin")
    c.put(23, 25, "skin")


def draw_sash(c: Canvas) -> None:
    """Красный кушак: широкий пояс в три ряда, как на референсе."""
    c.spans([(24, 11, 20), (25, 11, 20), (26, 11, 20)], "red")
    c.span(24, 12, 19, "red_hi")
    c.span(25, 11, 20, "red")
    c.span(26, 11, 20, "red_dark")
    c.put(11, 24, "red_dark")
    c.put(20, 26, "red_dark")


def draw_torso(c: Canvas, *, back: bool) -> None:
    """Плечи, грудная клетка и талия: общая часть спереди и сзади."""
    # Плечи: скос от шеи к дельтовидным, затем широкий дельтовидный пояс.
    c.span(11, 12, 19, "skin_mid")
    c.span(12, 9, 22, "skin")
    c.span(13, 7, 24, "skin")
    c.span(12, 10, 13, "skin_hi")
    c.span(12, 18, 21, "skin_hi")
    c.span(13, 7, 9, "skin_hi")
    c.span(13, 22, 24, "skin_hi")

    # Грудь и талия.
    c.spans(CHEST, "skin")
    c.spans(WAIST, "skin")

    if back:
        # Спина: позвоночник до лопаток, тени по бокам, насечки вместо полос.
        c.span(14, 12, 13, "skin_hi")
        c.span(14, 18, 19, "skin_hi")
        c.span(15, 12, 13, "skin_mid")
        c.span(15, 18, 19, "skin_mid")
        c.column(15, 16, 21, "skin_mid")
        c.column(16, 16, 21, "skin_dark")
        c.column(11, 20, 23, "skin_mid")
        c.column(20, 20, 23, "skin_dark")
        c.spans([(18, 12, 14), (18, 17, 19)], "skin_hi")
    else:
        # Грудь: две грудные массы с тенью под ними и короткой бороздой по центру.
        c.span(14, 12, 14, "skin_hi")
        c.span(14, 17, 19, "skin_hi")
        c.column(15, 14, 17, "skin_mid")
        c.column(16, 14, 17, "skin_mid")
        c.span(18, 11, 14, "skin_mid")
        c.span(18, 17, 20, "skin_mid")
        c.column(11, 19, 23, "skin_mid")
        c.column(20, 19, 23, "skin_dark")


# --- вид спереди (down) -----------------------------------------------------

DOWN_HAIR = [
    (0, 14, 17),
    (1, 13, 18),
    (2, 11, 20),
    (3, 10, 21),
    (4, 10, 21),
    (5, 10, 21),
    (6, 10, 21),
    (7, 10, 21),
    (8, 10, 21),
    (9, 11, 20),
]


def draw_down() -> Canvas:
    c = Canvas()
    # Волосы: объёмная масса с неровным контуром, а не шлем.
    c.spans(DOWN_HAIR, "hair")
    c.spans([(1, 14, 16), (2, 12, 14), (3, 11, 12)], "hair_hi")
    c.spans([(1, 17, 18), (2, 17, 18)], "hair_hi")
    c.column(16, 1, 3, "hair_dark")
    c.column(19, 2, 4, "hair_dark")
    c.put(12, 3, "hair_dark")
    # Выступающие локоны по краям массы.
    c.put(9, 3, "hair")
    c.put(9, 4, "hair_dark")
    c.put(22, 5, "hair")
    c.put(22, 6, "hair_dark")
    # Кончики прядей у шеи: рваный низ вместо ровной линии.
    c.put(11, 9, "hair_dark")
    c.put(20, 9, "hair_dark")
    c.put(12, 9, "hair")
    c.put(19, 9, "hair")

    # Лицо: видна только нижняя половина — глаза закрыты повязкой.
    c.spans([(6, 12, 19), (7, 12, 19), (8, 13, 18)], "skin")
    c.column(12, 6, 8, "skin_mid")
    c.column(19, 6, 8, "skin_mid")
    c.span(6, 13, 18, "skin_hi")
    c.put(15, 7, "skin_mid")
    c.put(16, 7, "skin_mid")
    c.span(8, 15, 16, "skin_dark")

    # Красная повязка на глазах — главный опознавательный элемент.
    c.spans([(4, 11, 20), (5, 11, 20)], "red")
    c.span(4, 12, 19, "red_hi")
    c.span(5, 11, 20, "red_dark")
    # Узел на виске и два сужающихся конца ткани.
    c.spans([(4, 21, 22), (5, 21, 22)], "red")
    c.put(21, 4, "red_hi")
    c.put(22, 5, "red_dark")
    c.spans([(3, 23, 25)], "red")
    c.put(26, 2, "red")
    c.put(26, 3, "red_dark")
    c.spans([(6, 23, 25)], "red")
    c.put(26, 7, "red_dark")

    # Шея.
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


# --- вид сзади (up) ---------------------------------------------------------

UP_HAIR = [
    (0, 14, 17),
    (1, 13, 18),
    (2, 11, 20),
    (3, 10, 21),
    (4, 10, 21),
    (5, 10, 21),
    (6, 10, 21),
    (7, 10, 21),
    (8, 10, 21),
    (9, 10, 21),
]


def draw_up() -> Canvas:
    c = Canvas()
    # Затылок: волосы закрывают голову целиком, лицо не видно.
    c.spans(UP_HAIR, "hair")
    c.spans([(1, 14, 16), (2, 12, 14), (3, 11, 12), (4, 11, 11)], "hair_hi")
    # Пряди: диагональные тёмные линии, а не вертикальные полосы.
    c.spans([(2, 16, 16), (3, 17, 17), (4, 18, 18)], "hair_dark")
    c.spans([(6, 12, 12), (7, 12, 12), (8, 13, 13)], "hair_dark")
    c.spans([(6, 19, 19), (7, 20, 20), (8, 20, 20)], "hair_dark")
    c.put(9, 3, "hair")
    c.put(22, 5, "hair")
    # Неровные кончики волос, не «шлем»: часть пикселей нижнего ряда убрана.
    for x in (10, 12, 15, 19, 21):
        c.erase(x, 9)
    c.put(10, 9, "hair_dark")
    c.put(13, 9, "hair")
    c.put(18, 9, "hair")
    c.put(21, 9, "hair_dark")

    # Узел повязки на затылке и два свисающих конца (референс, вид сзади).
    c.spans([(5, 14, 17), (6, 14, 17)], "red")
    c.put(15, 5, "red_hi")
    c.put(16, 6, "red_dark")
    c.spans([(7, 14, 14), (8, 14, 14), (9, 13, 13), (10, 13, 13)], "red")
    c.spans([(7, 17, 17), (8, 17, 17), (9, 18, 18), (10, 18, 18)], "red")
    c.put(13, 10, "red_dark")
    c.put(18, 10, "red_dark")

    # Шея и плечи.
    c.span(9, 14, 17, "skin_mid")
    c.span(10, 14, 17, "skin_dark")
    draw_torso(c, back=True)
    draw_arms(c)
    draw_sash(c)
    draw_legs(c)

    # Узел кушака сзади с двумя концами.
    c.spans([(27, 17, 18), (28, 17, 18), (29, 18, 19), (30, 19, 20)], "red")
    c.put(17, 27, "red_hi")

    c.outline_outward()
    return c


# --- вид в профиль (left) ---------------------------------------------------
#
# Боковых видов на утверждённом референсе нет: это рабочая художественная
# интерпретация до просмотра владельцем (см. STAGE_03.md §8).

LEFT_HAIR = [
    (0, 14, 17),
    (1, 12, 18),
    (2, 11, 19),
    (3, 10, 20),
    (4, 10, 21),
    (5, 10, 21),
    (6, 15, 21),
    (7, 15, 21),
    (8, 15, 20),
    (9, 16, 19),
]


def draw_left() -> Canvas:
    c = Canvas()
    # Волосы: спереди прядь на лицо, сзади объёмная масса ниже уха.
    c.spans(LEFT_HAIR, "hair")
    c.spans([(1, 13, 16), (2, 12, 15), (3, 11, 13)], "hair_hi")
    c.spans([(4, 20, 21), (5, 20, 21), (6, 20, 21)], "hair_dark")
    c.put(19, 8, "hair_dark")
    c.put(21, 3, "hair")
    c.put(16, 9, "hair_dark")

    # Профиль: лоб закрыт повязкой, видны нос, губы, подбородок.
    c.spans([(6, 8, 13), (7, 9, 13), (8, 10, 13)], "skin")
    c.put(8, 6, "skin_hi")
    c.put(8, 7, "skin_hi")
    c.put(10, 8, "skin_mid")
    c.put(13, 6, "skin_mid")
    c.put(13, 8, "skin_mid")

    # Повязка через глаз, узел у виска и конец, уходящий назад.
    c.spans([(4, 11, 20), (5, 11, 20)], "red")
    c.span(4, 12, 19, "red_hi")
    c.span(5, 11, 20, "red_dark")
    c.spans([(4, 21, 22), (5, 21, 22)], "red")
    c.put(22, 4, "red_dark")
    c.spans([(3, 23, 24)], "red")
    c.put(25, 2, "red_dark")
    c.spans([(6, 23, 23)], "red_dark")

    # Шея и плечо в профиль.
    c.span(9, 12, 15, "skin_mid")
    c.span(10, 12, 16, "skin_dark")
    c.span(11, 11, 19, "skin")
    c.span(12, 10, 20, "skin")
    c.span(13, 10, 20, "skin")
    c.span(12, 11, 18, "skin_hi")

    # Торс в профиль: грудь слева (лицом влево), спина справа.
    c.spans([(y, 11, 20) for y in range(14, 20)], "skin")
    c.spans([(y, 12, 19) for y in range(20, 25)], "skin")
    c.column(11, 14, 19, "skin_hi")
    c.column(20, 14, 24, "skin_dark")
    c.column(19, 20, 24, "skin_mid")
    c.put(12, 17, "skin_dark")

    # Кушак рисуется до руки: кисть должна остаться поверх пояса.
    c.spans([(25, 11, 20), (26, 11, 20)], "red")
    c.span(25, 12, 19, "red_hi")
    c.span(26, 11, 20, "red_dark")

    # Ближняя рука висит перед корпусом: её передняя кромка — край силуэта.
    c.spans([(y, 9, 11) for y in range(14, 20)], "skin")
    c.column(9, 14, 19, "skin_hi")
    c.column(12, 14, 26, "skin_mid")
    c.spans([(y, 9, 11) for y in range(20, 25)], "wrap")
    c.span(20, 9, 11, "wrap_hi")
    c.column(11, 20, 24, "wrap_dark")
    c.span(23, 9, 11, "wrap_dark")
    c.spans([(25, 9, 11), (26, 9, 11)], "skin_mid")
    c.put(9, 26, "skin")

    # Кушак: свисающий спереди конец.
    c.spans([(27, 10, 11), (28, 10, 11), (29, 9, 10)], "red")

    # Свободные штаны в профиль: широкие бёдра, сзади виден изгиб.
    c.spans([(y, 10, 21) for y in range(27, 34)], "pants")
    c.spans([(y, 10, 20) for y in range(34, 39)], "pants")
    c.span(27, 11, 14, "pants_hi")
    c.span(28, 11, 13, "pants_hi")
    c.column(21, 27, 33, "pants_dark")
    c.column(20, 30, 33, "pants_dark")
    c.column(10, 31, 38, "pants_dark")
    c.column(15, 34, 38, "pants_dark")
    c.column(16, 34, 38, "pants_dark")
    c.erase(10, 38)
    c.erase(20, 38)
    c.span(38, 11, 19, "pants_dark")

    # Передняя и задняя голень, стопы.
    c.spans([(y, 11, 14) for y in range(39, 45)], "wrap")
    c.spans([(y, 17, 20) for y in range(39, 45)], "wrap")
    for y in (39, 41, 43):
        c.spans([(y, 11, 14), (y, 17, 20)], "wrap_hi")
    c.spans([(40, 11, 14), (40, 17, 20)], "wrap_dark")
    c.spans([(44, 11, 14), (44, 17, 20)], "wrap_dark")
    # Передняя стопа выдвинута вперёд (влево) — читается направление.
    c.spans([(45, 8, 14), (46, 7, 14)], "skin")
    c.spans([(45, 17, 20), (46, 17, 21)], "skin_mid")
    c.span(45, 9, 13, "skin_hi")
    c.span(46, 8, 13, "skin_mid")
    c.put(10, 46, "skin_dark")
    c.put(18, 46, "skin_dark")

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
