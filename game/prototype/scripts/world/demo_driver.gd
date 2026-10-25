extends Node
## Сценарий демонстрационного маршрута для клипа приёмки Этапа 2 (задача 2.4).
##
## Это инструмент записи, а не игровая механика: драйвер лишь задаёт направление
## уже существующему герою по таймеру. Никаких новых врагов, атак или систем он
## не создаёт. Используется только с флагом `--demo`.
##
## Маршрут повторяет требования приёмки:
##   1. движение героя по территории;
##   2. подход к воротам с юга;
##   3. проход под аркой;
##   4. прозрачность арки при перекрытии героя (пауза под аркой);
##   5. столкновение со столбом ворот;
##   6. работа камеры при перемещении.

const SEGMENTS := [
	{"name": "approach_from_south", "dir": Vector2(0.0, -1.0), "duration": 1.2},
	{"name": "under_arch_fade", "dir": Vector2(0.0, -1.0), "duration": 0.8},
	{"name": "post_collision", "dir": Vector2(1.0, 0.0), "duration": 0.9},
	{"name": "retreat_south", "dir": Vector2(0.0, 1.0), "duration": 1.2},
	{"name": "yard_strafe_west", "dir": Vector2(-1.0, 0.0), "duration": 1.3},
	{"name": "return_to_gate", "dir": Vector2(0.0, -1.0), "duration": 1.0},
]

var _player: Node2D
var _index := -1
var _time := 0.0
var _quit_when_done := true


func setup(player: Node2D, quit_when_done: bool = true) -> void:
	_player = player
	_quit_when_done = quit_when_done


func total_duration() -> float:
	var total := 0.0
	for segment in SEGMENTS:
		total += float(segment["duration"])
	return total


func _process(delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		return
	if _index < 0:
		_start_segment(0)
		return
	_time += delta
	var segment: Dictionary = SEGMENTS[_index]
	if _time < float(segment["duration"]):
		return
	if _index + 1 >= SEGMENTS.size():
		_player.call("set_scripted_dir", Vector2.ZERO)
		print(
			"DEMO_FINISHED segments=%d pos=%.1f,%.1f"
			% [SEGMENTS.size(), _player.global_position.x, _player.global_position.y]
		)
		set_process(false)
		if _quit_when_done:
			get_tree().quit()
		return
	_start_segment(_index + 1)


func _start_segment(index: int) -> void:
	_index = index
	_time = 0.0
	var segment: Dictionary = SEGMENTS[index]
	_player.call("set_scripted_dir", segment["dir"])
	print(
		"DEMO_SEGMENT index=%d name=%s dir=%.1f,%.1f pos=%.1f,%.1f"
		% [
			index,
			segment["name"],
			(segment["dir"] as Vector2).x,
			(segment["dir"] as Vector2).y,
			_player.global_position.x,
			_player.global_position.y,
		]
	)
