extends CharacterBody2D
## Герой технической локации Этапа 2 (PROXY_TECHNICAL спрайт, D8).
##
## Отличия от технической комнаты Этапа 1:
##   * скорость задаётся в тайлах в секунду и масштабируется под кандидатный тайл (D9);
##   * спрайт привязывается к целому пикселю мира, чтобы при целочисленном
##     масштабе камеры кадр не «дрожал» (проверяется покадрово на реальном запуске);
##   * `--auto=dx,dy` ведёт героя без клавиатуры (проверка коллизий и зоны ворот).

const FRAMES := 4

@export var speed := 72.0
@export var anim_fps := 9.0

var _auto := Vector2.ZERO
var _scripted_dir := Vector2.ZERO
var _anim_time := 0.0
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
	print("PLAYER_READY pos=%.1f,%.1f auto=%s speed=%.1f" % [global_position.x, global_position.y, str(_auto), speed])


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

	if direction != Vector2.ZERO:
		velocity = direction.normalized() * speed
		_anim_time += delta
		sprite.frame = int(_anim_time * anim_fps) % FRAMES
		sprite.flip_h = direction.x < 0.0
	else:
		velocity = Vector2.ZERO
		_anim_time = 0.0
		sprite.frame = 0

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
		print("PLAYER_POS x=%.1f y=%.1f frame=%d" % [global_position.x, global_position.y, sprite.frame])
