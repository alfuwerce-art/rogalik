"""Проверка «нет размытия и дрожания пикселей» на реальном кадре игры.

Идея: при целочисленном масштабе каждый пиксель арта обязан попасть в блок
N x N пикселей окна одного цвета, где N = zoom камеры * масштаб окна.
Если в кадре есть интерполяция (фильтрация текстуры, дробный zoom, дробное
смещение камеры или спрайта), блоки перестают быть одноцветными.

Дополнительно проверяется, что кадр не показывает фон вне карты
(земля покрывает двор без «дыр»).

    python tools/stage2_location/check_pixel_scale.py <png> --block 4 --expect-size 960x540
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

CLEAR_COLOR = (27, 34, 48)


def check(path: Path, block: int, expect_size: tuple[int, int] | None, exclude_bottom: int, tolerance: int) -> int:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    play_height = height - exclude_bottom
    print(
        f"file={path.name} size={width}x{height} block={block}x{block} tolerance={tolerance} "
        f"checked_height={play_height} (HUD исключён: {exclude_bottom} px)"
    )
    failures: list[str] = []

    if expect_size and (width, height) != expect_size:
        failures.append(f"размер кадра {width}x{height} != ожидаемого {expect_size[0]}x{expect_size[1]}")
    if width % block or play_height % block:
        failures.append(f"размер проверяемой области не кратен блоку {block}: {width}x{play_height}")

    pixels = image.load()
    total_blocks = 0
    mixed_blocks = 0
    worst = 0
    worst_at = (0, 0)
    samples: list[str] = []
    for by in range(0, play_height - block + 1, block):
        for bx in range(0, width - block + 1, block):
            total_blocks += 1
            first = pixels[bx, by]
            differing = 0
            for dy in range(block):
                for dx in range(block):
                    current = pixels[bx + dx, by + dy]
                    if max(
                        abs(current[0] - first[0]),
                        abs(current[1] - first[1]),
                        abs(current[2] - first[2]),
                        abs(current[3] - first[3]),
                    ) > tolerance:
                        differing += 1
            if differing:
                mixed_blocks += 1
                if differing > worst:
                    worst = differing
                    worst_at = (bx, by)
                if len(samples) < 6:
                    samples.append(f"({bx},{by}) differing={differing}")

    unique_colors = len(image.getcolors(maxcolors=1 << 24) or [])
    background = 0
    background_samples: list[str] = []
    for y in range(0, play_height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if (r, g, b) == CLEAR_COLOR:
                background += 1
                if len(background_samples) < 8:
                    background_samples.append("(%d,%d)=(%d,%d,%d,%d)" % (x, y, r, g, b, a))

    ratio = mixed_blocks / max(1, total_blocks)
    print(f"blocks_total={total_blocks} blocks_not_uniform={mixed_blocks} ratio={ratio:.6f} worst_block_differing_px={worst} at={worst_at}")
    print(f"unique_colors={unique_colors} clear_color_pixels_sampled={background}")
    if samples:
        print("mixed_block_samples=" + ", ".join(samples))
    if background_samples:
        print("clear_color_samples=" + ", ".join(background_samples))

    if mixed_blocks:
        failures.append(
            f"{mixed_blocks} блоков {block}x{block} различаются сильнее допуска {tolerance}: есть интерполяция или дробное смещение (худший блок {worst} px в {worst_at})"
        )
    if background:
        failures.append(f"в кадре виден фон вне карты: {background} пикселей цвета {CLEAR_COLOR}")

    if failures:
        for line in failures:
            print(f"FAIL: {line}")
        return 1
    print("PASS: пиксели арта кратны блоку кадра, фон вне карты не виден")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path)
    parser.add_argument("--block", type=int, default=2)
    parser.add_argument("--expect-size", default="960x540")
    parser.add_argument(
        "--exclude-bottom",
        type=int,
        default=0,
        help="высота в пикселях окна, исключаемая снизу (HUD рисуется в нативном разрешении и намеренно не пиксельно-кратен)",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=0,
        help="допустимое различие каналов внутри блока: 0 — строгая проверка без света, 8 — допускает мягкое свечение",
    )
    args = parser.parse_args(argv)
    expect = None
    if args.expect_size:
        w, h = args.expect_size.lower().split("x")
        expect = (int(w), int(h))
    if not args.png.exists():
        print(f"FAIL: файл не найден: {args.png}")
        return 1
    return check(args.png, args.block, expect, args.exclude_bottom, args.tolerance)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
