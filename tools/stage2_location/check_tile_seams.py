"""Проверка шва тайлов земли в модульном тайлсете (Этап 2, задача 2.1).

Критерий: у тайлов земли крайний пиксель каждой стороны одноцветный и совпадает
у вариантов одного материала. Тогда соседние тайлы одного материала стыкуются
без видимой границы и земля не читается как «шахматная доска» из тайлов.
Стены, частокол и столбы проверяются отдельно: у объектов край намеренно контрастный.

    python tools/stage2_location/check_tile_seams.py <tileset.png> --tile 16
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

# Индексы тайлов должны совпадать с make_proxies.py.
GROUND_TILES = {
    0: "земля A",
    1: "земля B",
    3: "трава",
    4: "грязь",
}
# Материалы со структурным рисунком: линия на границе тайла — часть рисунка
# (затирка плит, стык досок), поэтому для них критерий информационный.
STRUCTURED_TILES = {2: "дорожка", 5: "настил"}
OBJECT_TILES = {6: "стена A", 7: "стена B", 8: "частокол", 9: "столб", 10: "камень", 11: "пустота"}


def sides(img: Image.Image, ox: int, oy: int, tile: int) -> dict[str, list[tuple]]:
    px = img.load()
    return {
        "left": [px[ox, oy + y] for y in range(tile)],
        "right": [px[ox + tile - 1, oy + y] for y in range(tile)],
        "top": [px[ox + x, oy] for x in range(tile)],
        "bottom": [px[ox + x, oy + tile - 1] for x in range(tile)],
    }


def uniform(pixels: list[tuple]) -> bool:
    return all(p == pixels[0] for p in pixels)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path)
    parser.add_argument("--tile", type=int, required=True)
    parser.add_argument("--columns", type=int, default=4)
    args = parser.parse_args(argv)
    if not args.png.exists():
        print(f"FAIL: файл не найден: {args.png}")
        return 1

    img = Image.open(args.png).convert("RGBA")
    tile = args.tile
    failures: list[str] = []
    borders: dict[int, dict[str, tuple]] = {}
    for index, name in GROUND_TILES.items():
        ox = (index % args.columns) * tile
        oy = (index // args.columns) * tile
        tilesides = sides(img, ox, oy, tile)
        for side, pixels in tilesides.items():
            if not uniform(pixels):
                failures.append(f"тайл {index} ({name}), сторона {side}: край не одноцветный")
                continue
            borders.setdefault(index, {})[side] = pixels[0]
        print(
            "tile %2d %-9s left=%s right=%s top=%s bottom=%s"
            % (
                index,
                name,
                tilesides["left"][0][:3],
                tilesides["right"][0][:3],
                tilesides["top"][0][:3],
                tilesides["bottom"][0][:3],
            )
        )

    # Варианты земли A и B обязаны иметь одинаковые края: иначе соседние тайлы
    # одного материала дают видимую границу.
    if 0 in borders and 1 in borders:
        for side in ("left", "right", "top", "bottom"):
            if borders[0].get(side) != borders[1].get(side):
                failures.append(
                    f"земля A и земля B различаются по краю {side}: {borders[0].get(side)} != {borders[1].get(side)}"
                )

    print(f"объектные тайлы (контрастный край ожидаем): {', '.join(OBJECT_TILES[k] for k in OBJECT_TILES)}")
    for index, name in STRUCTURED_TILES.items():
        ox = (index % args.columns) * tile
        oy = (index // args.columns) * tile
        tilesides = sides(img, ox, oy, tile)
        print(
            "tile %2d %-8s (структурный рисунок) left_uniform=%s right_uniform=%s top_uniform=%s bottom_uniform=%s"
            % (index, name, uniform(tilesides["left"]), uniform(tilesides["right"]), uniform(tilesides["top"]), uniform(tilesides["bottom"]))
        )
    if failures:
        for line in failures:
            print(f"FAIL: {line}")
        return 1
    print("PASS: края тайлов земли одноцветны и согласованы между вариантами")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
