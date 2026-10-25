extends Node2D
## Каркас технической локации Этапа 2 (задача 2.1).
##
## Что делает сцена:
##   * собирает TileSet из PNG-атласа кандидатной сетки и раскладывает карту
##     по слоям земля → детали пола → препятствия → персонажи → верхние части
##     → атмосфера (PIXEL_ART_STYLE_GUIDE §7);
##   * ставит камеру с кандидатными константами и целочисленной привязкой;
##   * добавляет техническую зону-«ворота» (greybox + пропс с коллизией столбов);
##   * включает базовый свет: холодная тонировка CanvasModulate и тёплые
##     точечные источники на столбах ворот;
##   * печатает измеряемые величины (профиль, тайлсет, карта, FPS) в stdout,
##     чтобы проверка не зависела от визуальной оценки.
##
## Запуск:
##   godot --path game/prototype -- --profile=a|b|c
##   godot --path game/prototype -- --profile=b --auto=0,-1 --quit-after 300
##   godot --path game/prototype -- --profile=b --bench
##   godot --path game/prototype -- --profile=b --probe     (сравнение боевого пространства, задача 2.2)

const PLAYER_SCRIPT := "res://scripts/world/player_world.gd"
const OVERHEAD_SCRIPT := "res://scripts/world/overhead_prop.gd"
const PROBE_SCRIPT := "res://scripts/world/combat_probe.gd"
const LIGHT_TEXTURE := "res://art/lights/light_soft.png"

## Точка героя в режиме пробы: середина двора, вокруг есть препятствия (забор, деревья,
## ворота) на расстоянии 3–7 тайлов — так масштабы сравниваются на одном и том же месте.
const PROBE_CELL := Vector2i(19, 9)

## Холодная ночная тонировка: множитель CanvasModulate (ориентиры палитры #1B2230/#39424C).
const NIGHT_TINT := Color(0.80, 0.84, 0.94, 1.0)
## Тёплый свет на столбах ворот.
const TORCH_COLOR := Color(1.0, 0.78, 0.52, 1.0)

@onready var ground: TileMapLayer = $Layers/Ground
@onready var details: TileMapLayer = $Layers/FloorDetails
@onready var collision_root: Node2D = $Layers/Collision
@onready var obstacles: TileMapLayer = $Layers/Obstacles
@onready var overhead: Node2D = $Layers/Overhead
@onready var entities: Node2D = $Layers/Entities
@onready var atmosphere: Node2D = $Layers/Atmosphere
@onready var night_tint: CanvasModulate = $Layers/Atmosphere/NightTint
@onready var camera: Camera2D = $Layers/Entities/CameraRig
@onready var hud_info: Label = $HUD/Info
@onready var hud_backdrop: ColorRect = $HUD/Backdrop

var _profile: Dictionary = {}
var _tile_px := 16
var _player: CharacterBody2D
var _bench := false
var _stats := false
var _no_lights := false
var _probe := false
var _probe_node: Node2D
var _probe_reported := false
var _frames := 0
var _fps_timer := 0.0
var _bench_timer := 0.0
var _stats_frames := 0
var _stats_time := 0.0
var _stats_max := 0.0
var _stats_wall_start := 0


func _ready() -> void:
	var requested := PixelProfiles.DEFAULT_ID
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--profile="):
			requested = arg.substr(10).strip_edges().to_lower()
		elif arg == "--bench":
			_bench = true
		elif arg == "--stats":
			_stats = true
		elif arg == "--no-lights":
			_no_lights = true
		elif arg == "--probe" or arg.begins_with("--probe="):
			_probe = true
	_profile = PixelProfiles.get_profile(requested)
	_tile_px = int(_profile["tile_px"])
	print(PixelProfiles.describe(_profile))

	_build_layers()
	_spawn_player()
	_spawn_props()
	_spawn_gate_zone()
	if _probe:
		_place_probe()
	_setup_camera()
	_setup_atmosphere()
	_setup_hud()

	if _bench:
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
		print("BENCH_START vsync=disabled")
	print(
		"RENDERER adapter=%s api=%s driver=%s"
		% [
			RenderingServer.get_video_adapter_name(),
			RenderingServer.get_video_adapter_api_version(),
			ProjectSettings.get_setting("rendering/renderer/rendering_method", "unknown"),
		]
	)
	print(
		"LOCATION_READY profile=%s map=%dx%d tile_px=%d props=%d cells=%d"
		% [
			_profile["id"],
			LocationLayout.width(),
			LocationLayout.height(),
			_tile_px,
			overhead.get_child_count(),
			ground.get_used_cells().size() + details.get_used_cells().size() + obstacles.get_used_cells().size(),
		]
	)


