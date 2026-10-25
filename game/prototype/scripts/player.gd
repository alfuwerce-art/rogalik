extends CharacterBody2D
## Prototype controller: polls keys directly so the project needs no InputMap.
## `--auto=<dir>` drives the character without a keyboard, which lets a headless
## test prove that the obstacle actually blocks movement.

const SPEED := 90.0
const FRAMES := 4
const ANIM_FPS := 8.0

@onready var sprite: Sprite2D = $Sprite2D

var _anim_time := 0.0
var _auto_dir := 0.0
var _report_time := 0.0
var _start_position := Vector2.ZERO
var _blocked_reported := false


func _ready() -> void:
	_start_position = position
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--auto="):
			_auto_dir = float(arg.substr(7))
	print("PLAYER_READY pos=%.1f,%.1f auto=%.1f" % [position.x, position.y, _auto_dir])


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
	if _auto_dir != 0.0:
		direction.x = _auto_dir

	if direction != Vector2.ZERO:
		velocity = direction.normalized() * SPEED
		_anim_time += delta
		sprite.frame = int(_anim_time * ANIM_FPS) % FRAMES
		sprite.flip_h = direction.x < 0.0
	else:
		velocity = Vector2.ZERO
		sprite.frame = 0

	move_and_slide()

	if _auto_dir != 0.0 and is_on_wall() and not _blocked_reported:
		if absf(position.x - _start_position.x) > 8.0:
			_blocked_reported = true
			print("PLAYER_BLOCKED x=%.1f y=%.1f" % [position.x, position.y])

	_report_time += delta
	if _report_time >= 1.0:
		_report_time = 0.0
		print("PLAYER_POS x=%.1f y=%.1f frame=%d" % [position.x, position.y, sprite.frame])
