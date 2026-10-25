extends CharacterBody2D
## Герой (Этап 3, задача 3.1): первый игровой силуэт 48 px, четыре направления, idle.
##
## Что делает скрипт:
##   * выбирает направление по доминирующей оси движения (4 направления, D16);
##   * проигрывает минимальный `idle` — два кадра дыхания на направление;
##   * при движении показывает базовый кадр текущего направления: полноценной
##     анимации `move` ещё нет, это следующая задача Этапа 3, и она сюда не
##     подмешивается;
##   * привязывает спрайт к целому пикселю мира, чтобы при целочисленном
##     масштабе камеры кадр не «дрожал»;
##   * `--auto=dx,dy` ведёт героя без клавиатуры, `--face=down|up|left|right`
##     задаёт стартовое направление для кадров проверки.
##
## Раскладку листа задаёт сцена (`location.gd`) через свойства
## `hero_directional` / `hero_directions` / `hero_frames_per_direction`:
## односторонние прокси профилей A и C работают по-старому, лист Этапа 3 —
## по направлениям. Кадр = направление * кадров_на_направление + кадр_idle.

const DIR_DOWN := 0
const DIR_UP := 1
const DIR_LEFT := 2
const DIR_RIGHT := 3
const DIR_NAMES := ["down", "up", "left", "right"]

@export var speed := 72.0
@export var anim_fps := 9.0
@export var idle_fps := 1.4

## Лист с направлениями (true) или односторонний прокси (false).
var hero_directional := false
var hero_directions := 4
var hero_frames_per_direction := 1

var _auto := Vector2.ZERO
var _scripted_dir := Vector2.ZERO
var _facing := DIR_DOWN
var _idle_index := 0
var _idle_time := 0.0
var _legacy_time := 0.0
var _legacy_frame := 0
var _legacy_flip := false
var _reported_idle_frame := -1
var _report_time := 0.0
var _start := Vector2.ZERO
var _blocked_reported := false

@onready var sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	add_to_group("player")
	_start = global_position
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--auto="):
			_auto = _parse_dir(arg.substr(7))
		elif arg.begins_with("--face="):
			var requested := arg.substr(7).strip_edges().to_lower()
			var index := DIR_NAMES.find(requested)
			if index >= 0:
				_facing = index
	_apply_frame()
	print(
		"PLAYER_READY pos=%.1f,%.1f auto=%s facing=%s speed=%.1f frame=%d"
		% [global_position.x, global_position.y, str(_auto), DIR_NAMES[_facing], speed, sprite.frame]
	)


func _parse_dir(text: String) -> Vector2:
	var parts := text.split(",")
	if parts.size() >= 2:
		return Vector2(float(parts[0]), float(parts[1]))
	return Vector2(float(parts[0]), 0.0)


## Направление от сценария записи клипа (`--demo`). Игровую логику не меняет:
## при ненулевом значении приоритет выше клавиш и `--auto`.
func set_scripted_dir(dir: Vector2) -> void:
	_scripted_dir = dir
	# Новый отрезок маршрута — новый отчёт о столкновении: иначе первое
	# столкновение «глушит» все следующие и столб ворот не будет виден в логе.
	_blocked_reported = false


## Направление по доминирующей оси. При равенстве осей (диагональ) направление
## не меняется — иначе на диагонали кадр мигает между двумя сторонами.
func _facing_for(direction: Vector2) -> int:
	if absf(direction.x) > absf(direction.y):
		return DIR_LEFT if direction.x < 0.0 else DIR_RIGHT
	if absf(direction.y) > absf(direction.x):
		return DIR_UP if direction.y < 0.0 else DIR_DOWN
	return _facing


func _apply_frame() -> void:
	if hero_directional:
		sprite.frame = _facing * maxi(1, hero_frames_per_direction) + _idle_index
	else:
		sprite.frame = _legacy_frame
	# Зеркалирование только для одностороннего прокси (поведение Этапа 2):
	# у листа Этапа 3 направления нарисованы отдельно, отражение не нужно.
	if hero_directional:
		sprite.flip_h = false
	else:
		sprite.flip_h = _legacy_flip


func _physics_process(delta: float) -> void:
	var direction := Vector2.ZERO
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		direction.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		direction.x += 1.0
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		direction.y -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		direction.y += 1.0
	if _auto != Vector2.ZERO:
		direction = _auto
	if _scripted_dir != Vector2.ZERO:
		direction = _scripted_dir

	var previous_facing := _facing
	if direction != Vector2.ZERO:
		_facing = _facing_for(direction)
		velocity = direction.normalized() * speed
		if hero_directional:
			# Полноценная анимация move — следующая задача; здесь показывается
			# базовый кадр направления, чтобы ориентация читалась.
			_idle_index = 0
		else:
			_legacy_time += delta
			_legacy_frame = int(_legacy_time * anim_fps) % maxi(1, sprite.hframes)
			if direction.x != 0.0:
				_legacy_flip = direction.x < 0.0
	else:
		velocity = Vector2.ZERO
		if hero_directional:
			_idle_time += delta
			_idle_index = int(_idle_time * idle_fps) % maxi(1, hero_frames_per_direction)
		else:
			_legacy_time = 0.0
			_legacy_frame = 0

	_apply_frame()

	if _facing != previous_facing:
		print(
			"HERO_FACING dir=%s frame=%d x=%.1f y=%.1f"
			% [DIR_NAMES[_facing], sprite.frame, global_position.x, global_position.y]
		)
	if hero_directional and _idle_index != _reported_idle_frame:
		_reported_idle_frame = _idle_index
		print("HERO_IDLE frame_index=%d frame=%d dir=%s" % [_idle_index, sprite.frame, DIR_NAMES[_facing]])

	move_and_slide()

	# Целочисленная привязка спрайта: камера тоже целочисленная, поэтому
	# каждый пиксель арта попадает в целое число экранных пикселей.
	sprite.position = global_position.round() - global_position

	if (
		(_auto != Vector2.ZERO or _scripted_dir != Vector2.ZERO)
		and not _blocked_reported
		and get_slide_collision_count() > 0
	):
		if absf(global_position.x - _start.x) + absf(global_position.y - _start.y) > 4.0:
			_blocked_reported = true
			var collision := get_slide_collision(0)
			var normal := collision.get_normal()
			var collider := collision.get_collider()
			var collider_name := "none"
			if collider != null and collider is Node:
				collider_name = (collider as Node).name
			print(
				"PLAYER_BLOCKED x=%.1f y=%.1f normal=(%.2f,%.2f) collider=%s"
				% [global_position.x, global_position.y, normal.x, normal.y, collider_name]
			)

	_report_time += delta
	if _report_time >= 1.0:
		_report_time = 0.0
		print(
			"PLAYER_POS x=%.1f y=%.1f frame=%d dir=%s"
			% [global_position.x, global_position.y, sprite.frame, DIR_NAMES[_facing]]
		)
