"""Превью листа героя для визуального контроля (не игровой ассет).

Увеличивает кадры целым коэффициентом с nearest-фильтром и подписывает
направления, чтобы сравнение четырёх видов не зависело от «взгляда на глаз».
Текст подписи рисуется обычным шрифтом PIL: это отчётный артефакт, а не арт игры.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DIRECTIONS = ("down", "up", "left", "right")


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet", help="лист 128x96 (4 направления x 2 кадра)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scale", type=int, default=6)
    parser.add_argument("--background", default="#20242c")
    args = parser.parse_args(argv)

    sheet = Image.open(args.sheet).convert("RGBA")
    frame_w, frame_h = sheet.width // len(DIRECTIONS), sheet.height // 2
    scale = args.scale

    pad = 12
    label_h = 22
    cell_w, cell_h = frame_w * scale, frame_h * scale
    width = pad + len(DIRECTIONS) * (cell_w + pad)
    height = pad + cell_h + label_h + pad
    canvas = Image.new("RGB", (width, height), args.background)
    draw = ImageDraw.Draw(canvas)
    font = load_font(14)

    for column, name in enumerate(DIRECTIONS):
        frame = sheet.crop((column * frame_w, 0, (column + 1) * frame_w, frame_h))
        frame = frame.resize((cell_w, cell_h), Image.NEAREST)
        x = pad + column * (cell_w + pad)
        y = pad
        # Шахматка под прозрачностью: видно, что фон кадра реально прозрачный.
        for cy in range(0, cell_h, 16):
            for cx in range(0, cell_w, 16):
                if ((cx // 16) + (cy // 16)) % 2 == 0:
                    canvas.paste("#2a2f38", (x + cx, y + cy, x + min(cx + 16, cell_w), y + min(cy + 16, cell_h)))
        canvas.paste(frame, (x, y), frame)
        draw.text((x + 4, y + cell_h + 4), f"{name}  {frame_w}x{frame_h}", fill="#c6c1b5", font=font)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    print(f"PREVIEW {args.out} {width}x{height} scale={scale}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
