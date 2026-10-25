extends Node
## Screenshot autoload for automated runs.
##
##   godot --path game/prototype -- --shot=C:/tmp/shot.png --shot-frames=120
##
## Waits for real rendering, saves the window image, then quits. In headless mode
## the dummy renderer produces no image, so the caller must run a windowed process.

var _shot_path := ""
var _wait_frames := 120
var _frames := 0
var _done := false


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shot="):
			_shot_path = arg.substr(7)
		elif arg.begins_with("--shot-frames="):
			_wait_frames = int(arg.substr(14))
	if _shot_path.is_empty():
		set_process(false)
	else:
		print("CAPTURE_READY path=%s frames=%d" % [_shot_path, _wait_frames])


func _process(_delta: float) -> void:
	if _done:
		return
	_frames += 1
	if _frames < _wait_frames:
		return
	_done = true
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var error := image.save_png(_shot_path)
	print(
		"SHOT_SAVED path=%s err=%d size=%dx%d"
		% [_shot_path, error, image.get_width(), image.get_height()]
	)
	get_tree().quit()
