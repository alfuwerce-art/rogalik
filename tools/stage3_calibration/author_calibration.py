"""Автор художественного калибровочного набора (Этап 3, задача 3.1b).

Что рисуется
------------
Один небольшой, но качественный вертикальный художественный срез ночной
древнерусской деревни на сетке D16 (тайл 24 px):

* модульный тайлсет земли и настила (мокрая земля, камень, доски);
* изба — сруб с тёплыми окнами, резными наличниками, крыльцом и фундаментом;
* часовня — фрагмент белокаменной стены с резным поясом, кокошниками и порталом;
* частокол, воротная башня-врата, силуэт ночного леса за ними;
* мёртвое дерево с навязанными красными лоскутами;
* факельный столб (2 кадра огня), полотнище-знамя, лужи с отражениями;
* атмосферные текстуры: тёплое и холодное свечение, туман, виньетка.

Это **не** финальный арт игры и не утверждённая локация: статус набора
`ASSET_DRAFT`, калибровочный кадр — ориентир для задачи 3.2 (анимация движения).

Почему так, а не «нарисовать красиво в редакторе»
------------------------------------------------
Уменьшение живописного look-референса даёт мыло, а не пиксель-арт. Поэтому каждый
ассет собран из примитивов на точной сетке (`pxcanvas.Canvas`) с детерминированной
случайностью: повторная сборка даёт байт-в-байт те же PNG. Затем каждый PNG
проходит настоящий Pixelorama-пайплайн (`export_assets.py`): PNG → `.pxo` →
экспорт **CLI Pixelorama** → игровой PNG.

Запуск:
    python tools/stage3_calibration/author_calibration.py --out tools/stage3_calibration/source
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from PIL import Image

from pxcanvas import CLEAR, PAL, Canvas, bayer, contact_shadow, fog_layer, glow_radial, vignette

TILE = 24


# ---------------------------------------------------------------------------
# Земля и настил: 8 тайлов 24 px в атласе 4x2
# ---------------------------------------------------------------------------

T_EARTH_A = 0
T_EARTH_B = 1
T_EARTH_C = 2
T_PATH_A = 3
T_PATH_B = 4
T_PLANKS = 5
T_PLANKS_WET = 6
T_CURB = 7


def _tile_canvas(atlas: Canvas, index: int) -> Canvas:
    tile = Canvas(TILE, TILE)
    ox = (index % 4) * TILE
    oy = (index // 4) * TILE
    for (x, y), color in atlas.px.items():
        if ox <= x < ox + TILE and oy <= y < oy + TILE:
            tile.put(x - ox, y - oy, color)
    return tile


def _paste_tile(atlas: Canvas, tile: Canvas, index: int) -> None:
    ox = (index % 4) * TILE
    oy = (index // 4) * TILE
    atlas.composite(tile, ox, oy)


def _blob(
    tile: Canvas,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    color,
    level_scale: int = 8,
    edge=None,
) -> None:
    """Пятно с чётким краем и необязательной каймой.

    На 24 px тайле дизеринг края читается как «телевизионный шум» и превращает
    землю в повторяющийся узор, поэтому пятно заливается ровно, а переход
    задаётся одним рядом пикселей по границе.
    """
    inside = []
    for y in range(1, tile.height - 1):
        for x in range(1, tile.width - 1):
            if ((x - cx) / max(0.1, rx)) ** 2 + ((y - cy) / max(0.1, ry)) ** 2 < 1.0:
                inside.append((x, y))
    for (x, y) in inside:
        tile.put(x, y, color)
    if edge is None:
        return
    inside_set = set(inside)
    for (x, y) in inside:
        if any(
            (x + dx, y + dy) not in inside_set
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            tile.put(x, y, edge)


def _earth_tile(seed: int, *, grass: bool = False, stones: int = 0, wet: bool = False) -> Canvas:
    """Мокрая земля: тихая тёмная поверхность с крупными мягкими пятнами.

    На 24 px любая мелкая «фактура» превращается в повторяющийся узор, поэтому
    земля намеренно спокойная: два крупных пятна близкого тона, солома, редкие
    крапины. Внимание в кадре должны держать свет, лужи и постройки, а не земля.
    """
    rng = random.Random(seed)
    tile = Canvas(TILE, TILE)
    tile.fill(PAL["earth"])
    _blob(tile, rng.uniform(4, 20), rng.uniform(4, 20), rng.uniform(8, 11), rng.uniform(6, 9), PAL["earth_d"], edge=PAL["earth"])
    _blob(tile, rng.uniform(4, 20), rng.uniform(4, 20), rng.uniform(6, 9), rng.uniform(4, 7), PAL["earth_m"], edge=PAL["earth"])
    if wet:
        _blob(tile, rng.uniform(8, 16), rng.uniform(8, 16), rng.uniform(5, 7), rng.uniform(3, 4), PAL["water"], edge=PAL["earth_d"])
    # Солома: короткие сгруппированные штрихи — след вытоптанного двора.
    for _ in range(2):
        gx = rng.randrange(2, TILE - 7)
        gy = rng.randrange(3, TILE - 3)
        for step in range(rng.randrange(2, 4)):
            tile.put(gx + step * 2, gy + (step % 2), PAL["straw"])
    for _ in range(stones):
        x = rng.randrange(3, TILE - 6)
        y = rng.randrange(3, TILE - 5)
        w = rng.randrange(3, 5)
        tile.hline(y, x, x + w, PAL["stone_d"])
        tile.put(x, y, PAL["stone"])
    # Фактура: несколько одиночных пикселей, без равномерного шума.
    for _ in range(4):
        x = rng.randrange(1, TILE - 1)
        y = rng.randrange(1, TILE - 1)
        tile.put(x, y, rng.choice((PAL["earth_d"], PAL["earth_l"])))
    if grass:
        # Пучки сухой травы: 2–3 группы, а не сплошная полоса по краю тайла.
        for _ in range(3):
            x = rng.randrange(3, TILE - 4)
            y = rng.randrange(6, TILE - 3)
            tile.vline(x, y - rng.randrange(2, 4), y, PAL["moss"])
            tile.put(x, y - rng.randrange(2, 4), PAL["moss_l"])
    return tile


def _path_tile(seed: int, variant: int) -> Canvas:
    """Вытоптанная дорога: мокрая земля, втоптанные плоские камни, колеи.

    Ровные каменные плиты на 24 px тайле давали «лестницу» из повторяющихся
    швов; поэтому дорожка — это земля с редкими втоптанными камнями, как на
    look-референсе. Камни не касаются края тайла: шва между тайлами не видно.
    """
    rng = random.Random(seed)
    tile = Canvas(TILE, TILE)
    tile.fill(PAL["earth_m"])
    _blob(tile, rng.uniform(6, 18), rng.uniform(6, 18), rng.uniform(7, 10), rng.uniform(5, 8), PAL["earth"], edge=PAL["earth_m"])
    _blob(tile, rng.uniform(6, 18), rng.uniform(6, 18), rng.uniform(5, 7), rng.uniform(3, 5), PAL["earth_d"], edge=PAL["earth"])
    # Колея: короткие прерывистые штрихи вдоль дороги, а не сплошные линии.
    for dash in range(2 + variant % 2):
        x = rng.randrange(4, TILE - 5)
        y = 3 + dash * 9 + rng.randrange(0, 3)
        tile.vline(x, y, y + rng.randrange(3, 6), PAL["earth_d"])
    # Мокрый блеск и солома.
    for _ in range(2):
        x = rng.randrange(2, TILE - 6)
        y = rng.randrange(3, TILE - 3)
        tile.hline(y, x, x + rng.randrange(2, 4), PAL["water_l"])
    for _ in range(3):
        x = rng.randrange(2, TILE - 5)
        y = rng.randrange(3, TILE - 3)
        tile.put(x, y, PAL["straw"])
    return tile


def _planks_tile(seed: int, wet: bool) -> Canvas:
    """Доски настила: две широкие доски, тёмные швы, гвозди, мокрый блеск."""
    rng = random.Random(seed)
    tile = Canvas(TILE, TILE)
    board = 12
    for index in range(2):
        y0 = index * board
        y1 = y0 + board - 1
        tone = PAL["wood_d"] if index % 2 == 0 else PAL["wood"]
        tile.rect(0, y0, TILE - 1, y1, tone)
        tile.hline(y0, 0, TILE - 1, PAL["wood_m"])  # светлая кромка доски
        tile.hline(y1, 0, TILE - 1, PAL["ink"])  # шов
        # Волокна: длинные горизонтальные штрихи, а не точки.
        for _ in range(2):
            x = rng.randrange(1, TILE - 8)
            y = rng.randrange(y0 + 3, y1 - 2)
            tile.hline(y, x, x + rng.randrange(3, 7), PAL["wood_d"] if index % 2 == 0 else PAL["wood_l"])
        # Гвозди у краёв.
        for nx in (3, TILE - 4):
            tile.put(nx, y1 - 3, PAL["iron"])
            tile.put(nx, y1 - 2, PAL["iron"])
    if wet:
        # Мокрые доски: холодный отблеск вдоль волокон и тёмный затёк в шве.
        for _ in range(2):
            y = rng.randrange(2, TILE - 3)
            x = rng.randrange(1, TILE - 9)
            tile.hline(y, x, x + rng.randrange(4, 8), PAL["water"])
        tile.hline(23, 0, TILE - 1, PAL["ink"])
    return tile


def _curb_tile(seed: int) -> Canvas:
    """Каменный бордюр: тёмный камень, край дорожки не должен светиться."""
    rng = random.Random(seed)
    tile = Canvas(TILE, TILE)
    tile.fill(PAL["earth_d"])
    tile.rect(0, 0, TILE - 1, 9, PAL["stone_d"])
    tile.hline(0, 0, TILE - 1, PAL["stone"])
    tile.hline(1, 0, TILE - 1, PAL["stone_l"])
    tile.hline(9, 0, TILE - 1, PAL["ink"])
    for _ in range(4):
        x = rng.randrange(1, TILE - 2)
        y = rng.randrange(2, 8)
        tile.put(x, y, rng.choice((PAL["stone"], PAL["ink"])))
    tile.rect(0, 11, TILE - 1, TILE - 1, PAL["earth_d"])
    return tile


def draw_ground_tileset() -> Canvas:
    atlas = Canvas(TILE * 4, TILE * 2)
    _paste_tile(atlas, _earth_tile(1201), T_EARTH_A)
    _paste_tile(atlas, _earth_tile(1202, wet=True), T_EARTH_B)
    _paste_tile(atlas, _earth_tile(1203, grass=True), T_EARTH_C)
    _paste_tile(atlas, _path_tile(1301, 0), T_PATH_A)
    _paste_tile(atlas, _path_tile(1302, 1), T_PATH_B)
    # Третий вариант дороги занимает место неиспользованного бордюра: повтор
    # рисунка на 24 px заметен, поэтому вариантов должно быть больше двух.
    _paste_tile(atlas, _path_tile(1303, 2), T_CURB)
    _paste_tile(atlas, _planks_tile(1401, wet=False), T_PLANKS)
    _paste_tile(atlas, _planks_tile(1402, wet=True), T_PLANKS_WET)
    return atlas


# ---------------------------------------------------------------------------
# Частокол: 48x72 (2x3 тайла), повторяемый сегмент
# ---------------------------------------------------------------------------


def draw_palisade() -> Canvas:
    width, height = 48, 72
    canvas = Canvas(width, height)
    rng = random.Random(2101)
    log_w, gap, pitch = 7, 1, 8
    bottom = height - 6
    for index in range(6):
        x0 = index * pitch
        x1 = x0 + log_w - 1
        # Верх бревна заострён: 4 ряда сужения — узнаваемый силуэт частокола.
        taper = (2, 4, 6, 7)
        top = 8 + (index % 3)
        for step, tip_w in enumerate(taper):
            half = tip_w // 2
            center = x0 + log_w // 2
            canvas.hline(top + step, center - half, center - half + tip_w - 1, PAL["wood_m"])
        canvas.rect(x0, top + 4, x1, bottom, PAL["wood"])
        # Светлая кромка слева, тень справа: брёвна в ряд, а не плоский забор.
        canvas.vline(x0, top + 4, bottom, PAL["wood_l"])
        canvas.vline(x0 + 1, top + 5, bottom - 2, PAL["wood_m"])
        canvas.vline(x1, top + 4, bottom, PAL["wood_d"])
        # Волокна и сучки.
        for _ in range(2):
            gy = rng.randrange(top + 8, bottom - 4)
            canvas.put(x0 + rng.randrange(2, log_w - 1), gy, PAL["wood_d"])
        if index % 2 == 0:
            gy = rng.randrange(top + 12, bottom - 8)
            canvas.hline(gy, x0 + 2, x0 + 4, PAL["wood_d"])
    # Горизонтальные прожилины: два ряда, тёмные, с бликом сверху.
    for rail_y in (44, 58):
        canvas.rect(0, rail_y, width - 1, rail_y + 3, PAL["wood_d"])
        canvas.hline(rail_y, 0, width - 1, PAL["wood_m"])
        canvas.hline(rail_y + 3, 0, width - 1, PAL["ink"])
    # Тень и мох у основания.
    canvas.rect(0, bottom - 3, width - 1, bottom, PAL["wood_d"])
    for _ in range(9):
        x = rng.randrange(0, width)
        y = rng.randrange(bottom - 7, bottom + 3)
        canvas.put(x, y, rng.choice((PAL["moss"], PAL["moss_d"])))
    canvas.rect(0, bottom + 1, width - 1, bottom + 4, PAL["earth_d"])
    return canvas


# ---------------------------------------------------------------------------
# Врата: 96x96 (4x4 тайла) — столбы, кровля, полотнища, свет из щели
# ---------------------------------------------------------------------------


def draw_gate() -> Canvas:
    width, height = 96, 96
    canvas = Canvas(width, height)
    rng = random.Random(2201)
    post_w = 12
    roof_h = 18
    door_top = 30
    base_y = 88

    # --- Кровля над вратами: двускатная, с резной причелиной ---
    for y in range(roof_h):
        half = int(4 + (y / max(1, roof_h - 1)) ** 0.75 * 44)
        left = 48 - half
        right = 48 + half
        canvas.hline(y, left, right, PAL["wood"])
        canvas.put(left, y, PAL["wood_l"])
        canvas.put(right, y, PAL["wood_d"])
        canvas.hline(y, left + 2, right - 2, PAL["slate_d"] if y % 5 else PAL["slate"])
    # Конёк и светлая кромка кровли.
    canvas.rect(46, 0, 49, 4, PAL["wood_l"])
    canvas.hline(roof_h - 1, 4, 91, PAL["wood_l"])
    # Резные подвески по краю кровли.
    for x in range(8, 90, 6):
        canvas.put(x, roof_h, PAL["wood_d"])
        canvas.put(x + 1, roof_h + 1, PAL["wood_d"])

    # --- Столбы ---
    for x0 in (0, width - post_w):
        canvas.rect(x0, roof_h + 1, x0 + post_w - 1, base_y + 4, PAL["wood"])
        canvas.vline(x0, roof_h + 1, base_y + 4, PAL["wood_l"])
        canvas.vline(x0 + 1, roof_h + 2, base_y + 2, PAL["wood_m"])
        canvas.vline(x0 + post_w - 1, roof_h + 1, base_y + 4, PAL["wood_d"])
        # Капитель и железные оковы с заклёпками.
        canvas.rect(x0 - 1, roof_h + 1, x0 + post_w, roof_h + 4, PAL["wood_l"])
        canvas.hline(roof_h + 4, x0 - 1, x0 + post_w, PAL["ink"])
        for band_y in (roof_h + 14, base_y - 16):
            canvas.rect(x0 + 1, band_y, x0 + post_w - 2, band_y + 2, PAL["iron"])
            canvas.hline(band_y, x0 + 1, x0 + post_w - 2, PAL["iron_l"])
            canvas.put(x0 + 3, band_y + 1, PAL["ivory"])
            canvas.put(x0 + post_w - 4, band_y + 1, PAL["ivory"])
        # Каменная опора.
        canvas.rect(x0, base_y + 1, x0 + post_w - 1, base_y + 6, PAL["stone"])
        canvas.hline(base_y + 1, x0, x0 + post_w - 1, PAL["stone_l"])
        canvas.hline(base_y + 6, x0, x0 + post_w - 1, PAL["stone_d"])

    # --- Притолока с резьбой ---
    canvas.rect(post_w, roof_h + 5, width - post_w - 1, roof_h + 13, PAL["wood"])
    canvas.hline(roof_h + 5, post_w, width - post_w - 1, PAL["wood_l"])
    canvas.hline(roof_h + 13, post_w, width - post_w - 1, PAL["ink"])
    for x in range(post_w + 3, width - post_w - 3, 5):
        canvas.put(x, roof_h + 9, PAL["gold_d"])
        canvas.put(x + 1, roof_h + 10, PAL["gold"])

    # --- Полотнища ворот: две створки, железные полосы, щель света ---
    door_left = post_w + 2
    door_right = width - post_w - 3
    canvas.rect(door_left, door_top, door_right, base_y, PAL["wood_d"])
    # Створки темнее столбов: врата читаются как проём, а не как стена.
    for leaf in ((door_left, 45), (51, door_right)):
        x0, x1 = leaf
        canvas.rect(x0, door_top, x1, base_y, PAL["wood_d"])
        for x in range(x0 + 1, x1, 4):
            canvas.rect(x, door_top + 1, x + 2, base_y - 1, PAL["wood"])
            canvas.vline(x, door_top + 1, base_y - 1, PAL["wood_m"])
        # Диагональная связь створки: без неё доски выглядят просто полосами.
        canvas.line(x0 + 2, base_y - 6, x1 - 2, door_top + 6, PAL["wood_d"])
        canvas.line(x0 + 2, base_y - 5, x1 - 2, door_top + 7, PAL["wood_d"])
    # Железные полосы с заклёпками.
    for band_y in (door_top + 10, door_top + 26, base_y - 10):
        canvas.rect(door_left, band_y, door_right, band_y + 2, PAL["iron"])
        canvas.hline(band_y, door_left, door_right, PAL["iron_l"])
        for x in range(door_left + 3, door_right - 1, 7):
            canvas.put(x, band_y + 1, PAL["stone_ll"])
    # Щель между створками: тёплый свет изнутри — сильнейший акцент врат.
    canvas.rect(46, door_top + 1, 49, base_y - 1, PAL["ink"])
    canvas.rect(47, door_top + 8, 48, base_y - 2, PAL["amber_d"])
    canvas.rect(47, door_top + 22, 48, base_y - 4, PAL["amber"])
    canvas.rect(47, door_top + 32, 48, base_y - 8, PAL["fire"])
    # Свет, вытекающий из-под ворот на землю.
    canvas.rect(door_left + 2, base_y - 1, door_right - 2, base_y, PAL["amber_d"])
    canvas.hline(base_y, door_left + 6, door_right - 6, PAL["amber"])
    # Кольца-ручки.
    for x in (41, 54):
        canvas.put(x, door_top + 20, PAL["iron_l"])
        canvas.put(x, door_top + 21, PAL["iron"])

    # --- Знамя на притолоке ---
    canvas.rect(36, roof_h + 14, 59, roof_h + 15, PAL["wood_d"])
    for x in (37, 58):
        canvas.vline(x, roof_h + 14, roof_h + 17, PAL["iron"])
    canvas.rect(38, roof_h + 17, 57, roof_h + 30, PAL["crimson"])
    canvas.vline(38, roof_h + 17, roof_h + 30, PAL["crimson_d"])
    canvas.vline(57, roof_h + 17, roof_h + 30, PAL["crimson_l"])
    # Вырез «ласточкин хвост» снизу и знак-оберег.
    for i in range(3):
        canvas.erase(38 + i, roof_h + 30 - i)
        canvas.erase(57 - i, roof_h + 30 - i)
    canvas.rect(46, roof_h + 20, 48, roof_h + 26, PAL["gold"])
    canvas.hline(roof_h + 21, 44, 50, PAL["gold_d"])

    # --- Опорные камни и тень у основания ---
    canvas.rect(10, base_y + 2, width - 11, base_y + 6, PAL["stone_d"])
    canvas.hline(base_y + 2, 10, width - 11, PAL["stone"])
    canvas.rect(6, base_y + 7, width - 7, base_y + 9, PAL["earth_d"])
    for _ in range(14):
        x = rng.randrange(2, width - 2)
        y = rng.randrange(base_y, base_y + 8)
        if (x, y) in canvas.px:
            canvas.put(x, y, PAL["moss_d"])
    return canvas


# ---------------------------------------------------------------------------
# Изба: 192x120 (8x5 тайлов)
# ---------------------------------------------------------------------------


def draw_izba() -> Canvas:
    width, height = 192, 120
    canvas = Canvas(width, height)
    rng = random.Random(2301)
    wall_top = 38
    wall_bottom = 110
    beam = 6  # высота венца сруба

    # --- Кровля: тёсовые ряды с нахлёстом, резная причелина, тень под свесом ---
    apex_y = 3
    for y in range(apex_y, wall_top + 4):
        t = (y - apex_y) / float(wall_top - apex_y + 1)
        half = int(3 + t * 94)
        left, right = 96 - half, 96 + half
        # Причелина: доска по краю кровли, резные зубцы через каждые 5 рядов.
        canvas.hline(y, left, left + 2, PAL["wood_l"])
        canvas.hline(y, right - 2, right, PAL["wood_m"])
        if y % 5 == 0:
            canvas.put(left + 1, y, PAL["wood_d"])
            canvas.put(right - 1, y, PAL["wood_d"])
        # Тело кровли: тёмный тёс, светлая кромка каждого ряда, тень под ним.
        canvas.hline(y, left + 3, right - 3, PAL["night_b"])
        if (y - apex_y) % 4 == 0:
            canvas.hline(y, left + 3, right - 3, PAL["night"])
        elif (y - apex_y) % 4 == 1:
            canvas.hline(y, left + 3, right - 3, PAL["slate_d"])
            # Вертикальные стыки тёса — со смещением через ряд.
            offset = 0 if ((y - apex_y) // 4) % 2 == 0 else 3
            for x in range(left + 3 + offset, right - 3, 7):
                canvas.put(x, y, PAL["night"])
    # Охлупень на коньке и тёмный свес над стеной.
    canvas.rect(92, 0, 99, 5, PAL["wood_m"])
    canvas.rect(93, 0, 98, 2, PAL["wood_l"])
    canvas.hline(0, 90, 101, PAL["wood_d"])
    canvas.hline(wall_top + 2, 2, width - 3, PAL["ink"])
    canvas.hline(wall_top + 3, 2, width - 3, PAL["wood_d"])
    # Слуховое окно в щипце: тёплая точка, которая сразу читает «жильё».
    canvas.rect(89, 18, 103, 32, PAL["wood_m"])
    canvas.rect(90, 19, 102, 31, PAL["night"])
    canvas.rect(91, 21, 101, 30, PAL["amber_d"])
    canvas.rect(93, 23, 99, 29, PAL["fire"])
    canvas.hline(19, 89, 103, PAL["wood_l"])
    canvas.vline(96, 21, 30, PAL["wood_d"])

    # --- Сруб: 12 венцов с выступающими концами ---
    courses = (wall_bottom - wall_top) // beam
    for index in range(courses):
        y0 = wall_top + index * beam
        y1 = y0 + beam - 1
        tone = PAL["wood_m"] if index % 2 == 0 else PAL["wood"]
        canvas.rect(3, y0, width - 4, y1, tone)
        canvas.hline(y0, 3, width - 4, PAL["wood_l"])
        canvas.hline(y1, 3, width - 4, PAL["wood_d"])
        # Волокна брёвен: короткие тёмные штрихи вразброс.
        for _ in range(10):
            x = rng.randrange(6, width - 10)
            gy = rng.randrange(y0 + 2, y1 - 1)
            canvas.hline(gy, x, x + rng.randrange(1, 4), PAL["wood_d"])
        # Выступающие концы брёвен: чередование венцов даёт «сруб», а не стену.
        if index % 2 == 0:
            for x0 in (-1, width - 4):
                canvas.ellipse(x0 + 3, y0 + beam / 2 - 0.5, 4.5, 2.6, PAL["wood_m"])
                canvas.hline(y0 + 1, max(0, x0 + 1), min(width - 1, x0 + 5), PAL["wood_l"])
                canvas.hline(y1 - 1, max(0, x0 + 1), min(width - 1, x0 + 5), PAL["wood_d"])
    # Угловые тени: сруб получает объём.
    canvas.vline(3, wall_top, wall_bottom - 1, PAL["wood_d"])
    canvas.vline(4, wall_top + 1, wall_bottom - 2, PAL["wood_l"])
    canvas.vline(width - 4, wall_top, wall_bottom - 1, PAL["ink"])
    canvas.vline(width - 5, wall_top, wall_bottom - 1, PAL["wood_d"])

    # --- Фундамент из камней ---
    canvas.rect(0, wall_bottom, width - 1, height - 1, PAL["stone_d"])
    for row in range(2):
        y = wall_bottom + 1 + row * 5
        x = 0
        while x < width:
            w = rng.randrange(8, 14)
            tone = rng.choice((PAL["stone"], PAL["stone_d"], PAL["stone_l"]))
            canvas.rect(x + 1, y, min(width - 2, x + w - 2), y + 3, tone)
            canvas.hline(y, x + 1, min(width - 2, x + w - 2), PAL["stone_l"])
            x += w
    canvas.hline(height - 1, 0, width - 1, PAL["ink"])

    # --- Окна с резными наличниками и тёплым светом ---
    for wx in (26, 134):
        wy = 54
        ww, wh = 22, 22
        canvas.rect(wx - 3, wy - 5, wx + ww + 2, wy + wh + 2, PAL["wood_l"])
        canvas.rect(wx - 3, wy - 5, wx - 2, wy + wh + 2, PAL["wood_ll"])
        canvas.rect(wx + ww + 1, wy - 5, wx + ww + 2, wy + wh + 2, PAL["wood_m"])
        # Кокошник наличника: ступенчатый «теремок» над окном.
        for i in range(6):
            canvas.hline(wy - 6 - i, wx + 5, wx + ww - 6, PAL["wood_ll"])
            canvas.put(wx + 5 - i, wy - 6 - i, PAL["wood_ll"])
            canvas.put(wx + ww - 6 + i, wy - 6 - i, PAL["wood_ll"])
        canvas.hline(wy - 4, wx - 3, wx + ww + 2, PAL["wood_d"])
        # Стекло: тёплый свет с переплётом.
        canvas.rect(wx, wy, wx + ww - 1, wy + wh - 1, PAL["amber"])
        canvas.rect(wx + 1, wy + 1, wx + ww - 2, wy + wh - 4, PAL["fire"])
        canvas.rect(wx + 4, wy + 2, wx + ww - 6, wy + wh - 8, PAL["fire_l"])
        canvas.vline(wx + ww // 2, wy, wy + wh - 1, PAL["wood_d"])
        canvas.hline(wy + wh // 2, wx, wx + ww - 1, PAL["wood_d"])
        canvas.rect(wx, wy, wx + ww - 1, wy, PAL["wood_m"])
        # Подоконник и световое пятно на стене под окном.
        canvas.hline(wy + wh + 2, wx - 4, wx + ww + 3, PAL["wood_ll"])
        canvas.hline(wy + wh + 3, wx - 4, wx + ww + 3, PAL["wood_d"])
        for dy in range(1, 8):
            width_here = ww - dy
            if width_here <= 0:
                break
            for dx in range(width_here):
                x = wx + dx + dy // 2
                if (dx + dy) % 2 == 0 or dy < 3:
                    canvas.put(x, wy + wh + 3 + dy, PAL["amber_d"])

    # --- Навес, дверь, крыльцо, фонарь ---
    door_x0, door_x1 = 84, 112
    door_top = 70
    # Навес над дверью: маленькая двускатная кровля на кронштейнах.
    for i in range(10):
        half = 20 - i * 2
        canvas.hline(58 + i, 98 - half, 98 + half, PAL["wood_m"] if i % 3 else PAL["wood_l"])
    canvas.hline(68, 78, 118, PAL["ink"])
    for x in (82, 114):
        canvas.vline(x, 60, 70, PAL["wood_d"])
    canvas.rect(door_x0 - 3, door_top - 2, door_x1 + 3, wall_bottom, PAL["wood_l"])
    canvas.rect(door_x0 - 3, door_top - 2, door_x0 - 2, wall_bottom, PAL["wood_ll"])
    canvas.rect(door_x1 + 2, door_top - 2, door_x1 + 3, wall_bottom, PAL["wood_m"])
    canvas.rect(door_x0, door_top, door_x1, wall_bottom - 1, PAL["wood_d"])
    canvas.rect(door_x0 + 2, door_top + 2, door_x1 - 2, wall_bottom - 3, PAL["wood"])
    for x in range(door_x0 + 5, door_x1 - 3, 6):
        canvas.vline(x, door_top + 2, wall_bottom - 3, PAL["wood_d"])
    canvas.hline(door_top + 10, door_x0 + 2, door_x1 - 2, PAL["iron"])
    canvas.hline(door_top + 11, door_x0 + 2, door_x1 - 2, PAL["iron_l"])
    # Свет из-под двери и щели: изба жива.
    canvas.hline(wall_bottom - 2, door_x0 + 2, door_x1 - 2, PAL["amber_d"])
    canvas.hline(wall_bottom - 1, door_x0 + 4, door_x1 - 4, PAL["fire"])
    canvas.put(door_x1 - 5, door_top + 15, PAL["iron_l"])
    # Крыльцо: две каменные ступени шире двери.
    canvas.rect(door_x0 - 9, wall_bottom + 1, door_x1 + 9, wall_bottom + 4, PAL["stone"])
    canvas.hline(wall_bottom + 1, door_x0 - 9, door_x1 + 9, PAL["stone_l"])
    canvas.rect(door_x0 - 6, wall_bottom + 5, door_x1 + 6, wall_bottom + 8, PAL["stone_d"])
    canvas.hline(wall_bottom + 5, door_x0 - 6, door_x1 + 6, PAL["stone"])
    canvas.hline(wall_bottom + 8, door_x0 - 6, door_x1 + 6, PAL["earth_d"])
    # Фонарь на крюке справа от двери.
    canvas.vline(door_x1 + 7, door_top + 4, door_top + 8, PAL["iron"])
    canvas.rect(door_x1 + 4, door_top + 9, door_x1 + 10, door_top + 15, PAL["iron"])
    canvas.rect(door_x1 + 5, door_top + 10, door_x1 + 9, door_top + 14, PAL["fire"])
    canvas.rect(door_x1 + 6, door_top + 11, door_x1 + 8, door_top + 13, PAL["fire_l"])
    canvas.put(door_x1 + 7, door_top + 15, PAL["amber_d"])

    # --- Лавка и утварь у стены ---
    canvas.rect(20, 92, 54, 94, PAL["wood_m"])
    canvas.hline(92, 20, 54, PAL["wood_l"])
    canvas.vline(23, 95, 99, PAL["wood_d"])
    canvas.vline(51, 95, 99, PAL["wood_d"])
    # Кадка у двери.
    canvas.rect(130, 90, 140, 101, PAL["wood_m"])
    canvas.vline(130, 90, 101, PAL["wood_l"])
    canvas.vline(140, 90, 101, PAL["wood_d"])
    canvas.hline(92, 130, 140, PAL["iron"])
    canvas.hline(98, 130, 140, PAL["iron"])
    canvas.hline(89, 129, 141, PAL["wood_d"])

    # --- Мох, потёки, трещины ---
    for _ in range(30):
        x = rng.randrange(2, width - 2)
        y = rng.randrange(wall_bottom - 14, wall_bottom + 2)
        canvas.put(x, y, rng.choice((PAL["moss_d"], PAL["moss"])))
    for _ in range(5):
        x = rng.randrange(8, width - 8)
        y = rng.randrange(wall_top + 10, wall_bottom - 16)
        canvas.vline(x, y, y + rng.randrange(3, 9), PAL["wood_d"])
    canvas.hline(112, 0, width - 1, PAL["earth_d"])
    return canvas


# ---------------------------------------------------------------------------
# Часовня: 168x120 (7x5 тайлов) — фрагмент белокаменной стены
# ---------------------------------------------------------------------------


def _arch_band(canvas: Canvas, cx: float, spring_y: int, inner: float, thickness: float, color) -> None:
    """Полуциркульная арка заданной толщины: облом портала или кокошник."""
    outer = inner + thickness
    for y in range(int(spring_y - outer), spring_y + 1):
        for x in range(int(cx - outer), int(cx + outer) + 1):
            distance = ((x - cx) ** 2 + (y - spring_y) ** 2) ** 0.5
            if inner <= distance <= outer:
                canvas.put(x, y, color)


def draw_chapel() -> Canvas:
    width, height = 168, 120
    canvas = Canvas(width, height)
    rng = random.Random(2401)
    cornice_y = 26
    wall_top = 30
    base_y = 106

    # --- Тёмная кровля за кокошниками ---
    canvas.rect(0, 0, width - 1, cornice_y, PAL["night"])
    for x in range(0, width, 3):
        if x % 6 == 0:
            canvas.put(x, 2, PAL["night_b"])
    # Три полуциркульных закомары над карнизом: узнаваемый силуэт древнерусской стены.
    for cx in (30, 84, 138):
        radius = 26
        for y in range(cornice_y - radius, cornice_y + 1):
            dy = cornice_y - y
            half = int((max(0.0, radius * radius - dy * dy)) ** 0.5)
            canvas.hline(y, cx - half, cx + half, PAL["white_d"])
            # Светлая кромка арки и тёмная внутренняя расшивка.
            canvas.put(cx - half, y, PAL["white_l"])
            canvas.put(cx + half, y, PAL["white_l"])
            if half > 3:
                canvas.hline(y, cx - half + 2, cx - half + 2, PAL["stone_l"])
                canvas.hline(y, cx + half - 2, cx + half - 2, PAL["stone_l"])
        # Внутри закомары — небольшая ниша с тенью.
        for y in range(cornice_y - 14, cornice_y - 2):
            dy = cornice_y - 8 - y
            half = int((max(0.0, 64.0 - dy * dy)) ** 0.5)
            canvas.hline(y, cx - half, cx + half, PAL["white"])
            canvas.put(cx - half, y, PAL["white_d"])
            canvas.put(cx + half, y, PAL["white_d"])
    # Карниз: выносная плита с тенью под ней.
    canvas.rect(0, cornice_y, width - 1, cornice_y + 3, PAL["white_l"])
    canvas.hline(cornice_y, 0, width - 1, PAL["white_ll"])
    canvas.hline(cornice_y + 3, 0, width - 1, PAL["stone_l"])
    canvas.hline(cornice_y + 4, 0, width - 1, PAL["white_d"])

    # --- Резной пояс: плетёнка в два ряда ---
    canvas.rect(0, cornice_y + 5, width - 1, cornice_y + 15, PAL["white_d"])
    canvas.hline(cornice_y + 5, 0, width - 1, PAL["white"])
    canvas.hline(cornice_y + 15, 0, width - 1, PAL["stone_l"])
    for x in range(1, width - 5, 8):
        for i in range(4):
            canvas.put(x + i, cornice_y + 7 + i, PAL["white_l"])
            canvas.put(x + 4 - i, cornice_y + 7 + i, PAL["stone_l"])
            canvas.put(x + 1 + i, cornice_y + 11 - i, PAL["stone_l"])
            canvas.put(x + 3 - i, cornice_y + 11 - i, PAL["white_l"])

    # --- Кладка: блоки белого камня с расшивкой и объёмом ---
    canvas.rect(0, wall_top, width - 1, base_y - 1, PAL["white_d"])
    block_h = 12
    row_index = 0
    y = wall_top + 4
    while y < base_y:
        offset = 0 if row_index % 2 == 0 else 16
        x = -offset
        while x < width:
            w = 32
            x0 = max(0, x + 1)
            x1 = min(width - 1, x + w - 2)
            if x1 > x0:
                tone = rng.choice((PAL["white_d"], PAL["white_d"], PAL["white"], PAL["white_l"]))
                canvas.rect(x0, y, x1, min(base_y - 1, y + block_h - 2), tone)
                canvas.hline(y, x0, x1, PAL["white_l"])
                canvas.vline(x0, y, min(base_y - 1, y + block_h - 2), PAL["white_l"])
                canvas.hline(min(base_y - 1, y + block_h - 2), x0, x1, PAL["stone_l"])
                canvas.vline(x1, y + 1, min(base_y - 1, y + block_h - 2), PAL["stone_l"])
            x += w
        y += block_h
        row_index += 1

    # --- Портал: три облома, тёплый свет из нутра, лампада ---
    cx = 84
    spring_y = 76
    for order, inner in enumerate((16, 19, 22)):
        color = (PAL["white"], PAL["white_l"], PAL["white_ll"])[order]
        _arch_band(canvas, cx, spring_y, inner, 3, color)
        # Вертикальные обломы вниз до цоколя.
        for side in (-1, 1):
            x_edge = cx + side * inner
            x_band = cx + side * (inner + 3)
            canvas.rect(min(x_edge, x_band), spring_y, max(x_edge, x_band) - 1, base_y - 1, color)
    # Нутро портала: почти чёрное, с тёплым отсветом у пола.
    for y in range(spring_y - 15, base_y):
        half = (max(0.0, 15.0 * 15.0 - (spring_y - 15 - y) ** 2)) ** 0.5 if y < spring_y else 15.0
        canvas.hline(y, int(cx - half) + 1, int(cx + half) - 1, PAL["ink"])
    canvas.rect(cx - 12, spring_y - 6, cx + 12, base_y - 6, PAL["night"])
    for i in range(9):
        canvas.hline(base_y - 5 - i, cx - 11 + i // 2, cx + 11 - i // 2, PAL["crimson_d"] if i > 5 else PAL["amber_d"])
    canvas.rect(cx - 8, base_y - 8, cx + 8, base_y - 4, PAL["amber"])
    canvas.rect(cx - 5, base_y - 7, cx + 5, base_y - 5, PAL["fire"])
    canvas.rect(cx - 2, base_y - 6, cx + 2, base_y - 5, PAL["fire_l"])
    # Ступень порога.
    canvas.rect(cx - 20, base_y - 2, cx + 20, base_y + 1, PAL["stone"])
    canvas.hline(base_y - 2, cx - 20, cx + 20, PAL["stone_l"])
    # Лампада на цепочке.
    canvas.vline(cx, spring_y - 14, spring_y - 8, PAL["iron"])
    canvas.rect(cx - 3, spring_y - 7, cx + 3, spring_y - 4, PAL["gold_d"])
    canvas.rect(cx - 2, spring_y - 6, cx + 2, spring_y - 5, PAL["fire_l"])

    # --- Узкие окна-бойницы с тёплым светом ---
    for wx in (22, 130):
        canvas.rect(wx - 2, 56, wx + 10, 84, PAL["white_l"])
        canvas.rect(wx, 58, wx + 8, 82, PAL["night"])
        canvas.rect(wx + 1, 62, wx + 7, 80, PAL["amber_d"])
        canvas.rect(wx + 2, 66, wx + 6, 77, PAL["amber"])
        canvas.rect(wx + 3, 69, wx + 5, 74, PAL["fire"])
        canvas.hline(55, wx - 3, wx + 11, PAL["white_ll"])
        canvas.vline(wx - 2, 56, 84, PAL["white_ll"])
        canvas.vline(wx + 10, 56, 84, PAL["stone_l"])

    # --- Лопатки по краям: стена читается как фрагмент ---
    for x0 in (0, width - 11):
        canvas.rect(x0, cornice_y, x0 + 10, base_y - 1, PAL["white_d"])
        canvas.vline(x0, cornice_y, base_y - 1, PAL["white_l"])
        canvas.vline(x0 + 1, cornice_y, base_y - 1, PAL["white"])
        canvas.vline(x0 + 10, cornice_y, base_y - 1, PAL["stone_l"])

    # --- Цоколь и мох ---
    canvas.rect(0, base_y, width - 1, height - 1, PAL["stone_d"])
    canvas.hline(base_y, 0, width - 1, PAL["stone"])
    for x in range(0, width, 9):
        canvas.vline(x, base_y + 1, height - 2, PAL["stone_d"])
        canvas.hline(base_y + 1, x, min(width - 1, x + 7), PAL["stone"])
    canvas.hline(height - 1, 0, width - 1, PAL["ink"])
    for _ in range(40):
        x = rng.randrange(0, width)
        y = rng.randrange(base_y - 12, base_y + 5)
        canvas.put(x, y, rng.choice((PAL["moss_d"], PAL["moss"], PAL["stone_l"])))
    # Сколы и трещины: белый камень не бывает идеальным.
    for _ in range(30):
        x = rng.randrange(2, width - 2)
        y = rng.randrange(wall_top + 20, base_y - 3)
        canvas.put(x, y, rng.choice((PAL["white_d"], PAL["stone_l"], PAL["white_l"])))
    for _ in range(3):
        x = rng.randrange(6, width - 20)
        y = rng.randrange(wall_top + 24, base_y - 14)
        canvas.vline(x, y, y + rng.randrange(4, 9), PAL["stone_l"])
    return canvas


# ---------------------------------------------------------------------------
# Мёртвое дерево: 120x144 (5x6 тайлов) с красными лоскутами
# ---------------------------------------------------------------------------


def _stamp_branch(canvas: Canvas, p0, p1, w0: float, w1: float, color) -> list[tuple[float, float, float]]:
    """Ветвь переменной толщины: штампы-диски по линии. Возвращает точки для сучьев."""
    (x0, y0), (x1, y1) = p0, p1
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    points: list[tuple[float, float, float]] = []
    for index in range(steps + 1):
        t = index / float(steps)
        cx = x0 + (x1 - x0) * t
        cy = y0 + (y1 - y0) * t
        half = (w0 + (w1 - w0) * t) / 2.0
        canvas.ellipse(cx, cy, max(0.6, half), max(0.6, half), color)
        points.append((cx, cy, half))
    return points


def _rim_light(canvas: Canvas, mapping: dict[tuple[int, int, int, int], tuple[int, int, int, int]]) -> None:
    """Лунный контровой свет: верхне-левая кромка силуэта светлеет на один тон."""
    for (x, y), color in list(canvas.px.items()):
        if color not in mapping:
            continue
        if (x - 1, y) in canvas.px or (x, y - 1) in canvas.px or (x - 1, y - 1) in canvas.px:
            continue
        canvas.put(x, y, mapping[color])


def draw_dead_tree() -> Canvas:
    width, height = 120, 144
    canvas = Canvas(width, height)
    rng = random.Random(2501)
    base_y = 136

    # --- Ствол: утолщён у корней, слегка изогнут ---
    for y in range(44, base_y + 1):
        t = (y - 44) / float(base_y - 44)
        cx = 62 + 6.0 * (t - 0.5) ** 2 * 4 + 3.0 * math.sin((y - 44) / 22.0)
        half = 3.0 + 6.5 * t
        canvas.hline(y, int(cx - half), int(cx + half), PAL["wood_m"])
    # Корни: растекаются по земле тонкими языками.
    for root in (
        ((62, base_y), (24, base_y + 4)),
        ((62, base_y), (100, base_y + 3)),
        ((62, base_y), (42, base_y + 6)),
        ((62, base_y), (84, base_y + 6)),
        ((62, base_y), (12, base_y - 2)),
    ):
        _stamp_branch(canvas, root[0], root[1], 5.0, 1.2, PAL["wood"])

    # --- Ветви: главные, затем сучья от них ---
    branches = (
        ((64, 74), (20, 40), 7.0, 2.0),
        ((60, 84), (8, 88), 6.0, 1.8),
        ((65, 64), (42, 12), 6.0, 1.8),
        ((68, 60), (102, 24), 6.0, 1.8),
        ((70, 92), (112, 66), 5.0, 1.6),
        ((64, 52), (78, 4), 5.0, 1.5),
        ((58, 104), (28, 118), 4.0, 1.4),
    )
    rag_anchors: list[tuple[int, int]] = []
    for (p0, p1, w0, w1) in branches:
        points = _stamp_branch(canvas, p0, p1, w0, w1, PAL["wood"])
        # Сучья: от середины и от конца ветви, вверх и в стороны.
        for t in (0.55, 0.8, 1.0):
            index = min(len(points) - 1, int(t * (len(points) - 1)))
            cx, cy, _half = points[index]
            for _ in range(2):
                length = rng.randrange(7, 16)
                dir_x = rng.uniform(-0.9, 0.9)
                tip = (cx + dir_x * length * 0.6, cy - length)
                _stamp_branch(canvas, (cx, cy), tip, 2.0, 0.8, PAL["wood"])
        tip_x, tip_y, _ = points[-1]
        rag_anchors.append((int(tip_x), int(tip_y) + 1))
        mid = points[int(len(points) * 0.62)]
        rag_anchors.append((int(mid[0]), int(mid[1]) + 1))

    # --- Кора: волокна, дупло, тёмная правая сторона ---
    for _ in range(44):
        x = rng.randrange(46, 80)
        y = rng.randrange(46, base_y - 2)
        if (x, y) in canvas.px:
            canvas.put(x, y, PAL["wood_d"])
    canvas.ellipse(66, 96, 3.5, 6, PAL["ink"])
    canvas.ellipse(66, 96, 2, 3.5, PAL["wood_d"])
    # Тень на правой стороне ствола: объём без градиентов.
    for y in range(50, base_y):
        for x in range(70, 80):
            if (x, y) in canvas.px and (x + 1, y) not in canvas.px:
                canvas.put(x, y, PAL["wood_d"])

    # --- Красные лоскуты на ветвях ---
    unique_anchors = []
    for anchor in rag_anchors:
        if all(abs(anchor[0] - other[0]) + abs(anchor[1] - other[1]) > 6 for other in unique_anchors):
            unique_anchors.append(anchor)
    for index, (x, y) in enumerate(unique_anchors[:9]):
        length = 9 + (index * 4) % 13
        cloth_w = 3 if index % 3 else 4
        for dy in range(length):
            fade = dy / float(max(1, length - 1))
            for dx in range(cloth_w):
                color = PAL["crimson"]
                if dx == cloth_w - 1:
                    color = PAL["crimson_d"]
                elif dx == 0 and dy % 3 == 0:
                    color = PAL["crimson_l"]
                if fade > 0.75:
                    color = PAL["crimson_d"]
                canvas.put(x + dx, y + dy, color)
        canvas.put(x, y + length, PAL["crimson_hi"] if index % 2 else PAL["crimson_d"])
        canvas.put(x - 1, y, PAL["crimson_d"])
        canvas.put(x + cloth_w, y, PAL["crimson_d"])
    # --- Мох у корней ---
    for _ in range(20):
        x = rng.randrange(20, 100)
        y = rng.randrange(base_y - 4, base_y + 5)
        canvas.put(x, y, rng.choice((PAL["moss_d"], PAL["moss"])))

    # Лунная кромка: дерево читается силуэтом даже в темноте.
    _rim_light(
        canvas,
        {
            PAL["wood_m"]: PAL["wood_l"],
            PAL["wood"]: PAL["wood_m"],
            PAL["crimson"]: PAL["crimson_l"],
        },
    )
    return canvas


# ---------------------------------------------------------------------------
# Факельный столб: 2 кадра 24x72 (огонь мерцает)
# ---------------------------------------------------------------------------


def draw_torch(frame: int) -> Canvas:
    width, height = 24, 72
    canvas = Canvas(width, height)
    rng = random.Random(2600 + frame)
    # Столб.
    canvas.rect(9, 26, 14, 66, PAL["wood"])
    canvas.vline(9, 26, 66, PAL["wood_l"])
    canvas.vline(10, 27, 65, PAL["wood_m"])
    canvas.vline(14, 26, 66, PAL["wood_d"])
    for _ in range(4):
        y = rng.randrange(30, 62)
        canvas.put(rng.randrange(11, 13), y, PAL["wood_d"])
    # Кованая чаша и кронштейн.
    canvas.rect(6, 22, 17, 26, PAL["iron"])
    canvas.hline(22, 6, 17, PAL["iron_l"])
    canvas.hline(26, 6, 17, PAL["ink"])
    canvas.rect(7, 20, 16, 21, PAL["iron_l"])
    # Угли в чаше.
    canvas.rect(8, 19, 15, 20, PAL["amber_d"])
    canvas.rect(9, 18, 14, 19, PAL["amber"])
    # Пламя: 2 кадра, форма и яркость меняются — огонь «живой».
    flame_base = 18
    sway = 0 if frame == 0 else 1
    for y in range(4, flame_base + 1):
        t = (y - 4) / float(flame_base - 4)
        half = max(0.6, 3.4 * (1.0 - abs(t - 0.55) * 1.35))
        cx = 11.5 + sway * ((1.0 - t) * 1.6 - 0.8)
        canvas.hline(y, int(cx - half), int(cx + half), PAL["amber_d"])
    for y in range(7, flame_base + 1):
        t = (y - 7) / float(flame_base - 7)
        half = max(0.4, 2.4 * (1.0 - abs(t - 0.5) * 1.5))
        cx = 11.5 + sway * ((1.0 - t) * 1.2 - 0.6)
        canvas.hline(y, int(cx - half), int(cx + half), PAL["fire"])
    for y in range(10, flame_base + 1):
        t = (y - 10) / float(flame_base - 10)
        half = max(0.2, 1.4 * (1.0 - abs(t - 0.5) * 1.6))
        cx = 11.5 + sway * 0.5
        canvas.hline(y, int(cx - half), int(cx + half), PAL["fire_l"])
    canvas.rect(11, 13, 12, 17, PAL["fire_w"])
    # Искры.
    spark_x = 6 if frame == 0 else 17
    canvas.put(spark_x, 9 - frame, PAL["amber"])
    canvas.put(spark_x + (1 if frame else -1), 6, PAL["fire"])
    # Основание: камни.
    canvas.rect(5, 66, 18, 70, PAL["stone_d"])
    canvas.hline(66, 5, 18, PAL["stone"])
    canvas.hline(70, 4, 19, PAL["earth_d"])
    return canvas


# ---------------------------------------------------------------------------
# Полотнище-знамя: 24x48
# ---------------------------------------------------------------------------


def draw_banner() -> Canvas:
    width, height = 24, 48
    canvas = Canvas(width, height)
    # Перекладина.
    canvas.rect(0, 0, 23, 2, PAL["wood_m"])
    canvas.hline(0, 0, 23, PAL["wood_l"])
    canvas.vline(2, 0, 5, PAL["iron"])
    canvas.vline(21, 0, 5, PAL["iron"])
    # Полотно с вертикальными складками.
    canvas.rect(3, 3, 20, 40, PAL["crimson"])
    canvas.vline(3, 3, 40, PAL["crimson_d"])
    canvas.vline(4, 3, 40, PAL["crimson_l"])
    canvas.vline(19, 3, 40, PAL["crimson_l"])
    canvas.vline(20, 3, 40, PAL["crimson_d"])
    for x in (8, 12, 16):
        canvas.vline(x, 4, 39, PAL["crimson_d"] if x != 12 else PAL["crimson_l"])
    # Знак-оберег: ромб с точкой (солнечный символ, не буква и не логотип).
    for i in range(4):
        canvas.put(12 - i, 14 + i, PAL["gold"])
        canvas.put(12 + i, 14 + i, PAL["gold"])
        canvas.put(12 - i, 21 - i, PAL["gold"])
        canvas.put(12 + i, 21 - i, PAL["gold"])
    canvas.put(12, 17, PAL["gold_l"])
    canvas.put(12, 18, PAL["gold"])
    # Рваный низ.
    for x in range(3, 21):
        cut = 2 if (x % 4 < 2) else 0
        for dy in range(cut):
            canvas.erase(x, 40 - dy)
    canvas.hline(37, 4, 19, PAL["crimson_hi"])
    # Прореха и потёртость.
    canvas.erase(9, 30)
    canvas.erase(10, 30)
    canvas.erase(9, 31)
    canvas.put(15, 33, PAL["crimson_hi"])
    return canvas


# ---------------------------------------------------------------------------
# Лужи с отражениями
# ---------------------------------------------------------------------------


def draw_puddle(width: int, height: int, seed: int) -> Canvas:
    canvas = Canvas(width, height)
    rng = random.Random(seed)
    cx, cy = width / 2.0, height / 2.0
    rx, ry = width / 2.0 - 1, height / 2.0 - 1
    # Форма: несколько наложенных «капель» вместо правильного эллипса.
    lobes = [
        (cx, cy, rx * 0.72, ry * 0.78),
        (cx - rx * 0.34, cy + ry * 0.10, rx * 0.40, ry * 0.55),
        (cx + rx * 0.36, cy - ry * 0.14, rx * 0.36, ry * 0.50),
    ]
    inside = set()
    for lx, ly, lrx, lry in lobes:
        for y in range(height):
            for x in range(width):
                if ((x - lx) / max(0.1, lrx)) ** 2 + ((y - ly) / max(0.1, lry)) ** 2 <= 1.0:
                    inside.add((x, y))
    # Вода: тёмная, с более светлой кромкой влажной земли (иначе лужа не видна).
    for (x, y) in inside:
        canvas.put(x, y, PAL["water"])
    for (x, y) in inside:
        neighbours = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        if any(point not in inside for point in neighbours):
            canvas.put(x, y, PAL["water_l"])
    # Отражения: короткие горизонтальные штрихи, а не сплошной дизеринг.
    for _ in range(max(3, width // 9)):
        x = rng.randrange(3, max(4, width - 5))
        y = rng.randrange(2, max(3, height - 2))
        if (x, y) in inside:
            canvas.hline(y, x, min(width - 2, x + rng.randrange(2, 5)), PAL["water_ll"])
    for _ in range(max(1, width // 20)):
        x = rng.randrange(4, max(5, width - 6))
        y = rng.randrange(2, max(3, height - 2))
        if (x, y) in inside:
            canvas.put(x, y, PAL["fog_cold"])
    # Тёплый отсвет огня в воде.
    for _ in range(max(1, width // 26)):
        x = rng.randrange(4, max(5, width - 6))
        y = rng.randrange(3, max(4, height - 3))
        if (x, y) in inside:
            canvas.hline(y, x, min(width - 2, x + 2), PAL["amber_d"])
            canvas.put(x + 1, y, PAL["amber"])
    return canvas


# ---------------------------------------------------------------------------
# Силуэт ночного леса за частоколом: 200x100
# ---------------------------------------------------------------------------


def draw_forest() -> Canvas:
    width, height = 200, 100
    canvas = Canvas(width, height)
    rng = random.Random(2701)
    # Холм-подложка: плотная тёмная масса, из которой растут силуэты.
    for x in range(width):
        top = int(height * 0.42 + 9 * ((x * 13) % 17) / 17.0)
        for y in range(top, height):
            canvas.put(x, y, PAL["night"])
    # Ели и сухие стволы: узнаваемый силуэт, без микродетали.
    for _ in range(13):
        cx = rng.randrange(4, width - 4)
        top = rng.randrange(2, 26)
        base = rng.randrange(int(height * 0.52), height - 2)
        kind = rng.random()
        if kind < 0.6:
            # Ель: треугольные ярусы с холодной кромкой сверху.
            for y in range(top, base):
                t = (y - top) / float(max(1, base - top))
                half = int(1 + t * 12)
                canvas.hline(y, cx - half, cx + half, PAL["night_b"])
                if (y - top) % 6 == 0:
                    canvas.hline(y, cx - half, cx + half, PAL["slate_d"])
            canvas.put(cx, top, PAL["slate_d"])
        else:
            # Сухой ствол с двумя ветвями: мёртвый лес, а не ёлочная картинка.
            canvas.vline(cx, top + 8, base, PAL["night_b"])
            canvas.line(cx, top + 12, cx - 9, top + 4, PAL["night_b"])
            canvas.line(cx, top + 20, cx + 10, top + 10, PAL["night_b"])
    # Полоса тумана у подножия: лес «растворяется» в ночи.
    for y in range(int(height * 0.62), height):
        depth = (y - height * 0.62) / (height * 0.38)
        for x in range(width):
            if bayer(x, y) < int(3 + depth * 6):
                canvas.put(x, y, PAL["slate_d"] if depth > 0.5 else PAL["night_b"])
    for y in range(height - 6, height):
        for x in range(0, width, 2):
            if bayer(x, y) < 5:
                canvas.put(x, y, PAL["slate"])
    canvas.px = {pos: color for pos, color in canvas.px.items() if color != CLEAR}
    return canvas


# ---------------------------------------------------------------------------
# Мелкие пропсы двора: кадь, поленница, придорожный камень, колесо — лист 96x24
# ---------------------------------------------------------------------------


def draw_small_props() -> Canvas:
    sheet = Canvas(24 * 4, 24)
    # --- Кадь (бочка) ---
    barrel = Canvas(24, 24)
    barrel.rect(6, 6, 17, 21, PAL["wood"])
    barrel.vline(6, 6, 21, PAL["wood_l"])
    barrel.vline(7, 6, 21, PAL["wood_m"])
    barrel.vline(17, 6, 21, PAL["wood_d"])
    for x in range(9, 17, 3):
        barrel.vline(x, 6, 21, PAL["wood_d"])
    for y in (9, 14, 19):
        barrel.hline(y, 5, 18, PAL["iron"])
        barrel.hline(y + 1, 5, 18, PAL["iron_l"])
    barrel.ellipse(11.5, 6, 7, 3, PAL["wood_m"])
    barrel.ellipse(11.5, 6, 5.5, 2, PAL["ink"])
    barrel.hline(4, 6, 17, PAL["wood_l"])
    barrel.rect(5, 22, 19, 23, PAL["earth_d"])
    # --- Поленница ---
    pile = Canvas(24, 24)
    for row, y in enumerate((13, 8, 3)):
        for column, x in enumerate((2, 12)):
            offset = 5 if row == 2 else 0
            log_x0 = x + offset // 2
            pile.rect(log_x0, y, log_x0 + 9, y + 4, PAL["wood"])
            pile.hline(y, log_x0, log_x0 + 9, PAL["wood_l"])
            pile.hline(y + 4, log_x0, log_x0 + 9, PAL["wood_d"])
            pile.ellipse(log_x0 + 1.5, y + 2, 1.6, 1.8, PAL["wood_ll"])
            pile.put(log_x0 + 1, y + 2, PAL["wood_m"])
    pile.rect(2, 18, 21, 19, PAL["earth_d"])
    # --- Придорожный камень с мхом ---
    stone = Canvas(24, 24)
    stone.rect(7, 8, 16, 21, PAL["stone"])
    stone.rect(8, 7, 15, 8, PAL["stone_l"])
    stone.vline(7, 8, 21, PAL["stone_l"])
    stone.vline(16, 8, 21, PAL["stone_d"])
    stone.hline(6, 9, 14, PAL["stone_l"])
    stone.put(9, 6, PAL["stone_l"])
    for _ in range(6):
        stone.put(8 + (_ * 3) % 8, 12 + (_ * 2) % 7, PAL["stone_d"])
    stone.hline(20, 8, 15, PAL["moss"])
    stone.hline(19, 9, 13, PAL["moss_d"])
    stone.rect(6, 22, 17, 23, PAL["earth_d"])
    # --- Колесо от телеги ---
    wheel = Canvas(24, 24)
    wheel.ellipse(11.5, 12, 8, 8, PAL["wood_m"])
    wheel.ellipse(11.5, 12, 6.5, 6.5, PAL["wood_d"])
    wheel.ellipse(11.5, 12, 5.4, 5.4, PAL["earth_d"])
    for dx, dy in ((0, -5), (0, 5), (-5, 0), (5, 0)):
        wheel.line(11, 12, 11 + dx, 12 + dy, PAL["wood"])
        wheel.line(12, 12, 12 + dx, 12 + dy, PAL["wood_l"])
    wheel.ellipse(11.5, 12, 1.8, 1.8, PAL["iron_l"])
    wheel.put(4, 7, PAL["wood_l"])
    # Сборка листа: каждый предмет — в своём кадре 24x24.
    sheet.composite(barrel, 0)
    sheet.composite(pile, 24)
    sheet.composite(stone, 48)
    sheet.composite(wheel, 72)
    return sheet


# ---------------------------------------------------------------------------
# Вспомогательные текстуры
# ---------------------------------------------------------------------------


def build_textures() -> dict[str, Image.Image]:
    return {
        "glow_warm_24": glow_radial(128, (255, 203, 138, 255), 215, power=2.1, steps=20),
        "glow_cold_24": glow_radial(128, (150, 180, 226, 255), 150, power=2.6, steps=16),
        "fog_a_24": fog_layer(320, 160, 2801, max_alpha=30),
        "fog_b_24": fog_layer(320, 160, 2802, max_alpha=22),
        "vignette_24": vignette(480, 270, max_alpha=196, inner=0.30),
        "shadow_24": contact_shadow(44, 16, 170),
    }


# ---------------------------------------------------------------------------
# Сборка
# ---------------------------------------------------------------------------

ASSETS = {
    "ground_calib_24.png": draw_ground_tileset,
    "palisade_24.png": draw_palisade,
    "gate_calib_24.png": draw_gate,
    "izba_24.png": draw_izba,
    "chapel_24.png": draw_chapel,
    "dead_tree_24.png": draw_dead_tree,
    "banner_24.png": draw_banner,
    "forest_24.png": draw_forest,
    "props_calib_24.png": draw_small_props,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="tools/stage3_calibration/source")
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, dict] = {}
    for name, builder in ASSETS.items():
        canvas: Canvas = builder()
        path = canvas.save(out_dir / name)
        written[name] = {"size": [canvas.width, canvas.height], "path": str(path)}

    # Факельный лист: два кадра огня 24x72 в одном ряду.
    torch_sheet = Image.new("RGBA", (24 * 2, 72), CLEAR)
    for frame in range(2):
        torch_sheet.alpha_composite(draw_torch(frame).image(), (frame * 24, 0))
    torch_path = out_dir / "torch_24.png"
    torch_sheet.save(torch_path)
    written["torch_24.png"] = {"size": [48, 72], "path": str(torch_path), "frames": 2}

    # Лужи: три размера, чтобы не повторялись.
    for name, (w, h, seed) in {
        "puddle_a_24.png": (54, 18, 2901),
        "puddle_b_24.png": (36, 14, 2902),
        "puddle_c_24.png": (72, 24, 2903),
    }.items():
        canvas = draw_puddle(w, h, seed)
        path = canvas.save(out_dir / name)
        written[name] = {"size": [w, h], "path": str(path)}

    textures = build_textures()
    for name, image in textures.items():
        path = out_dir / f"{name}.png"
        image.save(path)
        written[f"{name}.png"] = {"size": list(image.size), "path": str(path)}

    report = {
        "art_revision": "3.1b",
        "status": "ASSET_DRAFT",
        "tile_px": TILE,
        "assets": written,
        "note": "калибровочный набор: не финальный арт и не утверждённая локация (D10)",
    }
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
