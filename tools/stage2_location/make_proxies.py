"""Генератор PROXY_TECHNICAL-прокси для задачи 2.1 (Этап 2).

Что делает: рисует по одной «рецептуре» модульный тайлсет, спрайт-лист героя,
пропсы (дерево, ворота) и текстуру света в трёх пиксельных сетках — 16, 24 и 32 px.
Это НЕ финальный арт: изображения помечены PROXY_TECHNICAL (D8) и нужны только
для сравнения кандидатных пиксельных констант (D9) на реальных кадрах игры.

Запуск:
    python tools/stage2_location/make_proxies.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "game" / "prototype" / "art"

# Сетки-кандидаты: тайл (px) -> высота спрайта героя (px). Герой всегда 2 тайла.
GRIDS = ((16, 32), (24, 48), (32, 64))

TILESET_COLUMNS = 4
TILE_COUNT = 12

# Индексы тайлов в атласе: (col, row) = (i % 4, i // 4).
T_DIRT_A = 0
T_DIRT_B = 1
T_PATH = 2
T_GRASS = 3
T_MUD = 4
T_PLANKS = 5
T_WALL_A = 6
T_WALL_B = 7
T_FENCE = 8
T_POST = 9
T_STONE_DARK = 10
T_VOID = 11

# Непроходимые тайлы: стены, частокол, столб, камень, «пустота».
SOLID_TILES = (T_WALL_A, T_WALL_B, T_FENCE, T_POST, T_STONE_DARK, T_VOID)

PAL = {
    "night": (27, 34, 48, 255),
    "slate": (57, 66, 76, 255),
    "ash": (119, 115, 109, 255),
    "gold": (170, 144, 104, 255),
    "ivory": (198, 193, 181, 255),
    "crimson": (108, 39, 57, 255),
    "crimson_d": (74, 26, 39, 255),
    "dirt": (74, 62, 49, 255),
    "dirt_d": (56, 46, 37, 255),
    "dirt_l": (96, 81, 63, 255),
    "moss": (55, 70, 52, 255),
    "moss_d": (40, 52, 39, 255),
    "moss_l": (78, 96, 70, 255),
    "stone": (74, 77, 82, 255),
    "stone_d": (52, 55, 60, 255),
    "stone_l": (98, 101, 106, 255),
    "wood": (70, 53, 40, 255),
    "wood_d": (48, 36, 27, 255),
    "wood_l": (94, 72, 54, 255),
    "void": (18, 21, 28, 255),
    "hair": (44, 36, 30, 255),
    "hair_l": (70, 58, 48, 255),
    "skin": (158, 126, 98, 255),
    "skin_d": (118, 92, 69, 255),
    "pants": (62, 60, 70, 255),
    "pants_d": (44, 42, 50, 255),
}

CLEAR = (0, 0, 0, 0)


def rect(img: Image.Image, x0: int, y0: int, x1: int, y1: int, color) -> None:
    """Заливка прямоугольника в пиксельных координатах (x1/y1 — исключающие)."""
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    if x1 <= x0 or y1 <= y0:
        return
    img.paste(color, (x0, y0, x1, y1))


def px(img: Image.Image, x: int, y: int, color) -> None:
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), color)


def add_outline(img: Image.Image, color, alpha_threshold: int = 1) -> None:
    """Тёмный контур в 1 px вокруг непрозрачных пикселей: силуэт читается на любом фоне."""
    solid = img.load()
    edges: list[tuple[int, int]] = []
    for y in range(img.height):
        for x in range(img.width):
            if solid[x, y][3] >= alpha_threshold:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < img.width and 0 <= ny < img.height):
                    continue
                if solid[nx, ny][3] >= alpha_threshold:
                    edges.append((x, y))
                    break
    for x, y in edges:
        img.putpixel((x, y), color)


def tile_dirt(img, ox, oy, t, rng, base, dark, light) -> None:
    """Земля: ровный базовый тон и крапины, не касающиеся края тайла (без шва)."""
    rect(img, ox, oy, ox + t, oy + t, base)
    for _ in range(max(1, int((t - 2) * (t - 2) * 0.16))):
        x = rng.randrange(1, max(2, t - 1))
        y = rng.randrange(1, max(2, t - 1))
        px(img, ox + x, oy + y, rng.choice((dark, light)))
    stone_w = max(2, t // 7)
    for _ in range(max(1, t // 10)):
        x = rng.randrange(2, max(3, t - stone_w - 1))
        y = rng.randrange(2, max(3, t - stone_w - 1))
        rect(img, ox + x, oy + y, ox + x + stone_w, oy + y + max(1, stone_w // 2), PAL["ash"])


def tile_path(img, ox, oy, t, rng) -> None:
    rect(img, ox, oy, ox + t, oy + t, PAL["stone_d"])
    slab = t // 2
    for row in range(2):
        for col in range(2):
            x0 = ox + col * slab + 1
            y0 = oy + row * slab + 1
            tone = rng.choice((PAL["stone"], PAL["stone_l"]))
            rect(img, x0, y0, x0 + slab - 1, y0 + slab - 1, tone)
            rect(img, x0, y0, x0 + slab - 1, y0 + 1, PAL["stone_l"])
            rect(img, x0, y0 + slab - 2, x0 + slab - 1, y0 + slab - 1, PAL["stone_d"])
    # Равномерная затирка по краю тайла: соседние плиты стыкуются без шва.
    rect(img, ox, oy, ox + t, oy + 1, PAL["stone_d"])
    rect(img, ox, oy + t - 1, ox + t, oy + t, PAL["stone_d"])
    rect(img, ox, oy, ox + 1, oy + t, PAL["stone_d"])
    rect(img, ox + t - 1, oy, ox + t, oy + t, PAL["stone_d"])
    for _ in range(max(1, int(t * t * 0.05))):
        x = rng.randrange(1, max(2, t - 1))
        y = rng.randrange(1, max(2, t - 1))
        px(img, ox + x, oy + y, rng.choice((PAL["stone_d"], PAL["ash"])))


def tile_grass(img, ox, oy, t, rng) -> None:
    rect(img, ox, oy, ox + t, oy + t, PAL["moss_d"])
    for _ in range(max(3, int(t * t * 0.07))):
        x = rng.randrange(1, max(2, t - 1))
        y = rng.randrange(1, max(2, t - 1))
        px(img, ox + x, oy + y, rng.choice((PAL["moss"], PAL["moss_l"])))
    for _ in range(max(2, t // 8)):
        x = rng.randrange(1, max(2, t - 1))
        y = rng.randrange(2, max(3, t - 1))
        px(img, ox + x, oy + y, PAL["moss_l"])
        px(img, ox + x, oy + y - 1, PAL["moss_l"])


def tile_mud(img, ox, oy, t, rng) -> None:
    rect(img, ox, oy, ox + t, oy + t, PAL["dirt_d"])
    w = max(2, t // 6)
    for _ in range(max(2, t // 6)):
        # Лужи держатся в глубине тайла: крайний пиксель остаётся ровным (без шва).
        x = rng.randrange(2, max(3, t - w - 2))
        y = rng.randrange(2, max(3, t - w - 2))
        rect(img, ox + x, oy + y, ox + x + w, oy + y + max(1, w // 2), PAL["night"])
    for _ in range(max(1, int(t * t * 0.08))):
        x = rng.randrange(1, max(2, t - 1))
        y = rng.randrange(1, max(2, t - 1))
        px(img, ox + x, oy + y, PAL["dirt"])


def tile_planks(img, ox, oy, t, rng) -> None:
    """Настил: доски с внутренними швами; крайние пиксели каймы одноцветны (без шва)."""
    rect(img, ox, oy, ox + t, oy + t, PAL["wood"])
    board = max(2, t // 4)
    y = oy + board
    while y < oy + t:
        rect(img, ox + 1, y, ox + t - 1, y + 1, PAL["wood_d"])
        y += board
    for row in range(max(1, t // board)):
        base = oy + row * board
        for _ in range(max(1, t // 8)):
            gx = rng.randrange(1, max(2, t - 1))
            gy = base + board // 2
            if gy < oy + t - 1:
                px(img, ox + gx, gy, PAL["wood_d"])
    rect(img, ox, oy + t - 1, ox + t, oy + t, PAL["wood_d"])
    rect(img, ox, oy, ox + t, oy + 1, PAL["wood_l"])


def tile_wall(img, ox, oy, t, rng, offset: bool) -> None:
    rect(img, ox, oy, ox + t, oy + t, PAL["stone_d"])
    rows = 3 if t >= 24 else 2
    block_h = t // rows
    for row in range(rows):
        y0 = oy + row * block_h
        base_x = ox + (t // 4 if offset != (row % 2 == 0) else 0)
        x = base_x - t // 4
        while x < ox + t:
            x0 = x + 1
            x1 = x + t // 2 - 1
            tone = rng.choice((PAL["slate"], PAL["stone"], PAL["ash"]))
            rect(img, x0, y0 + 1, x1, y0 + block_h, tone)
            rect(img, x0, y0 + 1, x1, y0 + 2, PAL["stone_l"])
            rect(img, x0, y0 + block_h - 1, x1, y0 + block_h, PAL["stone_d"])
            x += t // 2
    rect(img, ox, oy, ox + t, oy + 1, PAL["ash"])
    rect(img, ox, oy + t - 1, ox + t, oy + t, PAL["night"])


def tile_fence(img, ox, oy, t, rng) -> None:
    """Частокол: вертикальные доски с просветами (прозрачный фон)."""
    picket_w = max(2, int(t * 0.22))
    gap = max(1, int(t * 0.14))
    x = ox + gap // 2
    top = oy + int(t * 0.10)
    bottom = oy + t - int(t * 0.12)
    while x + picket_w <= ox + t:
        rect(img, x, top, x + picket_w, bottom, PAL["wood"])
        rect(img, x, top, x + 1, bottom, PAL["wood_l"])
        rect(img, x + picket_w - 1, top, x + picket_w, bottom, PAL["wood_d"])
        px(img, x, bottom - 1, PAL["wood_d"])
        px(img, x + picket_w // 2, top, PAL["wood_l"])
        x += picket_w + gap
    rail_y = oy + int(t * 0.42)
    rect(img, ox, rail_y, ox + t, rail_y + max(1, t // 10), PAL["wood_d"])
    rect(img, ox, rail_y, ox + t, rail_y + 1, PAL["wood"])
    rect(img, ox, oy + t - max(1, t // 14), ox + t, oy + t, PAL["wood_d"])


def tile_post(img, ox, oy, t, rng) -> None:
    rect(img, ox, oy, ox + t, oy + t, PAL["wood_d"])
    rect(img, ox + 1, oy + 1, ox + t - 1, oy + t - 1, PAL["wood"])
    rect(img, ox + 1, oy + 1, ox + max(2, t // 5), oy + t - 1, PAL["wood_l"])
    rect(img, ox + t - max(2, t // 6), oy, ox + t, oy + t, PAL["night"])
    for _ in range(max(1, t // 8)):
        gx = rng.randrange(2, max(3, t - 2))
        gy = rng.randrange(1, max(2, t - 2))
        rect(img, ox + gx, oy + gy, ox + gx + 1, oy + gy + max(1, t // 8), PAL["wood_d"])


def tile_stone_dark(img, ox, oy, t, rng) -> None:
    rect(img, ox, oy, ox + t, oy + t, PAL["stone_d"])
    for _ in range(max(1, int(t * t * 0.12))):
        x = rng.randrange(1, max(2, t - 1))
        y = rng.randrange(1, max(2, t - 1))
        px(img, ox + x, oy + y, rng.choice((PAL["night"], PAL["stone"])))


def tile_void(img, ox, oy, t, rng) -> None:
    rect(img, ox, oy, ox + t, oy + t, PAL["void"])
    for _ in range(max(1, int(t * t * 0.05))):
        x = rng.randrange(1, max(2, t - 1))
        y = rng.randrange(1, max(2, t - 1))
        px(img, ox + x, oy + y, PAL["night"])


def build_tileset(tile: int, out: Path) -> None:
    cols = TILESET_COLUMNS
    rows = (TILE_COUNT + cols - 1) // cols
    img = Image.new("RGBA", (cols * tile, rows * tile), CLEAR)
    for index in range(TILE_COUNT):
        ox = (index % cols) * tile
        oy = (index // cols) * tile
        rng = random.Random(1000 + tile * 31 + index)
        if index == T_DIRT_A:
            tile_dirt(img, ox, oy, tile, rng, PAL["dirt"], PAL["dirt_d"], PAL["dirt_l"])
        elif index == T_DIRT_B:
            # Тот же базовый тон, что и у T_DIRT_A: иначе вариант земли читается
            # как шахматная доска из тайлов, то есть как шов.
            tile_dirt(img, ox, oy, tile, rng, PAL["dirt"], PAL["dirt_d"], PAL["dirt_l"])
        elif index == T_PATH:
            tile_path(img, ox, oy, tile, rng)
        elif index == T_GRASS:
            tile_grass(img, ox, oy, tile, rng)
        elif index == T_MUD:
            tile_mud(img, ox, oy, tile, rng)
        elif index == T_PLANKS:
            tile_planks(img, ox, oy, tile, rng)
        elif index == T_WALL_A:
            tile_wall(img, ox, oy, tile, rng, offset=False)
        elif index == T_WALL_B:
            tile_wall(img, ox, oy, tile, rng, offset=True)
        elif index == T_FENCE:
            tile_fence(img, ox, oy, tile, rng)
        elif index == T_POST:
            tile_post(img, ox, oy, tile, rng)
        elif index == T_STONE_DARK:
            tile_stone_dark(img, ox, oy, tile, rng)
        elif index == T_VOID:
            tile_void(img, ox, oy, tile, rng)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def build_hero(height: int, out: Path, frames: int = 4) -> None:
    """Простой 4-кадровый силуэт идущего героя: повязка, объёмные волосы, голый торс (D7)."""
    sheet = Image.new("RGBA", (height * frames, height), CLEAR)
    for frame in range(frames):
        img = Image.new("RGBA", (height, height), CLEAR)
        bob = -1 if frame in (1, 3) else 0
        swing = (frame - 1.5) / 1.5 if frame % 2 == 1 else 0.0
        cx = height // 2
        top = max(1, int(height * 0.06)) + bob
        head_h = int(height * 0.34)
        head_w = int(height * 0.50)
        # Волосы одинаково спереди и сзади (D7).
        rect(img, cx - head_w // 2, top, cx + head_w // 2, top + head_h, PAL["hair"])
        rect(img, cx - head_w // 2, top, cx - head_w // 2 + max(1, head_w // 5), top + head_h, PAL["hair_l"])
        rect(img, cx - head_w // 2, top + head_h - 2, cx + head_w // 2, top + head_h, PAL["hair_l"])
        # Повязка на глазах.
        band_y = top + int(head_h * 0.52)
        band_h = max(2, int(height * 0.06))
        rect(img, cx - head_w // 2, band_y, cx + head_w // 2, band_y + band_h, PAL["ivory"])
        rect(img, cx - head_w // 2, band_y + band_h - 1, cx + head_w // 2, band_y + band_h, PAL["ash"])
        # Торс.
        torso_top = top + head_h
        torso_h = int(height * 0.28)
        torso_w = int(height * 0.40)
        rect(img, cx - torso_w // 2, torso_top, cx + torso_w // 2, torso_top + torso_h, PAL["skin"])
        rect(
            img,
            cx - torso_w // 2,
            torso_top,
            cx - torso_w // 2 + max(1, torso_w // 4),
            torso_top + torso_h,
            PAL["skin_d"],
        )
        # Руки.
        arm_w = max(2, int(height * 0.10))
        arm_shift = int(swing * height * 0.04)
        rect(img, cx - torso_w // 2 - arm_w, torso_top + 1 + arm_shift, cx - torso_w // 2, torso_top + torso_h + 1, PAL["skin_d"])
        rect(img, cx + torso_w // 2, torso_top + 1 - arm_shift, cx + torso_w // 2 + arm_w, torso_top + torso_h + 1, PAL["skin_d"])
        # Штаны и шаг.
        legs_top = torso_top + torso_h
        leg_h = max(3, int(height * 0.24))
        leg_w = max(2, int(torso_w * 0.42))
        gap = max(1, torso_w - leg_w * 2)
        step = int(swing * height * 0.05)
        rect(img, cx - leg_w - gap // 2, legs_top, cx - gap // 2, legs_top + leg_h + step, PAL["pants"])
        rect(img, cx + gap // 2, legs_top, cx + gap // 2 + leg_w, legs_top + leg_h - step, PAL["pants"])
        rect(img, cx - leg_w - gap // 2, legs_top + leg_h + step - 2, cx - gap // 2, legs_top + leg_h + step, PAL["pants_d"])
        rect(img, cx + gap // 2, legs_top + leg_h - step - 2, cx + gap // 2 + leg_w, legs_top + leg_h - step, PAL["pants_d"])
        add_outline(img, PAL["void"])
        sheet.alpha_composite(img, (frame * height, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def build_tree(tile: int, out: Path) -> None:
    w, h = tile * 2, tile * 3
    img = Image.new("RGBA", (w, h), CLEAR)
    rng = random.Random(2000 + tile)
    trunk_w = max(3, int(tile * 0.55))
    cx = w // 2
    # Тень у корней.
    rect(img, cx - tile // 2, h - max(2, tile // 5), cx + tile // 2, h, (0, 0, 0, 90))
    # Ствол.
    base_y = int(h * 0.52)
    bottom = h - max(1, tile // 6)
    rect(img, cx - trunk_w // 2, base_y, cx + trunk_w // 2, bottom, PAL["wood"])
    rect(img, cx - trunk_w // 2, base_y, cx - trunk_w // 2 + max(1, trunk_w // 4), bottom, PAL["wood_l"])
    rect(img, cx + trunk_w // 2 - max(1, trunk_w // 5), base_y, cx + trunk_w // 2, bottom, PAL["wood_d"])
    # Крона: несколько перекрывающихся масс.
    canopy = Image.new("RGBA", (w, h), CLEAR)
    d = ImageDraw.Draw(canopy)
    blobs = (
        (cx, int(h * 0.33), int(w * 0.46)),
        (cx - int(w * 0.20), int(h * 0.42), int(w * 0.30)),
        (cx + int(w * 0.21), int(h * 0.44), int(w * 0.29)),
        (cx, int(h * 0.20), int(w * 0.30)),
    )
    for bx, by, radius in blobs:
        d.ellipse((bx - radius, by - radius, bx + radius, by + radius), fill=PAL["moss_d"])
    img.alpha_composite(canopy)
    # Световая кромка сверху-слева и листва.
    for y in range(int(h * 0.10), int(h * 0.62)):
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
            if a == 0:
                continue
            above = img.getpixel((x, max(0, y - 1)))
            if above[3] == 0 and y < h * 0.42:
                px(img, x, y, PAL["moss_l"])
            elif above[0] == PAL["moss_d"][0] and above[3] and rng.random() < 0.10:
                px(img, x, y, rng.choice((PAL["moss"], PAL["moss_l"])))
    for _ in range(tile * 3):
        x = rng.randrange(w)
        y = rng.randrange(int(h * 0.08), int(h * 0.60))
        if img.getpixel((x, y))[3]:
            px(img, x, y, rng.choice((PAL["moss"], PAL["moss_l"], PAL["moss_d"])))
    add_outline(img, PAL["void"], alpha_threshold=60)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def build_gate(tile: int, out: Path) -> None:
    """Техническая зона-«ворота»: два столба, верхняя перекладина, притолока и знамя."""
    w, h = tile * 3, tile * 2
    img = Image.new("RGBA", (w, h), CLEAR)
    rng = random.Random(3000 + tile)
    post_w = max(4, int(tile * 0.75))
    beam_h = max(3, int(tile * 0.42))
    # Столбы.
    for x0 in (0, w - post_w):
        rect(img, x0, 0, x0 + post_w, h, PAL["wood_d"])
        rect(img, x0 + 1, 1, x0 + post_w - 1, h - 1, PAL["wood"])
        rect(img, x0 + 1, 1, x0 + 1 + max(1, post_w // 4), h - 1, PAL["wood_l"])
        rect(img, x0 + post_w - max(2, post_w // 5), 0, x0 + post_w, h, PAL["night"])
        for _ in range(max(2, tile // 6)):
            gy = rng.randrange(2, max(3, h - 2))
            rect(img, x0 + 2, gy, x0 + post_w - 2, gy + 1, PAL["wood_d"])
    # Верхняя перекладина поверх столбов.
    rect(img, 0, 0, w, beam_h, PAL["wood_d"])
    rect(img, 0, 0, w, max(1, beam_h // 3), PAL["wood_l"])
    rect(img, 0, beam_h - max(1, beam_h // 4), w, beam_h, PAL["night"])
    for x in range(0, w, max(3, tile // 2)):
        rect(img, x, 0, min(w, x + max(1, tile // 10)), beam_h, PAL["wood_d"])
    # Притолока (нижняя перекладина) и знамя.
    lintel_y = int(h * 0.62)
    rect(img, post_w, lintel_y, w - post_w, lintel_y + max(2, tile // 6), PAL["wood"])
    rect(img, post_w, lintel_y, w - post_w, lintel_y + 1, PAL["wood_l"])
    banner_w = max(4, int(tile * 0.8))
    banner_x = w // 2 - banner_w // 2
    rect(img, banner_x, beam_h, banner_x + banner_w, beam_h + int(h * 0.32), PAL["crimson"])
    rect(img, banner_x, beam_h, banner_x + 1, beam_h + int(h * 0.32), PAL["crimson_d"])
    rect(img, banner_x + banner_w - 1, beam_h, banner_x + banner_w, beam_h + int(h * 0.32), PAL["crimson_d"])
    rect(img, banner_x, beam_h + int(h * 0.32) - 1, banner_x + banner_w, beam_h + int(h * 0.32), PAL["crimson_d"])
    # Мох на столбах.
    for _ in range(tile):
        x = rng.randrange(w)
        y = rng.randrange(1, max(2, h - 1))
        if img.getpixel((x, y))[3] and img.getpixel((x, y)) in (PAL["wood"], PAL["wood_l"]):
            if rng.random() < 0.25:
                px(img, x, y, PAL["moss"])
    add_outline(img, PAL["void"])
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def build_light(out: Path, size: int = 64) -> None:
    """Радиальный градиент с дизерингом: пиксельный тёплый свет без грубых ступеней."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bayer = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
    cx = cy = (size - 1) / 2.0
    warm = (255, 214, 160)
    steps = 24
    for y in range(size):
        for x in range(size):
            dx = (x - cx) / cx
            dy = (y - cy) / cy
            r = (dx * dx + dy * dy) ** 0.5
            if r > 1.0:
                continue
            value = (1.0 - r) ** 1.6
            threshold = (bayer[y % 4][x % 4] + 0.5) / 16.0
            quantized = int(value * steps) / steps
            if value * steps - int(value * steps) > threshold:
                quantized = (int(value * steps) + 1) / steps
            alpha = int(max(0.0, min(1.0, quantized)) * 255)
            if alpha > 0:
                img.putpixel((x, y), (*warm, alpha))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def main() -> None:
    manifest = {"status": "PROXY_TECHNICAL", "grids": []}
    for tile, hero in GRIDS:
        tileset_path = ART / "tilesets" / f"tileset_{tile}.png"
        hero_path = ART / "sprites" / f"hero_proxy_{hero}.png"
        tree_path = ART / "props" / f"tree_{tile}.png"
        gate_path = ART / "props" / f"gate_{tile}.png"
        build_tileset(tile, tileset_path)
        build_hero(hero, hero_path)
        build_tree(tile, tree_path)
        build_gate(tile, gate_path)
        manifest["grids"].append(
            {
                "tile_px": tile,
                "hero_height_px": hero,
                "tileset": str(tileset_path.relative_to(ROOT)).replace("\\", "/"),
                "tileset_size": f"{TILESET_COLUMNS * tile}x{((TILE_COUNT + TILESET_COLUMNS - 1) // TILESET_COLUMNS) * tile}",
                "tiles": TILE_COUNT,
                "solid_tiles": list(SOLID_TILES),
                "hero_sheet": str(hero_path.relative_to(ROOT)).replace("\\", "/"),
                "hero_frames": 4,
                "tree": str(tree_path.relative_to(ROOT)).replace("\\", "/"),
                "gate": str(gate_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
    light_path = ART / "lights" / "light_soft.png"
    build_light(light_path)
    manifest["light"] = str(light_path.relative_to(ROOT)).replace("\\", "/")
    manifest_path = ROOT / "tools" / "stage2_location" / "proxy_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for grid in manifest["grids"]:
        print(f"tileset {grid['tile_px']}px -> {grid['tileset']} ({grid['tileset_size']})")
    print(f"light -> {manifest['light']}")
    print(f"manifest -> {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
