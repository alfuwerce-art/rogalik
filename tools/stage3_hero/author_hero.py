"""Автор первого игрового силуэта героя (Этап 3, задача 3.1).

Что делает
----------
Рисует героя 48 px по утверждённому референсу (D7, HERO_REFERENCE.md) в четырёх
направлениях и двух кадрах `idle`, собирает лист-источник PNG и строит из него
настоящий проект Pixelorama `.pxo` через пайплайн (`tools/pixel_pipeline/pxo.py`).
Дальше `.pxo` экспортируется **самим Pixelorama CLI**
(`python -m pixel_pipeline.cli export`), и уже этот экспорт идёт в игру.

Почему рисунок задан таблицами пикселей
---------------------------------------
Спрайт такого размера нельзя получить масштабированием живописного референса:
уменьшение 1536x1024 даёт мыло, а не пиксель-арт. Поэтому силуэт собран из явно
заданных горизонтальных пробегов и точечных деталей — повязка, волосы, шрамы,
обмотки, рваный край штанов. Никакого шума, случайности и авто-даунскейла:
каждый пиксель задан вручную.

Соглашения
----------
* кадр 32x48, герой 48 px по высоте (D16), опорная точка — середина стоп;
* части тела разделяются **прозрачным зазором в 1 px**: контур, который
  дорисовывается наружу (`outline_outward`), заполняет его тёмным и работает как
  внутренняя обводка конечности. Так рука не сливается с торсом, а ноги — друг с
  другом (обычный приём пиксель-арта такого размера);
* нижняя строка кадра — подошва контура; она одинакова во всех восьми кадрах;
* кадр `idle` B — тот же рисунок со сдвигом головы и плеч на 1 px (вдох);
  стопы, штаны и опорная точка не двигаются;
* свет условно сверху-слева: блик на левой/верхней кромке, тень на правой/нижней.

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

# Палитра: тёмная кожа + серо-бурые ткани + красный акцент
# (PIXEL_ART_STYLE_GUIDE §4, HERO_REFERENCE §«Палитра»).
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
        """Копия со сдвигом головы и плеч (дыхание) при неподвижных бёдрах и ногах."""
        result = Canvas(self.width, self.height)
        for (x, y), key in self.pixels.items():
            result.put(x, y + dy if y <= max_y else y, key)
        return result

    def to_image(self) -> Image.Image:
        image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        for (x, y), key in self.pixels.items():
            image.putpixel((x, y), rgba(key))
        return image


# --- общая нижняя половина (спереди и сзади) --------------------------------
#
# Горизонталь кадра 32 px, центр между x15 и x16:
#   руки            x8..9  и x22..23   (зазор x10 / x21 заполняет контур)
#   торс            x11..20
#   бёдра/штаны     x10..21
#   штанины         x10..14 и x17..21  (зазор x15..16)
#   голени          x11..14 и x17..20

PANTS_HIPS = [(y, 10, 21) for y in range(28, 34)]
PANTS_LEG_L = [(y, 10, 14) for y in range(34, 38)]
PANTS_LEG_R = [(y, 17, 21) for y in range(34, 38)]
SHIN_L = [(y, 11, 14) for y in range(38, 45)]
SHIN_R = [(y, 17, 20) for y in range(38, 45)]
FOOT_L = [(45, 10, 15), (46, 9, 15)]
FOOT_R = [(45, 16, 21), (46, 16, 22)]


def draw_legs(c: Canvas) -> None:
    """Штаны, обмотки голеней и босые стопы — одинаково спереди и сзади."""
    c.spans(PANTS_HIPS, "pants")
    c.spans(PANTS_LEG_L, "pants")
    c.spans(PANTS_LEG_R, "pants")
    # Складки и свет: слева сверху светлее, справа тень.
    c.spans([(28, 11, 13), (29, 11, 12), (30, 10, 12), (31, 10, 11)], "pants_hi")
    c.column(21, 28, 33, "pants_dark")
    c.column(20, 30, 33, "pants_dark")
    c.column(10, 31, 33, "pants_dark")
    c.column(13, 34, 37, "pants_dark")
    c.column(18, 34, 37, "pants_dark")
    c.spans([(33, 14, 17)], "pants_dark")
    # Рваный низ: зубцы разной длины вместо линейки.
    for x, y in ((10, 37), (12, 37), (21, 37), (19, 37), (14, 36), (17, 36)):
        c.erase(x, y)
    c.spans([(37, 10, 13), (37, 18, 21)], "pants_dark")
    c.span(37, 14, 14, "pants")
    c.span(37, 17, 17, "pants")

    # Обмотки голеней: полосы ткани.
    c.spans(SHIN_L, "wrap")
    c.spans(SHIN_R, "wrap")
    for y in (39, 41, 43):
        c.spans([(y, 11, 14), (y, 17, 20)], "wrap_hi")
    c.spans([(40, 11, 14), (40, 17, 20)], "wrap_dark")
    c.spans([(44, 11, 14), (44, 17, 20)], "wrap_dark")

    # Босые стопы.
    c.spans(FOOT_L, "skin")
    c.spans(FOOT_R, "skin")
    c.span(45, 11, 14, "skin_hi")
    c.span(45, 17, 20, "skin_hi")
    c.span(46, 10, 15, "skin_mid")
    c.span(46, 16, 21, "skin_mid")
    c.put(13, 46, "skin_dark")
    c.put(19, 46, "skin_dark")


def draw_arms(c: Canvas) -> None:
    """Руки: плечо, предплечье в обмотке, кисть. Отделены от торса зазором."""
    c.spans([(y, 8, 9) for y in range(17, 22)], "skin")
    c.spans([(y, 22, 23) for y in range(17, 22)], "skin")
    c.column(8, 17, 25, "skin_hi")
    c.column(23, 17, 25, "skin_dark")
    c.column(22, 17, 21, "skin_mid")
    c.column(9, 20, 21, "skin_mid")
    # Обмотки на предплечьях.
    c.spans([(y, 8, 9) for y in range(22, 26)], "wrap")
    c.spans([(y, 22, 23) for y in range(22, 26)], "wrap")
    c.column(8, 22, 25, "wrap_hi")
    c.column(23, 22, 25, "wrap_dark")
    c.spans([(23, 8, 9), (23, 22, 23)], "wrap_hi")
    c.spans([(24, 8, 9), (24, 22, 23)], "wrap_dark")
    c.spans([(25, 8, 9), (25, 22, 23)], "wrap")
    # Кисти.
    c.spans([(26, 8, 9), (27, 8, 9)], "skin_mid")
    c.spans([(26, 22, 23), (27, 22, 23)], "skin_mid")
    c.put(8, 26, "skin")
    c.put(23, 26, "skin")


def draw_sash(c: Canvas) -> None:
    """Красный кушак: широкий пояс с подвёрнутым верхом."""
    c.spans([(26, 10, 21), (27, 10, 21)], "red")
    c.span(26, 11, 20, "red_hi")
    c.span(27, 11, 20, "red_dark")
    c.put(10, 26, "red_dark")
    c.put(21, 27, "red_dark")


# --- вид спереди (down) -----------------------------------------------------

DOWN_HAIR = [
    (0, 14, 17),
    (1, 12, 19),
    (2, 11, 20),
    (3, 10, 21),
    (4, 10, 21),
    (5, 10, 21),
    (6, 10, 21),
    (7, 10, 21),
    (8, 10, 21),
    (9, 10, 21),
    (10, 10, 21),
    (11, 10, 21),
]


def draw_down() -> Canvas:
    c = Canvas()
    # Волосы: объёмная масса, одинаковая спереди и сзади (D7), с прядями на лицо.
    c.spans(DOWN_HAIR, "hair")
    # Блики по направлению прядей и тёмные кончики: масса не должна быть пятном.
    c.spans([(1, 13, 17), (2, 12, 15), (3, 11, 13), (4, 10, 11)], "hair_hi")
    c.spans([(1, 18, 19), (2, 18, 19), (3, 16, 17)], "hair_hi")
    c.put(21, 5, "hair_dark")
    c.put(10, 7, "hair_dark")
    c.put(10, 11, "hair_dark")
    c.put(21, 11, "hair_dark")
    c.put(11, 12, "hair")
    c.put(20, 12, "hair")
    c.put(12, 12, "hair_dark")
    c.put(19, 12, "hair_dark")

    # Лицо: видна только нижняя половина — глаза закрыты повязкой.
    c.spans([(8, 12, 19), (9, 12, 19), (10, 12, 19), (11, 13, 18)], "skin")
    c.span(8, 13, 18, "skin_hi")
    c.column(12, 8, 11, "skin_mid")
    c.column(19, 8, 11, "skin_mid")
    c.put(15, 10, "skin_mid")
    c.put(16, 10, "skin_mid")
    c.span(11, 15, 16, "skin_dark")

    # Красная повязка на глазах — смысловой центр силуэта.
    c.spans([(5, 11, 20), (6, 11, 20), (7, 11, 20)], "red")
    c.span(5, 13, 18, "red_hi")
    c.span(7, 12, 19, "red_dark")
    c.put(11, 5, "red_hi")
    # Тонкие развевающиеся концы: начинаются у кромки волос, а не в воздухе.
    c.spans([(5, 21, 22), (4, 22, 23), (3, 23, 24)], "red")
    c.spans([(7, 21, 22), (8, 22, 23)], "red")
    c.put(24, 3, "red_dark")
    c.put(23, 8, "red_dark")

    # Шея.
    c.span(12, 14, 17, "skin_mid")
    c.span(13, 14, 17, "skin_dark")

    # Плечи: скос от шеи к дельтовидным, скруглённые наружные углы.
    c.span(14, 11, 20, "skin_mid")
    c.span(15, 9, 22, "skin")
    c.span(16, 8, 23, "skin")
    c.span(15, 10, 13, "skin_hi")
    c.span(15, 18, 21, "skin_hi")
    c.erase(8, 16)
    c.erase(23, 16)

    # Торс: только крупные массы — борозда по центру, тень под грудью,
    # одна линия пресса и боковые тени. Мелкая «сетка» мышц на 10 px ширины
    # распадается в полосы, поэтому детализация намеренно ограничена.
    c.spans([(y, 11, 20) for y in range(17, 26)], "skin")
    c.span(17, 12, 13, "skin_hi")
    c.span(17, 18, 19, "skin_hi")
    c.column(15, 17, 19, "skin_mid")
    c.column(16, 17, 19, "skin_mid")
    c.span(20, 11, 14, "skin_mid")
    c.span(20, 17, 20, "skin_mid")
    c.column(15, 21, 25, "skin_mid")
    c.column(16, 21, 25, "skin_mid")
    c.column(11, 21, 25, "skin_mid")
    c.column(20, 21, 25, "skin_dark")
    # Шрам через грудь: из референса переносятся только крупные детали.
    c.put(13, 18, "skin_dark")
    c.put(14, 19, "skin_dark")

    draw_arms(c)
    draw_sash(c)
    draw_legs(c)

    # Кушак: узел спереди слева и свисающие концы.
    c.spans([(28, 11, 12), (29, 12, 13), (30, 12, 13), (31, 11, 12)], "red")
    c.put(13, 29, "red_hi")
    c.put(11, 31, "red_dark")

    c.outline_outward()
    return c


# --- вид сзади (up) ---------------------------------------------------------

UP_HAIR = DOWN_HAIR


def draw_up() -> Canvas:
    c = Canvas()
    # Затылок: волосы закрывают голову целиком, лицо не видно.
    c.spans(UP_HAIR, "hair")
    c.spans([(1, 13, 18), (2, 12, 17), (3, 11, 16), (4, 11, 15)], "hair_hi")
    c.spans([(y, 20, 21) for y in range(4, 10)], "hair_dark")
    c.spans([(y, 10, 11) for y in range(6, 12)], "hair_dark")
    # Неровные кончики волос: масса не должна выглядеть шлемом.
    c.put(12, 12, "hair")
    c.put(19, 12, "hair")
    c.put(11, 12, "hair_dark")
    c.put(20, 12, "hair_dark")

    # Узел повязки на затылке и два свисающих конца (референс, вид сзади).
    c.span(8, 15, 16, "red")
    c.span(9, 14, 17, "red")
    c.put(15, 8, "red_hi")
    c.put(17, 9, "red_dark")
    c.spans([(10, 14, 14), (11, 14, 14), (12, 13, 14)], "red")
    c.spans([(10, 17, 17), (11, 17, 17), (12, 17, 18)], "red")
    c.put(13, 12, "red_dark")
    c.put(18, 12, "red_dark")

    # Шея и плечи.
    c.span(12, 14, 17, "skin_mid")
    c.span(13, 14, 17, "skin_dark")
    c.span(14, 11, 20, "skin")
    c.span(15, 9, 22, "skin")
    c.span(16, 8, 23, "skin")
    c.span(15, 10, 13, "skin_hi")
    c.span(15, 18, 21, "skin_hi")
    c.erase(8, 16)
    c.erase(23, 16)

    # Спина: позвоночник, лопатки одной полосой, тени по бокам.
    c.spans([(y, 11, 20) for y in range(17, 26)], "skin")
    c.span(17, 12, 13, "skin_hi")
    c.span(17, 18, 19, "skin_hi")
    c.span(18, 12, 13, "skin_mid")
    c.span(18, 18, 19, "skin_mid")
    c.column(15, 18, 25, "skin_mid")
    c.column(16, 18, 25, "skin_dark")
    c.column(11, 21, 25, "skin_mid")
    c.column(20, 21, 25, "skin_dark")
    c.put(13, 24, "skin_dark")
    c.put(18, 24, "skin_dark")

    draw_arms(c)
    draw_sash(c)
    draw_legs(c)

    # Узел кушака сзади.
    c.spans([(28, 18, 19), (29, 18, 19), (30, 19, 20)], "red")
    c.put(19, 29, "red_hi")

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
    (6, 10, 21),
    (7, 10, 21),
    (8, 15, 21),
    (9, 16, 21),
    (10, 16, 20),
    (11, 17, 20),
    (12, 17, 19),
]


def draw_left() -> Canvas:
    c = Canvas()
    # Волосы: спереди прядь на лицо, сзади объёмная масса ниже уха.
    c.spans(LEFT_HAIR, "hair")
    c.spans([(1, 13, 17), (2, 12, 16), (3, 11, 15)], "hair_hi")
    c.spans([(4, 20, 21), (5, 20, 21), (6, 20, 21), (7, 20, 21)], "hair_dark")
    c.put(17, 12, "hair_dark")
    c.put(20, 11, "hair_dark")

    # Профиль лица: нос, губы, подбородок.
    c.spans([(8, 10, 14), (9, 10, 14), (10, 11, 14)], "skin")
    c.put(9, 8, "skin_hi")
    c.put(9, 9, "skin_hi")
    c.put(10, 10, "skin_mid")
    c.put(11, 11, "skin_dark")
    c.put(14, 8, "skin_mid")
    c.put(14, 10, "skin_mid")

    # Повязка через глаз и конец, уходящий назад.
    c.spans([(5, 11, 20), (6, 11, 20), (7, 11, 20)], "red")
    c.span(5, 13, 18, "red_hi")
    c.span(7, 12, 19, "red_dark")
    c.spans([(6, 21, 22), (5, 22, 23)], "red")
    c.spans([(8, 21, 22), (9, 22, 23)], "red")
    c.put(23, 5, "red_dark")
    c.put(23, 9, "red_dark")

    # Шея и плечо в профиль.
    c.span(11, 12, 15, "skin_mid")
    c.span(12, 12, 16, "skin_mid")
    c.span(13, 12, 16, "skin_dark")
    c.span(14, 11, 19, "skin")
    c.span(15, 10, 20, "skin")
    c.span(16, 10, 20, "skin")
    c.span(15, 11, 18, "skin_hi")

    # Торс в профиль: грудь слева (лицом влево), спина справа.
    c.spans([(y, 12, 20) for y in range(14, 21)], "skin")
    c.spans([(y, 12, 20) for y in range(21, 26)], "skin")
    c.column(12, 17, 25, "skin")
    c.column(20, 17, 25, "skin_dark")
    c.column(19, 20, 25, "skin_mid")
    c.put(12, 17, "skin_hi")
    c.put(12, 18, "skin_hi")
    c.put(13, 19, "skin_dark")

    # Кушак рисуется до руки: кисть должна остаться поверх пояса.
    c.spans([(26, 11, 20), (27, 11, 20)], "red")
    c.span(26, 12, 19, "red_hi")
    c.span(27, 11, 20, "red_dark")

    # Ближняя рука висит перед корпусом: её передняя кромка — край силуэта.
    # Обмотка короткая (2 ряда), иначе предплечье читается как сумка на боку.
    c.spans([(y, 10, 12) for y in range(18, 24)], "skin")
    c.column(10, 18, 25, "skin_hi")
    c.column(13, 18, 28, "skin_mid")
    c.spans([(24, 10, 12), (25, 10, 12)], "wrap")
    c.span(24, 10, 12, "wrap_hi")
    c.span(25, 10, 12, "wrap_dark")
    c.spans([(26, 10, 12), (27, 10, 12)], "skin_mid")
    c.put(10, 26, "skin")

    # Бёдра в профиль: спереди ткань свисает ниже, сзади виден изгиб.
    c.spans([(y, 11, 21) for y in range(28, 34)], "pants")
    c.spans([(y, 11, 20) for y in range(34, 38)], "pants")
    c.span(28, 12, 14, "pants_hi")
    c.span(29, 12, 13, "pants_hi")
    c.column(21, 28, 33, "pants_dark")
    c.column(11, 32, 37, "pants_dark")
    c.column(15, 34, 37, "pants_dark")
    c.column(16, 34, 37, "pants_dark")
    c.erase(11, 37)
    c.erase(20, 37)
    c.span(37, 12, 20, "pants_dark")

    # Передняя и задняя голень, стопы.
    c.spans([(y, 12, 15) for y in range(38, 45)], "wrap")
    c.spans([(y, 17, 20) for y in range(38, 45)], "wrap")
    for y in (39, 41, 43):
        c.spans([(y, 12, 15), (y, 17, 20)], "wrap_hi")
    c.spans([(40, 12, 15), (40, 17, 20)], "wrap_dark")
    c.spans([(44, 12, 15), (44, 17, 20)], "wrap_dark")
    # Передняя стопа выдвинута вперёд (влево) — читается направление.
    c.spans([(45, 9, 15), (46, 8, 15)], "skin")
    c.spans([(45, 17, 20), (46, 17, 21)], "skin_mid")
    c.span(45, 10, 14, "skin_hi")
    c.span(46, 9, 14, "skin_mid")
    c.put(12, 46, "skin_dark")
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
    # idle B: вдох — голова и плечи опускаются на 1 px,
    # стопы и штаны остаются на месте (опорная точка не «прыгает»).
    for name, canvas in (("down", down), ("up", up), ("left", left), ("right", right)):
        frames[name] = [canvas, canvas.shifted_head(max_y=12, dy=1)]
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
