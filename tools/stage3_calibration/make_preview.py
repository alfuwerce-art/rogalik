"""Контактный лист калибровочного набора: увеличенные ассеты с подписями.

Это рабочий инструмент проверки рисунка, а не игровой кадр: он показывает, как
нарисованы ассеты, но не заменяет реальный кадр Godot. Подписи рисуются шрифтом
по умолчанию (не пиксельным) — по ним нельзя судить о пиксельном стиле.

    python tools/stage3_calibration/make_preview.py --source tools/stage3_calibration/source \
        --out reports/stage3b_assets_preview.png --scale 3
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

BACKGROUND = (18, 22, 30, 255)
LABEL = (198, 193, 181)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="tools/stage3_calibration/source")
    parser.add_argument("--out", default="reports/stage3b_assets_preview.png")
    parser.add_argument("--scale", type=int, default=3)
    parser.add_argument("--columns", type=int, default=2)
    args = parser.parse_args(argv)

    source = Path(args.source)
    names = [
        "ground_calib_24.png",
        "izba_24.png",
        "chapel_24.png",
        "gate_calib_24.png",
        "palisade_24.png",
        "dead_tree_24.png",
        "torch_24.png",
        "banner_24.png",
        "puddle_a_24.png",
        "puddle_b_24.png",
        "puddle_c_24.png",
        "forest_24.png",
        "glow_warm_24.png",
        "fog_a_24.png",
    ]
    entries = []
    for name in names:
        path = source / name
        if not path.is_file():
            continue
        image = Image.open(path).convert("RGBA")
        scaled = image.resize(
            (image.width * args.scale, image.height * args.scale), Image.NEAREST
        )
        entries.append((name, scaled))

    if not entries:
        print(f"FAIL: в {source} нет ассетов")
        return 1

    columns = args.columns
    padding = 16
    label_height = 18
    column_widths = [0] * columns
    row_heights: list[int] = []
    for index, (_name, image) in enumerate(entries):
        column = index % columns
        column_widths[column] = max(column_widths[column], image.width)
        if column == 0:
            row_heights.append(0)
        row_heights[-1] = max(row_heights[-1], image.height)

    width = sum(column_widths) + padding * (columns + 1)
    height = sum(row_heights) + (label_height + padding) * len(row_heights) + padding
    sheet = Image.new("RGBA", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)

    y = padding
    for row, row_height in enumerate(row_heights):
        x = padding
        for column in range(columns):
            index = row * columns + column
            if index >= len(entries):
                break
            name, image = entries[index]
            sheet.alpha_composite(image, (x, y + label_height))
            draw.text((x, y + 3), f"{name}  {image.width // args.scale}x{image.height // args.scale}", fill=LABEL)
            x += column_widths[column] + padding
        y += row_height + label_height + padding

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"preview={out} size={sheet.size} assets={len(entries)} scale={args.scale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
