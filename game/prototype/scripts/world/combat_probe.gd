extends Node2D
## Временные маркеры предполагаемых боевых объектов (задача 2.2).
##
## Это геометрия, нарисованная по пиксельной сетке мира: НЕ враги, НЕ механика и
## НЕ финальный арт — `PROXY_TECHNICAL` (D8). Нужна только для того, чтобы на одном
## и том же наборе объектов сравнить, сколько боевого пространства видно в каждом
## кандидатном масштабе (D9).
##
## Маркеры:
##   ромб (багровый)   — 1.8 тайла: гипотетическая дистанция удара/замаха;
##   круг (янтарный)   — 4.5 тайла: гипотетический подход/перебежка;
##   крест (голубой)   — 7 тайлов: дальняя дистанция, проверка обзора.
## Кольца на тех же радиусах показывают, какие дистанции попадают в кадр.
##
## Важно: фигуры рисуются только осевыми прямоугольниками по 1 мировому пикселю,
## позиции округляются до целого пикселя. Векторные примитивы (draw_circle/draw_line
## по дробным координатам) рвут пиксельную сетку и ломают проверку
## tools/stage2_location/check_pixel_scale.py.

const RING_NEAR := 1.8
const RING_MID := 4.5
const RING_FAR := 7.0

const COLOR_MELEE := Color(0.86, 0.30, 0.32, 1.0)
const COLOR_APPROACH := Color(0.95, 0.66, 0.26, 1.0)
const COLOR_RANGED := Color(0.47, 0.74, 0.96, 1.0)
const COLOR_OUTLINE := Color(0.06, 0.07, 0.10, 1.0)

var tile_px := 24.0
## Заполняется в setup(): {"kind": String, "pos": Vector2i (целые мировые px от героя)}.
var markers: Array[Dictionary] = []


func setup(tile: float, hero_world_pos: Vector2) -> void:
	tile_px = tile
	global_position = hero_world_pos.round()
	markers.clear()
	for direction in [Vector2.UP, Vector2.RIGHT, Vector2.DOWN, Vector2.LEFT]:
		markers.append({"kind": "melee", "pos": (direction * RING_NEAR * tile_px).round()})
	for direction in [Vector2.UP, Vector2.DOWN]:
		markers.append({"kind": "approach", "pos": (direction * RING_MID * tile_px).round()})
	markers.append({"kind": "ranged", "pos": (Vector2.RIGHT * RING_FAR * tile_px).round()})
	queue_redraw()


func marker_world_positions() -> Array[Vector2]:
	var result: Array[Vector2] = []
	for marker in markers:
		result.append(global_position + (marker["pos"] as Vector2))
	return result


func radius_of(kind: String) -> int:
	match kind:
		"melee":
			return maxi(2, int(round(tile_px * 0.34)))
		"approach":
			return maxi(2, int(round(tile_px * 0.30)))
		_:
			return maxi(2, int(round(tile_px * 0.32)))


func _draw() -> void:
	_pixel_ring(roundi(RING_NEAR * tile_px), Color(COLOR_MELEE, 0.62), 0)
	_pixel_ring(roundi(RING_MID * tile_px), Color(COLOR_APPROACH, 0.48), 1)
	_pixel_ring(roundi(RING_FAR * tile_px), Color(COLOR_RANGED, 0.38), 2)
	for marker in markers:
		var center := Vector2i((marker["pos"] as Vector2).round())
		var radius := radius_of(marker["kind"])
		match marker["kind"]:
			"melee":
				_pixel_diamond(center, radius, COLOR_MELEE)
			"approach":
				_pixel_disc(center, radius, COLOR_APPROACH)
			"ranged":
				_pixel_cross(center, radius, COLOR_RANGED)


## Один мировой пиксель — осевой прямоугольник. Все координаты целые.
func _cell(x: int, y: int, color: Color) -> void:
	draw_rect(Rect2(Vector2(x, y), Vector2.ONE), color)


func _pixel_diamond(center: Vector2i, radius: int, color: Color) -> void:
	for dy in range(-radius, radius + 1):
		var half := radius - absi(dy)
		for dx in range(-half, half + 1):
			if absi(dx) == half or absi(dy) == radius:
				_cell(center.x + dx, center.y + dy, COLOR_OUTLINE)
			else:
				_cell(center.x + dx, center.y + dy, color)
	# Контур в 1 px вокруг ромба: соседние клетки по вертикали и горизонтали.
	for dy in range(-radius - 1, radius + 2):
		var half := radius - absi(dy) + 1
		if half < 0:
			continue
		_cell(center.x - half, center.y + dy, COLOR_OUTLINE)
		_cell(center.x + half, center.y + dy, COLOR_OUTLINE)


func _pixel_disc(center: Vector2i, radius: int, color: Color) -> void:
	for dy in range(-radius, radius + 1):
		var half := int(floor(sqrt(maxf(0.0, float(radius * radius - dy * dy)))))
		for dx in range(-half, half + 1):
			var edge := absi(dx) >= half - 1 or absi(dy) >= radius - 1
			_cell(center.x + dx, center.y + dy, COLOR_OUTLINE if edge else color)


func _pixel_cross(center: Vector2i, arm: int, color: Color) -> void:
	# Крест-«X» из одиночных мировых пикселей: остаётся пиксельно-кратным кадру.
	for offset in range(-arm, arm + 1):
		_cell(center.x + offset, center.y + offset, color)
		_cell(center.x + offset, center.y - offset, color)


## Пунктирное кольцо: только осевые пиксели, шаг пунктира задаётся `phase`.
func _pixel_ring(radius: int, color: Color, phase: int) -> void:
	for dy in range(-radius, radius + 1):
		var half := int(floor(sqrt(maxf(0.0, float(radius * radius - dy * dy)))))
		var angle := atan2(float(dy), float(maxi(1, half)))
		var dash := int(floor((angle + PI) / (TAU / 28.0))) + phase * 3
		if dash % 4 == 3:
			continue
		_cell(-half, dy, color)
		_cell(half, dy, color)
