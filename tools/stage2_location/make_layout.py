"""Генератор ASCII-карты технической локации (Этап 2, задача 2.1).

Карта — кандидат, не канон (D10): прямоугольный двор с воротами на севере,
дорожкой, травой, грязью, деревянным настилом и деревьями. Скрипт гарантирует
одинаковую ширину всех строк и записывает результат в GDScript-константу.

    python tools/stage2_location/make_layout.py
"""

from __future__ import annotations

import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "game" / "prototype" / "scripts" / "world" / "location_layout.gd"

W, H = 40, 24
GATE_X = 18          # первый столбец проёма ворот
GATE_Y = 2           # первая строка арки ворот
YARD_X0, YARD_X1 = 3, 36
YARD_Y0, YARD_Y1 = 5, 22


def blank_grid() -> list[list[str]]:
    return [["#" for _ in range(W)] for _ in range(H)]


def stamp(grid, x0, y0, x1, y1, char) -> None:
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            grid[y][x] = char


def build() -> list[str]:
    rng = random.Random(20251025)
    grid = blank_grid()

    # Двор: земля с вариантами фактуры.
    for y in range(YARD_Y0, YARD_Y1 + 1):
        for x in range(YARD_X0, YARD_X1 + 1):
            grid[y][x] = "." if rng.random() < 0.78 else ","

    # Дорожка от ворот вниз и небольшая площадь перед воротами.
    stamp(grid, GATE_X, GATE_Y, GATE_X + 2, YARD_Y0 + 13, "=")
    stamp(grid, GATE_X - 5, 16, GATE_X + 7, 18, "=")

    # Трава у стен и вокруг деревьев.
    stamp(grid, YARD_X0, YARD_Y0, YARD_X0 + 8, YARD_Y0 + 4, "g")
    stamp(grid, YARD_X1 - 7, YARD_Y0, YARD_X1, YARD_Y0 + 1, "g")
    stamp(grid, YARD_X1 - 9, YARD_Y1 - 3, YARD_X1, YARD_Y1, "g")

    # Грязь: лужи у юго-западного угла.
    stamp(grid, YARD_X0, YARD_Y1 - 4, YARD_X0 + 5, YARD_Y1, "m")
    stamp(grid, YARD_X0 + 1, YARD_Y1 - 2, YARD_X0 + 3, YARD_Y1 - 1, "m")

    # Деревянный настил в восточной части двора.
    stamp(grid, YARD_X1 - 7, 11, YARD_X1 - 1, 15, "p")

    # Деревья (2x3 тайла, крона перекрывает героя). Два — по сторонам ворот,
    # чтобы кадр сравнения констант показывал арку, кроны и землю одновременно.
    for tx, ty in ((14, 7), (24, 7), (9, 19), (30, 20)):
        grid[ty][tx] = "T"
        grid[ty][tx + 1] = "g"
        grid[ty + 1][tx] = "g"
        grid[ty + 1][tx + 1] = "g"

    # Частокол по периметру двора с проёмом под воротами.
    for x in range(YARD_X0, YARD_X1 + 1):
        if not (GATE_X <= x <= GATE_X + 2):
            grid[YARD_Y0 - 1][x] = "f"
    for y in range(YARD_Y0, YARD_Y1 + 1):
        grid[y][YARD_X0 - 1] = "f"
        grid[y][YARD_X1 + 1] = "f"
    for x in range(YARD_X0 - 1, YARD_X1 + 2):
        grid[YARD_Y1 + 1][x] = "f"

    # Точка появления героя: у ворот, чтобы кадр сравнения показывал арку, деревья и двор.
    grid[17][GATE_X + 1] = "="
    grid[5][GATE_X + 1] = "@"
    return ["".join(row) for row in grid]


HEADER = '''## Карта технической локации Этапа 2 (кандидат, D10).
##
## Сгенерировано tools/stage2_location/make_layout.py — можно править руками,
## но после ручной правки ширины строк проверяются в location_layout.gd.
##
## Легенда:
##   '#' каменная стена (непроходимо)   'f' частокол (непроходимо)
##   '.' земля        ',' земля-вариант  '=' дорожка из плит
##   'g' трава        'm' грязь          'p' деревянный настил
##   'T' дерево (проходимая земля + пропс с коллизией у ствола)
##   '@' точка появления героя (дорожка)
##
## PROXY_TECHNICAL: раскладка нужна для проверки пиксельных констант, это не финальная локация.

class_name LocationLayout
extends RefCounted

const GATE_CELL := Vector2i(%d, %d)
const GATE_SIZE_CELLS := Vector2i(3, 2)

const ROWS: PackedStringArray = [
%s
]


static func width() -> int:
	return ROWS[0].length()


static func height() -> int:
	return ROWS.size()


static func char_at(cell: Vector2i) -> String:
	if cell.y < 0 or cell.y >= ROWS.size():
		return "#"
	var row: String = ROWS[cell.y]
	if cell.x < 0 or cell.x >= row.length():
		return "#"
	return row[cell.x]


static func find_spawn() -> Vector2i:
	for y in ROWS.size():
		var column := ROWS[y].find("@")
		if column >= 0:
			return Vector2i(column, y)
	return Vector2i(1, 1)


static func tree_cells() -> Array[Vector2i]:
	var result: Array[Vector2i] = []
	for y in ROWS.size():
		var row: String = ROWS[y]
		for x in row.length():
			if row[x] == "T":
				result.append(Vector2i(x, y))
	return result
'''


def main() -> None:
    rows = build()
    widths = {len(r) for r in rows}
    assert widths == {W}, widths
    body = ",\n".join(f'\t"{r}"' for r in rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER % (GATE_X, GATE_Y, body), encoding="utf-8")
    print(f"layout -> {OUT.relative_to(ROOT)} ({W}x{H}, widths={sorted(widths)})")
    for index, r in enumerate(rows):
        print(f"{index:2d} {r}")


if __name__ == "__main__":
    main()