var _hud_frames := 0
var _hud_time := 0.0
var _hud_fps := 0


# --- слои и тайлмапы ---------------------------------------------------------


func _build_layers() -> void:
	var sheet: Texture2D = load(_profile["tileset"])
	if sheet == null:
		push_error("Не найден тайлсет %s" % _profile["tileset"])
		return
	var tile_set := TilesetFactory.build(sheet, _tile_px)
	for layer in [ground, details, obstacles]:
		layer.tile_set = tile_set
		layer.collision_enabled = true

	var walls := 0
	var fences := 0
	var paths := 0
	for y in LocationLayout.height():
		for x in LocationLayout.width():
			var cell := Vector2i(x, y)
			var ch := LocationLayout.char_at(cell)
			var base := TilesetFactory.base_tile(ch, cell)
			ground.set_cell(cell, TilesetFactory.SOURCE_ID, TilesetFactory.atlas_coord(base))
			var detail := TilesetFactory.detail_tile(ch)
			if detail >= 0:
				details.set_cell(cell, TilesetFactory.SOURCE_ID, TilesetFactory.atlas_coord(detail))
				paths += 1
			var obstacle := TilesetFactory.obstacle_tile(ch, cell)
			if obstacle >= 0:
				obstacles.set_cell(cell, TilesetFactory.SOURCE_ID, TilesetFactory.atlas_coord(obstacle))
				if ch == "#":
					walls += 1
				else:
					fences += 1
	print(
		"TILESET_READY sheet=%s tile_px=%d tiles=%d solid=%d walls=%d fences=%d path_tiles=%d"
		% [
			_profile["tileset"],
			_tile_px,
			TilesetFactory.TILE_COUNT,
			TilesetFactory.SOLID_TILES.size(),
			walls,
			fences,
			paths,
		]
	)


# --- герой -------------------------------------------------------------------


func _spawn_player() -> void:
	var tile := float(_tile_px)
	var spawn_cell := LocationLayout.find_spawn()
	_player = CharacterBody2D.new()
	_player.name = "Player"
	_player.set_script(load(PLAYER_SCRIPT))
	_player.position = Vector2(spawn_cell) * tile + Vector2(tile * 0.5, tile * 0.5)
	_player.collision_layer = 2
	_player.collision_mask = 1
	_player.z_index = 1
	_player.set("speed", tile * 3.2)

	var sprite := Sprite2D.new()
	sprite.name = "Sprite2D"
	sprite.texture = load(_profile["hero_sheet"])
	sprite.hframes = PixelProfiles.HERO_FRAMES
	sprite.vframes = 1
	sprite.centered = true
	# Ноги героя на точке появления: спрайт поднят на половину своей высоты.
	sprite.offset = Vector2(0.0, -float(_profile["hero_height_px"]) * 0.5)
	_player.add_child(sprite)

	var body := CollisionShape2D.new()
	body.name = "CollisionShape2D"
	var shape := RectangleShape2D.new()
	shape.size = Vector2(tile * 0.5, tile * 0.4)
	body.shape = shape
	body.position = Vector2(0.0, -shape.size.y * 0.5)
	_player.add_child(body)

	entities.add_child(_player)
	print(
		"PLAYER_SPAWN cell=%s pos=%.1f,%.1f hero_px=%d"
		% [str(spawn_cell), _player.position.x, _player.position.y, _profile["hero_height_px"]]
	)


# --- пропсы и зона ворот -----------------------------------------------------


