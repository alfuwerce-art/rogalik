extends Camera2D
## Игровая камера каркаса локации.
##
## Камера держится за героем, ограничена границами карты и привязывается к целому
## пикселю мира: при целочисленном масштабе (zoom 1 или 2 и окно x2) пиксели арта
## не интерполируются, поэтому нет размытия и дрожания.

var target: Node2D

## Смещение кадра вперёд по направлению движения: у top-down боя полезнее видеть
## больше пространства перед героем. Значение задаётся профилем (в пикселях мира).
@export var lookahead := Vector2.ZERO

## Дробная часть половины кадра (0 или 0.5): компенсирует то, что половина видимой
## высоты в мировых пикселях может быть дробной (270 / 2 / 2 = 67.5). Без этой
## компенсации сетка арта ложится на пол-пикселя относительно сетки экрана.
@export var grid_offset := Vector2.ZERO

var _warned := false


func _ready() -> void:
	position_smoothing_enabled = false
	rotation_smoothing_enabled = false
	ignore_rotation = true


func _process(_delta: float) -> void:
	if target == null or not is_instance_valid(target):
		target = get_tree().get_first_node_in_group("player")
		if target == null:
			if not _warned:
				_warned = true
				print("CAMERA_WAIT player not found yet")
			return
	# Целая позиция камеры + дробная компенсация: при ограничении границами карты
	# края кадра остаются на целой мировой координате, поэтому фаза не сбивается.
	global_position = (target.global_position + lookahead).round() + grid_offset
