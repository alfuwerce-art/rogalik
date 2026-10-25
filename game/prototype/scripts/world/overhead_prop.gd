extends Sprite2D
## Пропс, перекрывающий героя (крона дерева, арка ворот).
##
## Пока герой находится под спрайтом, прозрачность плавно снижается до fade_alpha,
## чтобы силуэт и опасные зоны оставались читаемыми. Это техническая проверка
## требования «прозрачность объектов, перекрывающих героя» (PIXEL_ART_STYLE_GUIDE §2).

const GROUP := "overhead"

## Прозрачность, до которой уходит перекрывающий пропс.
@export var fade_alpha := 0.32
## Скорость перехода, единиц альфы в секунду.
@export var fade_speed := 7.0

var _player: Node2D
var _cover_rect := Rect2()
var _faded := false


func _ready() -> void:
	add_to_group(GROUP)
	if texture:
		_cover_rect = Rect2(-texture.get_size() * 0.5, texture.get_size())


func _resolve_player() -> Node2D:
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group("player")
	return _player


func _process(delta: float) -> void:
	var player := _resolve_player()
	if player == null:
		return
	var under := _cover_rect.has_point(to_local(player.global_position))
	var target := fade_alpha if under else 1.0
	if not is_equal_approx(modulate.a, target):
		modulate.a = move_toward(modulate.a, target, fade_speed * delta)
	if under != _faded:
		_faded = under
		print(
			"OVERHEAD_FADE prop=%s under=%s alpha=%.2f"
			% [name, str(under), modulate.a]
		)