func _spawn_props() -> void:
	var tile := float(_tile_px)
	var gate_texture: Texture2D = load(_profile["gate"])
	var gate := Sprite2D.new()
	gate.name = "Gate"
	gate.texture = gate_texture
	gate.centered = true
	gate.position = (
		Vector2(LocationLayout.GATE_CELL) * tile
		+ Vector2(LocationLayout.GATE_SIZE_CELLS) * tile * 0.5
	)
	gate.z_index = 2
	gate.set_script(load(OVERHEAD_SCRIPT))
	overhead.add_child(gate)

	# Коллизия столбов ворот: art рисует столбы шириной 0.75 тайла по краям.
	var post_w := tile * 0.75
	var gate_h := tile * float(LocationLayout.GATE_SIZE_CELLS.y)
	var gate_left := Vector2(LocationLayout.GATE_CELL) * tile
	_add_static_rect(Vector2(gate_left.x + post_w * 0.5, gate_left.y + gate_h * 0.5), Vector2(post_w, gate_h))
	_add_static_rect(
		Vector2(gate_left.x + tile * float(LocationLayout.GATE_SIZE_CELLS.x) - post_w * 0.5, gate_left.y + gate_h * 0.5),
		Vector2(post_w, gate_h)
	)

	var tree_texture: Texture2D = load(_profile["tree"])
	for cell in LocationLayout.tree_cells():
		var tree := Sprite2D.new()
		tree.name = "Tree_%d_%d" % [cell.x, cell.y]
		tree.texture = tree_texture
		tree.centered = true
		tree.position = Vector2(cell.x + 1.0, cell.y + 1.0) * tile
		tree.z_index = 2
		tree.set_script(load(OVERHEAD_SCRIPT))
		overhead.add_child(tree)
		# Ствол перекрывает перемещение, крона — нет.
		_add_static_rect(
			Vector2(cell.x + 1.0, cell.y + 0.62) * tile,
			Vector2(tile * 0.7, tile * 0.6)
		)
	print("PROPS_READY gate=1 trees=%d" % LocationLayout.tree_cells().size())


func _spawn_gate_zone() -> void:
	var tile := float(_tile_px)
	var area := Area2D.new()
	area.name = "GateZone"
	area.collision_layer = 4
	area.collision_mask = 2
	area.monitoring = true
	var zone_shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(tile * LocationLayout.GATE_SIZE_CELLS.x, tile * 2.0)
	zone_shape.shape = rect
	area.add_child(zone_shape)
	area.position = (
		Vector2(LocationLayout.GATE_CELL) * tile
		+ Vector2(LocationLayout.GATE_SIZE_CELLS.x * 0.5, 2.6) * tile
	)
	area.body_entered.connect(_on_gate_zone_body_entered)
	collision_root.add_child(area)


func _on_gate_zone_body_entered(body: Node2D) -> void:
	print("GATE_ENTERED body=%s x=%.1f y=%.1f" % [body.name, body.global_position.x, body.global_position.y])


func _add_static_rect(center: Vector2, size: Vector2) -> void:
	var body := StaticBody2D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = size
	shape.shape = rect
	body.add_child(shape)
	body.position = center
	collision_root.add_child(body)


# --- камера, свет, HUD ------------------------------------------------------


func _setup_camera() -> void:
	var zoom: float = _profile["camera_zoom"]
	var tile := float(_tile_px)
	camera.zoom = Vector2(zoom, zoom)
	camera.position_smoothing_enabled = false
	camera.limit_left = 0
	camera.limit_top = 0
	camera.limit_right = LocationLayout.width() * _tile_px
	camera.limit_bottom = LocationLayout.height() * _tile_px
	camera.limit_smoothed = false
	camera.offset = Vector2.ZERO
	camera.set("grid_offset", Vector2(_grid_offset(zoom, true), _grid_offset(zoom, false)))
	camera.global_position = _player.global_position.round()
	camera.set("target", _player)
	# Кадр смещён на один тайл вверх: в кадре видно арку ворот, а не только землю под героем.
	camera.set("lookahead", Vector2(0.0, -tile))
	camera.make_current()
	print(
		"CAMERA_READY zoom=%.1f limits=%d,%d,%d,%d"
		% [
			zoom,
			camera.limit_left,
			camera.limit_top,
			camera.limit_right,
			camera.limit_bottom,
		]
	)


