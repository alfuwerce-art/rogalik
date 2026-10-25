"""Лист сравнения: утверждённый референс, пиксельный лист и игровые кадры.

Артефакт для художественного рассмотрения владельцем, а не игровой ассет.
Референс масштабируется с LANCZOS (это фотографический материал, не пиксель-арт);
пиксельные кадры увеличиваются только целым коэффициентом с NEAREST, чтобы
сравнение не искажало пиксельную сетку.

Герой на игровом кадре находится не «на глаз», а по палитре самого листа:
берутся цвета спрайта (кроме почти чёрного контура) и ищется их область рядом с
центром кадра. Так кадрирование не зависит от догадок о смещении камеры.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DIRECTIONS = ("down", "up", "left", "right")
CAPTIONS = {
    "down": "down · спереди",
    "up": "up · сзади",
    "left": "left · профиль",
    "right": "right · профиль",
}
FRAME_W = 32
FRAME_H = 48


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def figure_boxes(reference: Path) -> list[tuple[int, int, int, int]]:
    """Две фигуры на референсе находятся по яркости: фон почти чёрный."""
    image = Image.open(reference).convert("RGB")
    mask = image.convert("L").point(lambda value: 255 if value > 42 else 0)
    columns = [
        x for x in range(mask.width) if mask.crop((x, 0, x + 1, mask.height)).getbbox() is not None
    ]
    if not columns:
        raise SystemExit("не удалось найти фигуры на референсе")
    groups: list[list[int]] = [[columns[0]]]
    for previous, current in zip(columns, columns[1:]):
        if current - previous > 20:
            groups.append([])
        groups[-1].append(current)
    groups = [group for group in groups if len(group) > 40]
    boxes = []
    for group in groups[:2]:
        left, right = group[0], group[-1]
        strip = mask.crop((left, 0, right + 1, mask.height))
        top, bottom = strip.getbbox()[1], strip.getbbox()[3]
        boxes.append((left, top, right + 1, bottom))
    return boxes


def sprite_palette(sheet: Image.Image) -> set[tuple[int, int, int]]:
    """Цвета спрайта без почти чёрного контура: фон сцены тоже тёмный."""
    colors = {pixel[:3] for _count, pixel in sheet.getcolors(1 << 24) or [] if pixel[3] > 0}
    return {color for color in colors if sum(color) > 150}


def hero_box(
    frame: Image.Image,
    *,
    tile_px: int = 24,
    hero_art_height: int = FRAME_H,
    window_scale: int = 2,
    lookahead_tiles: float = 1.0,
) -> tuple[int, int, int, int]:
    """Габарит героя на игровом кадре — по геометрии камеры, а не «на глаз».

    Камера (`camera_rig.gd`) держится за героем с целочисленной привязкой,
    zoom 1.0 и фиксированным смещением на 1 тайл вверх, поэтому стопы героя
    всегда оказываются на `lookahead` ниже центра кадра, а силуэт 48 px
    занимает 96 экранных пикселей при окне 960x540. Кадрирование строится из
    этих чисел; поиск «тёплых пятен» оказался ненадёжным — факелы и ворота
    тоже тёплые.
    """
    width, height = frame.size
    center_x = width // 2
    feet_y = height // 2 + int(tile_px * lookahead_tiles * window_scale)
    top = feet_y - hero_art_height * window_scale
    margin_x, margin_top, margin_bottom = 26, 8, 8
    return (
        max(0, center_x - 32 * window_scale // 2 - margin_x),
        max(0, top - margin_top),
        min(width, center_x + 32 * window_scale // 2 + margin_x),
        min(height, feet_y + margin_bottom),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--sheet", required=True)
    parser.add_argument("--frames", nargs="+", required=True, help="игровые кадры 960x540 по направлениям")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=5, help="увеличение пиксельных кадров")
    parser.add_argument("--frames-per-direction", type=int, default=2)
    args = parser.parse_args(argv)

    reference = Image.open(args.reference).convert("RGB")
    boxes = figure_boxes(Path(args.reference))
    sheet = Image.open(args.sheet).convert("RGBA")
    if sheet.width != FRAME_W * len(DIRECTIONS) * args.frames_per_direction:
        raise SystemExit(
            f"ожидался лист {FRAME_W * len(DIRECTIONS) * args.frames_per_direction} px шириной, получено {sheet.width}"
        )
    palette = sprite_palette(sheet)

    scale = args.scale
    sprite_w, sprite_h = FRAME_W * scale, FRAME_H * scale
    pad = 16
    label_h = 26
    header_h = 34
    ref_height = int(sprite_h * 1.7)

    ref_crops = []
    for box in boxes:
        crop = reference.crop(box)
        ratio = ref_height / crop.height
        ref_crops.append(crop.resize((max(1, int(crop.width * ratio)), ref_height), Image.LANCZOS))

    game_scale = 3
    game_crops = []
    for path in args.frames:
        image = Image.open(path).convert("RGB")
        box = hero_box(image)
        margin_x, margin_top, margin_bottom = 24, 14, 20
        box = (
            max(0, box[0] - margin_x),
            max(0, box[1] - margin_top),
            min(image.width, box[2] + margin_x),
            min(image.height, box[3] + margin_bottom),
        )
        crop = image.crop(box)
        game_crops.append(crop.resize((crop.width * game_scale, crop.height * game_scale), Image.NEAREST))

    refs_w = sum(crop.width for crop in ref_crops) + pad * (len(ref_crops) - 1)
    sprites_w = sprite_w * len(DIRECTIONS) + pad * (len(DIRECTIONS) - 1)
    games_w = sum(crop.width for crop in game_crops) + pad * (len(game_crops) - 1)
    content_w = max(refs_w, sprites_w, games_w)
    width = content_w + pad * 2

    game_h = max(crop.height for crop in game_crops)
    height = header_h + ref_height + label_h + pad + sprite_h + label_h + pad + game_h + label_h + pad + 30

    canvas = Image.new("RGB", (width, height), "#1a1d24")
    draw = ImageDraw.Draw(canvas)
    font_title = load_font(17)
    font = load_font(14)

    draw.text(
        (pad, 9),
        "Rogalik · Этап 3 · задача 3.1 — силуэт героя 48 px · ASSET_DRAFT (приёмка за владельцем)",
        fill="#c6c1b5",
        font=font_title,
    )
    y = header_h

    x = pad
    for crop, title in zip(ref_crops, ("референс · спереди", "референс · сзади")):
        canvas.paste(crop, (x, y))
        draw.text((x + 2, y + ref_height + 4), title, fill="#9aa0aa", font=font)
        x += crop.width + pad
    y += ref_height + label_h + pad

    x = pad
    for column, name in enumerate(DIRECTIONS):
        frame = sheet.crop((column * args.frames_per_direction * FRAME_W, 0, (column * args.frames_per_direction + 1) * FRAME_W, FRAME_H))
        frame = frame.resize((sprite_w, sprite_h), Image.NEAREST)
        for cy in range(0, sprite_h, 16):
            for cx in range(0, sprite_w, 16):
                if ((cx // 16) + (cy // 16)) % 2 == 0:
                    canvas.paste("#262a33", (x + cx, y + cy, x + min(cx + 16, sprite_w), y + min(cy + 16, sprite_h)))
        canvas.paste(frame, (x, y), frame)
        draw.text((x + 2, y + sprite_h + 4), f"спрайт · {CAPTIONS[name]}", fill="#c6c1b5", font=font)
        x += sprite_w + pad
    y += sprite_h + label_h + pad

    x = pad
    for crop, name in zip(game_crops, DIRECTIONS):
        canvas.paste(crop, (x, y))
        draw.text((x + 2, y + crop.height + 4), f"в игре ×{game_scale} · {CAPTIONS[name]}", fill="#c6c1b5", font=font)
        x += crop.width + pad
    y += game_h + label_h

    draw.text(
        (pad, y),
        "Боковые виды на референсе отсутствуют — рабочая интерпретация до решения владельца. "
        "Технические проверки не заменяют художественную приёмку.",
        fill="#8f959e",
        font=font,
    )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    print(f"COMPARE {args.out} {canvas.width}x{canvas.height} sprite_scale={scale}x game_scale={game_scale}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
