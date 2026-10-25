## Карта технической локации Этапа 2 (кандидат, D10).
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

const GATE_CELL := Vector2i(18, 2)
const GATE_SIZE_CELLS := Vector2i(3, 2)

const ROWS: PackedStringArray = [
	"########################################",
	"########################################",
	"##################===###################",
	"##################===###################",
	"###fffffffffffffff===ffffffffffffffff###",
	"##fggggggggg.,.,..=@=.,......ggggggggf##",
	"##fggggggggg..,...===,.....,.ggggggggf##",
	"##fggggggggg.,Tg.,===.,.Tg.......,,..f##",
	"##fggggggggg..gg.,===..,gg..........,f##",
	"##fggggggggg,.....===.........,...,,.f##",
	"##f........,..,..,===..,........,....f##",
	"##f.........,,....===,....,..ppppppp,f##",
	"##f...,,,.,......,===........ppppppp.f##",
	"##f.,,,....,,.....===..,,.,..ppppppp.f##",
	"##f...,.....,....,===..,,...,ppppppp.f##",
	"##f.,.,....,.,,..,===..,.....ppppppp,f##",
	"##f,.,..,..,.=============..,,.......f##",
	"##f..,..,.,,.=============........,..f##",
	"##fmmmmmm....=============.,.,..,,..,f##",
	"##fmmmmmmTg..,.,..........,ggggggggggf##",
	"##fmmmmmmgg.....,..,.......gggTggggggf##",
	"##fmmmmmm............,....,ggggggggggf##",
	"##fmmmmmm,.....,...,...,.,.ggggggggggf##",
	"##ffffffffffffffffffffffffffffffffffff##"
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