## Половина видимого кадра в мировых пикселях может оказаться дробной
## (при viewport 270 и zoom 2 это 67.5). Тогда сетка арта смещается на пол-пикселя
## относительно сетки экрана, и пиксели перестают укладываться в целые блоки
## N x N (проверено tools/stage2_location/check_pixel_scale.py). Дробная часть
## компенсируется в позиции камеры — её видно на краях кадра, но не в ограничениях.
func _grid_offset(zoom: float, horizontal: bool) -> float:
	var view := 480.0 if horizontal else 270.0
	var half_world := view / (2.0 * zoom)
	return half_world - floorf(half_world)


func _setup_atmosphere() -> void:
	night_tint.color = NIGHT_TINT
	if _no_lights:
		print("ATMOSPHERE_READY tint=%s lights=0 (диагностический режим --no-lights)" % str(NIGHT_TINT))
		return
	var light_texture: Texture2D = load(LIGHT_TEXTURE)
	var tile := float(_tile_px)
	# Диаметр света 8 тайлов; texture_scale целый, поэтому свет тоже не мылит пиксели.
	var light_scale := tile * 8.0 / float(light_texture.get_width())
	var gate_center := (
		Vector2(LocationLayout.GATE_CELL) * tile
		+ Vector2(LocationLayout.GATE_SIZE_CELLS) * tile * 0.5
	)
	for side in [-1.0, 1.0]:
		var torch := PointLight2D.new()
		torch.name = "Torch_%s" % ("left" if side < 0.0 else "right")
		torch.texture = light_texture
		torch.texture_scale = light_scale
		torch.color = TORCH_COLOR
		torch.energy = 1.15
		torch.blend_mode = Light2D.BLEND_MODE_ADD
		# Пиксельный свет: ближайший фильтр, чтобы градиент не мылил пиксели арта.
		torch.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		# Позиция света выравнивается по сетке его текстуры (кратна texture_scale):
		# иначе дизеринг свечения попадает на дробное смещение и рвёт блоки пикселей.
		torch.position = (
			((gate_center + Vector2(side * tile * 1.2, tile * 0.15)) / light_scale).round() * light_scale
		)
		atmosphere.add_child(torch)
	print("ATMOSPHERE_READY tint=%s lights=2 light_scale=%.1f" % [str(NIGHT_TINT), light_scale])


## Режим пробы боевого пространства (задача 2.2): герой ставится в середину двора,
## вокруг рисуются маркеры предполагаемых боевых объектов. Маркеры — `PROXY_TECHNICAL`,
## это не враги и не механика, они не влияют на коллизии и бой.
func _place_probe() -> void:
	var tile := float(_tile_px)
	_player.global_position = Vector2(PROBE_CELL) * tile + Vector2(tile, tile) * 0.5
	_probe_node = Node2D.new()
	_probe_node.name = "CombatProbe"
	_probe_node.z_index = 3
	_probe_node.set_script(load(PROBE_SCRIPT))
	entities.add_child(_probe_node)
	_probe_node.call("setup", tile, _player.global_position)
	print(
		"PROBE_READY cell=%s hero=%.1f,%.1f markers=%d rings=3 status=PROXY_TECHNICAL"
		% [str(PROBE_CELL), _player.global_position.x, _player.global_position.y, 7]
	)


## Считает, какие маркеры и кольца реально попали в кадр — это объективная мера
## «сколько боевого пространства видно» для сравнения A/B/C.
func _report_probe_visibility() -> void:
	if _probe_node == null:
		return
	var view_size := get_viewport().get_visible_rect().size
	var view_rect := Rect2(Vector2.ZERO, view_size)
	# Игровое поле без HUD: маркер под панелью формально в кадре, но глазу недоступен.
	var play_rect := view_rect
	if hud_backdrop != null:
		play_rect.size.y = maxf(0.0, hud_backdrop.position.y)
	var xform := get_viewport().get_canvas_transform()
	var positions: Array[Vector2] = _probe_node.call("marker_world_positions")
	var visible_markers := 0
	var unobstructed := 0
	var farthest_visible := 0.0
	var details: Array[String] = []
	for index in positions.size():
		var screen: Vector2 = xform * positions[index]
		var inside := view_rect.has_point(screen)
		if inside:
			visible_markers += 1
			farthest_visible = maxf(farthest_visible, positions[index].distance_to(_player.global_position))
		if inside and play_rect.has_point(screen):
			unobstructed += 1
		details.append(
			"%d:%s(%.0f,%.0f)"
			% [index, "in" if inside else "out", screen.x, screen.y]
		)
	var world_visible := view_size / float(_profile["camera_zoom"])
	var visible_tiles := world_visible / float(_tile_px)
	print(
		"PROBE_VISIBLE profile=%s markers_in_view=%d/%d markers_unobstructed=%d/%d play_h=%.0f farthest_visible_px=%.0f world_visible=%.0fx%.0f tiles_visible=%.2fx%.2f hero_screen_px=%d probe_cell=%s %s"
		% [
			_profile["id"],
			visible_markers,
			positions.size(),
			unobstructed,
			positions.size(),
			play_rect.size.y,
			farthest_visible,
			world_visible.x,
			world_visible.y,
			visible_tiles.x,
			visible_tiles.y,
			int(_profile["hero_height_px"] * PixelProfiles.screen_px_per_art_px(_profile)),
			str(PROBE_CELL),
			" ".join(details),
		]
	)


func _setup_hud() -> void:
	if _probe:
		# В режиме пробы HUD выше: нужна легенда маркеров (текст в мировых координатах
		# не рисуется, чтобы не ломать пиксельную проверку кадра).
		hud_backdrop.position = Vector2(6.0, 198.0)
		hud_backdrop.size = Vector2(468.0, 68.0)
		hud_info.position = Vector2(10.0, 200.0)
		hud_info.size = Vector2(460.0, 64.0)
	hud_info.text = PixelProfiles.hud_text(_profile, 0, _probe)


func _process(delta: float) -> void:
	_frames += 1
	if _probe and not _probe_reported and _frames >= 4:
		_probe_reported = true
		_report_probe_visibility()
	# FPS считается по фактическим дельтам кадра: Engine.get_frames_per_second()
	# сразу после запуска показывает значение, усреднённое вместе со стартовым
	# хичкем, из-за чего первый кадр сравнения мог показывать «2 FPS».
	_hud_frames += 1
	_hud_time += delta
	if _hud_time >= 0.5:
		_hud_fps = int(round(float(_hud_frames) / _hud_time))
		_hud_frames = 0
		_hud_time = 0.0
		hud_info.text = PixelProfiles.hud_text(_profile, _hud_fps, _probe)
	if _stats:
		if _stats_wall_start == 0:
			_stats_wall_start = Time.get_ticks_msec()
		_stats_frames += 1
		_stats_time += delta
		_stats_max = maxf(_stats_max, delta)
		if _stats_time >= 1.0:
			var wall := (Time.get_ticks_msec() - _stats_wall_start) / 1000.0
			print(
				"STATS frames=%d window_s=%.2f avg_frame_ms=%.1f max_frame_ms=%.1f frames_per_s=%.1f engine_fps=%d draw_calls=%d objects=%d"
				% [
					_stats_frames,
					wall,
					_stats_time / float(_stats_frames) * 1000.0,
					_stats_max * 1000.0,
					float(_stats_frames) / maxf(wall, 0.001),
					Engine.get_frames_per_second(),
					RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
					RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
				]
			)
			_stats_frames = 0
			_stats_time = 0.0
			_stats_max = 0.0
			_stats_wall_start = Time.get_ticks_msec()
	if _bench:
		_bench_timer += delta
		if _bench_timer >= 1.0:
			_bench_timer = 0.0
			print(
				"BENCH fps=%d draw_calls=%d objects=%d process_ms=%.2f physics_ms=%.2f"
				% [
					Engine.get_frames_per_second(),
					RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
					RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
					Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
					Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
				]
			)
