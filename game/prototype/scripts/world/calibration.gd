extends Node2D
## Художественный калибровочный кадр (Этап 3, задача 3.1b).
##
## Что это: **один небольшой, но качественный вертикальный художественный срез**
## ночной древнерусской деревни — двор перед белокаменной часовней, частокол,
## воротная башня, изба с тёплыми окнами, мёртвое дерево с красными лоскутами,
## мокрая земля с лужами, туман и локальные источники света.
##
## Что это НЕ: не финальный арт игры, не утверждённая локация (D10) и не переделка
## Этапа 2. Статус набора — `ASSET_DRAFT`; `ASSET_APPROVED` ставит только владелец.
##
## Технические границы (D16) не меняются: тайл 24 px, герой 48 px, камера zoom 1.0,
## 480x270, окно 960x540, 4 направления, спрайты героя из Pixelorama.
##
## Запуск:
##   godot --path game/prototype res://scenes/calibration.tscn
##   godot --path game/prototype res://scenes/calibration.tscn -- --shot=C:/tmp/c.png --shot-frames=150
##   godot --path game/prototype res://scenes/calibration.tscn -- --face=left --walk
##
## `--walk` включает короткий маршрут героя (4 отрезка) для записи клипа: это
## проверка читаемости сцены в движении, а не анимация движения (она — задача 3.2).

const PLAYER_SCRIPT := "res://scripts/world/player_world.gd"
const ART := "res://art/calibration/"

## Кадр проверки: те же константы, что у основной локации; берутся из PixelProfiles,
## чтобы калибровка не могла «незаметно» разойтись с утверждённым стандартом D16.
var _profile: Dictionary = PixelProfiles.get_profile(PixelProfiles.APPROVED_ID)
var _tile := 24
var _zoom := 1.0

## Холодная ночная тонировка: сцена держится в сине-серой гамме, тёплый свет
## добавляется локально (запечённые пятна + мерцание огня).
##
## Почему свет запечён, а не динамический: калибровка с `PointLight2D` (5 источников,
## аддитивный блендинг, nearest-фильтр, целочисленные позиции) дала 5–6 блоков 2x2
## с расхождением до 9/255 на кадре 960x540 (замер `check_pixel_scale.py
## --block 2 --tolerance 8`), то есть нарушала требование пиксельной чистоты.
## Запечённые аддитивные пятна из того же дизеренного атласа дают 0 таких блоков.
## Динамические источники оставлены под флагом `--lights` для сравнения.
const NIGHT_TINT := Color(0.58, 0.64, 0.88, 1.0)
const TORCH_COLOR := Color(1.0, 0.76, 0.46, 1.0)

## Театр кадра: 28x18 тайлов = 672x432 px. При камере zoom 1.0 в кадр попадает
## 20x11.25 тайла, то есть ровно участок двора с героем.
const MAP := Vector2i(28, 18)
const HERO_CELL := Vector2i(13, 12)

## Индексы тайлов в калибровочном атласе (4 колонки x 2 ряда).
const T_EARTH_A := 0
const T_EARTH_B := 1
const T_EARTH_C := 2
const T_PATH_A := 3
const T_PATH_B := 4
const T_PLANKS := 5
const T_PLANKS_WET := 6
const T_CURB := 7

## Пропсы: позиция — левый верхний угол в мировых пикселях (centered = false).
## Порядок в массиве задаёт порядок отрисовки внутри одного z_index.
const PROPS := [
	{"name": "Forest", "tex": "forest_24.png", "pos": Vector2(236, 130), "z": -6},
	{"name": "PalisadeL", "tex": "palisade_24.png", "pos": Vector2(228, 176), "z": 1},
	{"name": "PalisadeR", "tex": "palisade_24.png", "pos": Vector2(372, 176), "z": 1},
	{"name": "Gate", "tex": "gate_calib_24.png", "pos": Vector2(276, 156), "z": 1},
	{"name": "Izba", "tex": "izba_24.png", "pos": Vector2(76, 140), "z": 2},
	{"name": "Chapel", "tex": "chapel_24.png", "pos": Vector2(396, 140), "z": 2},
	{"name": "Banner", "tex": "banner_24.png", "pos": Vector2(382, 174), "z": 3},
	{"name": "TorchL", "tex": "torch_24.png", "pos": Vector2(252, 228), "z": 4, "torch": true},
	{"name": "TorchR", "tex": "torch_24.png", "pos": Vector2(372, 228), "z": 4, "torch": true},
	{"name": "DeadTree", "tex": "dead_tree_24.png", "pos": Vector2(120, 190), "z": 7},
]

## Мелкие пропсы двора — кадры листа `props_calib_24.png` (0 кадь, 1 поленница,
## 2 камень, 3 колесо). Позиция — левый верхний угол кадра 24x24.
const SMALL_PROPS := [
	{"name": "BarrelA", "frame": 0, "pos": Vector2(196, 312), "z": 3},
	{"name": "BarrelB", "frame": 0, "pos": Vector2(216, 322), "z": 3},
	{"name": "WoodpileR", "frame": 1, "pos": Vector2(468, 316), "z": 3},
	{"name": "WoodpileL", "frame": 1, "pos": Vector2(84, 300), "z": 3},
	{"name": "RoadStone", "frame": 2, "pos": Vector2(286, 366), "z": 3},
	{"name": "CartWheel", "frame": 3, "pos": Vector2(444, 350), "z": 3},
]

## Лужи: лежат на земле, под пропсами и героем.
const PUDDLES := [
	{"tex": "puddle_c_24.png", "pos": Vector2(300, 318)},
	{"tex": "puddle_a_24.png", "pos": Vector2(196, 352)},
	{"tex": "puddle_b_24.png", "pos": Vector2(430, 302)},
	{"tex": "puddle_a_24.png", "pos": Vector2(148, 296)},
	{"tex": "puddle_b_24.png", "pos": Vector2(344, 366)},
]

## Тёплые пятна света на земле (запечённые, аддитивные): окна, портал, факелы,
## пятно у героя. Позиция — центр пятна, целые пиксели. Альфа намеренно низкая:
## свет должен выделять точки, а не заливать двор оранжевым.
const BAKED_GLOWS := [
	{"pos": Vector2(262, 296), "scale": 2, "alpha": 0.34, "color": Color(1.0, 0.68, 0.38)},
	{"pos": Vector2(386, 296), "scale": 2, "alpha": 0.32, "color": Color(1.0, 0.68, 0.38)},
	{"pos": Vector2(172, 268), "scale": 2, "alpha": 0.24, "color": Color(1.0, 0.66, 0.36)},
	{"pos": Vector2(202, 258), "scale": 1, "alpha": 0.20, "color": Color(1.0, 0.68, 0.40)},
	{"pos": Vector2(480, 268), "scale": 3, "alpha": 0.28, "color": Color(1.0, 0.60, 0.30)},
	{"pos": Vector2(324, 336), "scale": 1, "alpha": 0.26, "color": Color(1.0, 0.70, 0.42)},
	{"pos": Vector2(324, 300), "scale": 1, "alpha": 0.18, "color": Color(1.0, 0.74, 0.46)},
]

## Холодные пятна (лунный свет): держат контраст «тёплое-холодное», без них
## двор выглядит просто коричневым. Также запечённые.
const COLD_GLOWS := [
	{"pos": Vector2(200, 208), "scale": 3, "alpha": 0.26, "color": Color(0.55, 0.70, 1.0)},
	{"pos": Vector2(430, 190), "scale": 2, "alpha": 0.20, "color": Color(0.60, 0.74, 1.0)},
	{"pos": Vector2(60, 240), "scale": 2, "alpha": 0.16, "color": Color(0.55, 0.70, 1.0)},
]

## Коллизии непроходимых объектов (центр, размер) — герой не входит в стены и столбы.
const COLLIDERS := [
	{"name": "IzbaBase", "center": Vector2(172, 252), "size": Vector2(192, 16)},
	{"name": "ChapelBase", "center": Vector2(480, 252), "size": Vector2(168, 16)},
	{"name": "PalisadeL", "center": Vector2(252, 238), "size": Vector2(48, 20)},
	{"name": "PalisadeR", "center": Vector2(396, 238), "size": Vector2(48, 20)},
	{"name": "GatePostLeft", "center": Vector2(282, 226), "size": Vector2(12, 52)},
	{"name": "GatePostRight", "center": Vector2(366, 226), "size": Vector2(12, 52)},
	{"name": "TorchBaseL", "center": Vector2(264, 297), "size": Vector2(22, 10)},
	{"name": "TorchBaseR", "center": Vector2(384, 297), "size": Vector2(22, 10)},
	{"name": "TreeTrunk", "center": Vector2(158, 336), "size": Vector2(30, 22)},
]

@onready var ground: TileMapLayer = $Layers/Ground
@onready var details: Node2D = $Layers/Details
@onready var structures: Node2D = $Layers/Structures
@onready var collision_root: Node2D = $Layers/Collision
@onready var entities: Node2D = $Layers/Entities
@onready var atmosphere: Node2D = $Layers/Atmosphere
@onready var night_tint: CanvasModulate = $Layers/Atmosphere/NightTint
@onready var camera: Camera2D = $Layers/Entities/CameraRig
@onready var fog_root: Node2D = $Layers/Atmosphere/Fog
@onready var light_root: Node2D = $Layers/Atmosphere/Lights
@onready var hud: CanvasLayer = $HUD
@onready var hud_info: Label = $HUD/Info

var _player: CharacterBody2D
var _shadow: Sprite2D
var _torches: Array[Dictionary] = []
var _glows: Array[Dictionary] = []
var _fog_sprites: Array[Sprite2D] = []
var _fog_base_alpha: Array = [0.55, 0.45, 0.35]
var _fog_speed: Array = [0.35, -0.27, 0.19]
var _walk := false
var _walk_time := 0.0
var _walk_index := 0
var _walk_cycles := 0
var _time := 0.0
var _frames := 0
var _dynamic_lights := false
## Диагностические режимы проверки пиксельной чистоты: выключают ту или иную
## часть освещения, чтобы понять источник неодноцветных блоков в кадре.
var _no_lights := false
var _no_baked := false
var _no_fog := false
var _no_vignette := false

## Маршрут для клипа: (направление, секунды). Небольшой участок двора, чтобы
## камера не уезжала из композиции, а герой показывался в четырёх направлениях.
const WALK_ROUTE := [
	{"dir": Vector2(1, 0), "time": 1.1},
	{"dir": Vector2(0, -1), "time": 0.7},
	{"dir": Vector2(-1, 0), "time": 1.3},
	{"dir": Vector2(0, 1), "time": 0.6},
]


func _ready() -> void:
	_tile = int(_profile["tile_px"])
	_zoom = float(_profile["camera_zoom"])
	for arg in OS.get_cmdline_user_args():
		if arg == "--walk":
			_walk = true
		elif arg == "--hud":
			hud.visible = true
		elif arg == "--no-lights":
			_no_lights = true
		elif arg == "--no-baked":
			_no_baked = true
		elif arg == "--no-fog":
			_no_fog = true
		elif arg == "--no-vignette":
			_no_vignette = true
		elif arg == "--lights":
			_dynamic_lights = true
	print(PixelProfiles.describe(_profile))
	print(PixelProfiles.constants_summary(_profile))
	print("CALIB_ART art=res://art/calibration art_revision=3.1b status=ASSET_DRAFT tile_px=%d" % _tile)

	_build_ground()
	_spawn_details()
	_spawn_props()
	_spawn_colliders()
	_spawn_player()
	_setup_camera()
	_setup_atmosphere()
	_setup_fog()
	_setup_vignette()
	_setup_hud()
	if _walk:
		_player.call("set_scripted_dir", WALK_ROUTE[0]["dir"])
		print("WALK_START segments=%d dir=%s" % [WALK_ROUTE.size(), str(WALK_ROUTE[0]["dir"])])

	print(
		"CALIB_READY map=%dx%d tile_px=%d visible_tiles=%.2fx%.2f props=%d puddles=%d lights=%d fog=%d hero_px=%d"
		% [
			MAP.x,
			MAP.y,
			_tile,
			PixelProfiles.visible_tiles(_profile).x,
			PixelProfiles.visible_tiles(_profile).y,
			structures.get_child_count(),
			details.get_child_count(),
			light_root.get_child_count(),
			fog_root.get_child_count(),
			int(_profile["hero_height_px"]),
		]
	)


# --- земля -------------------------------------------------------------------


func _build_ground() -> void:
	var sheet: Texture2D = load(ART + "ground_calib_24.png")
	if sheet == null:
		push_error("Не найден калибровочный тайлсет")
		return
	var tile_set := TileSet.new()
	tile_set.tile_size = Vector2i(_tile, _tile)
	var source := TileSetAtlasSource.new()
	source.texture = sheet
	source.texture_region_size = Vector2i(_tile, _tile)
	for index in 8:
		source.create_tile(Vector2i(index % 4, index / 4))
	tile_set.add_source(source, 0)
	ground.tile_set = tile_set
	ground.collision_enabled = false

	var counts := {}
	for y in MAP.y:
		for x in MAP.x:
			var cell := Vector2i(x, y)
			var tile := _ground_tile(cell)
			ground.set_cell(cell, 0, Vector2i(tile % 4, tile / 4))
			counts[tile] = int(counts.get(tile, 0)) + 1
	print("CALIB_GROUND cells=%d variants=%s" % [ground.get_used_cells().size(), str(counts)])


## Раскладка земли: дорожка из плит ведёт от врат к герою, бордюр держит её края,
## деревянные мостки — к дверям избы и порталу часовни, настил в нижней полосе
## кадра, трава — по краям двора.
func _ground_tile(cell: Vector2i) -> int:
	var x := cell.x
	var y := cell.y
	if y >= 16:
		return T_PLANKS_WET if (x * 5 + y * 3) % 4 != 0 else T_PLANKS
	# Дорога: широкий вытоптанный тракт из плотной земли с втоптанными камнями.
	if x >= 11 and x <= 15 and y >= 4:
		return [T_PATH_A, T_PATH_B, T_CURB][(x * 7 + y * 13) % 3]
	# Мостки к дверям: путь героя читается, двор не выглядит пустым полем.
	if y >= 13 and y <= 15 and x >= 18 and x <= 21:
		return T_PLANKS
	if y >= 11 and (x <= 9 or x >= 22):
		return T_EARTH_C
	if y >= 14 and x >= 6 and x <= 10:
		return T_EARTH_C
	return T_EARTH_B if (x * 5 + y * 11) % 7 == 0 else T_EARTH_A


func _spawn_details() -> void:
	for puddle in PUDDLES:
		var sprite := Sprite2D.new()
		sprite.name = "Puddle_%d" % details.get_child_count()
		sprite.texture = load(ART + puddle["tex"])
		sprite.centered = false
		sprite.position = puddle["pos"]
		sprite.z_index = 0
		details.add_child(sprite)


# --- пропсы ------------------------------------------------------------------


func _spawn_props() -> void:
	for entry in PROPS:
		var sprite := Sprite2D.new()
		sprite.name = entry["name"]
		sprite.texture = load(ART + entry["tex"])
		sprite.centered = false
		sprite.position = entry["pos"]
		sprite.z_index = int(entry["z"])
		structures.add_child(sprite)
		if bool(entry.get("torch", false)):
			# Лист факела — 2 кадра огня по 24x72; кадр переключается в _process.
			sprite.hframes = 2
			sprite.vframes = 1
			_torches.append({"sprite": sprite, "phase": float(_torches.size()) * 0.7})
	# Мелкие пропсы двора: один лист на четыре предмета, кадр выбирается полем frame.
	for entry in SMALL_PROPS:
		var sprite := Sprite2D.new()
		sprite.name = entry["name"]
		sprite.texture = load(ART + "props_calib_24.png")
		sprite.hframes = 4
		sprite.vframes = 1
		sprite.frame = int(entry["frame"])
		sprite.centered = false
		sprite.position = entry["pos"]
		sprite.z_index = int(entry["z"])
		structures.add_child(sprite)
	# Запечённые тёплые пятна: аддитивные спрайты на земле, выровненные по пикселю.
	for glow in BAKED_GLOWS:
		if _no_baked:
			break
		var sprite := Sprite2D.new()
		sprite.name = "BakedGlow_%d" % structures.get_child_count()
		sprite.texture = load(ART + "glow_warm_24.png")
		sprite.centered = true
		var scale_factor := float(glow["scale"])
		sprite.scale = Vector2(scale_factor, scale_factor)
		sprite.modulate = Color(glow["color"].r, glow["color"].g, glow["color"].b, float(glow["alpha"]))
		# Целая позиция + целый масштаб = каждый тексель света попадает в целый
		# блок пикселей арта; дизеринг свечения не размывается.
		sprite.position = glow["pos"].round()
		sprite.z_index = 0
		var material := CanvasItemMaterial.new()
		material.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		sprite.material = material
		structures.add_child(sprite)
		# Мерцание: меняется только альфа пятна, геометрия и позиция неизменны,
		# поэтому блоки пикселей остаются одноцветными.
		_glows.append({"sprite": sprite, "alpha": float(glow["alpha"]), "phase": float(_glows.size()) * 0.9})
	# Холодные пятна лунного света: та же геометрия, другая текстура и цвет.
	for glow in COLD_GLOWS:
		if _no_baked:
			break
		var sprite := Sprite2D.new()
		sprite.name = "BakedCold_%d" % structures.get_child_count()
		sprite.texture = load(ART + "glow_cold_24.png")
		sprite.centered = true
		var scale_factor := float(glow["scale"])
		sprite.scale = Vector2(scale_factor, scale_factor)
		sprite.modulate = Color(glow["color"].r, glow["color"].g, glow["color"].b, float(glow["alpha"]))
		sprite.position = glow["pos"].round()
		sprite.z_index = 0
		var material := CanvasItemMaterial.new()
		material.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		sprite.material = material
		structures.add_child(sprite)
		_glows.append({"sprite": sprite, "alpha": float(glow["alpha"]), "phase": float(_glows.size()) * 0.6})


func _spawn_colliders() -> void:
	for entry in COLLIDERS:
		var body := StaticBody2D.new()
		body.name = entry["name"]
		body.collision_layer = 1
		body.collision_mask = 0
		var shape := CollisionShape2D.new()
		var rect := RectangleShape2D.new()
		rect.size = entry["size"]
		shape.shape = rect
		body.add_child(shape)
		body.position = entry["center"]
		collision_root.add_child(body)


# --- герой -------------------------------------------------------------------


func _spawn_player() -> void:
	var tile := float(_tile)
	_player = CharacterBody2D.new()
	_player.name = "Player"
	_player.set_script(load(PLAYER_SCRIPT))
	_player.position = Vector2(HERO_CELL) * tile + Vector2(tile * 0.5, tile * 0.5)
	_player.collision_layer = 2
	_player.collision_mask = 1
	_player.z_index = 6
	_player.set("speed", tile * 3.2)

	var sprite := Sprite2D.new()
	sprite.name = "Sprite2D"
	sprite.texture = load(_profile["hero_sheet"])
	sprite.hframes = int(_profile.get("hero_hframes", PixelProfiles.HERO_SHEET_FRAMES))
	sprite.vframes = 1
	sprite.centered = true
	sprite.offset = Vector2(0.0, -float(_profile["hero_height_px"]) * 0.5)
	_player.add_child(sprite)
	_player.set("hero_directional", bool(_profile.get("hero_directional", false)))
	_player.set("hero_directions", int(_profile.get("directions", 4)))
	_player.set("hero_frames_per_direction", int(_profile.get("hero_frames_per_direction", 1)))
	_player.set("idle_fps", float(_profile.get("hero_idle_fps", 1.4)))

	var body := CollisionShape2D.new()
	body.name = "CollisionShape2D"
	var shape := RectangleShape2D.new()
	shape.size = Vector2(tile * 0.5, tile * 0.4)
	body.shape = shape
	body.position = Vector2(0.0, -shape.size.y * 0.5)
	_player.add_child(body)

	# Контактная тень: без неё герой «висит» над землёй. Тень — отдельный спрайт
	# и ставится на целый пиксель каждый кадр (`_process`), иначе она мылит блоки.
	_shadow = Sprite2D.new()
	_shadow.name = "HeroContactShadow"
	_shadow.texture = load(ART + "shadow_24.png")
	_shadow.centered = true
	_shadow.position = _player.position + Vector2(0.0, -1.0)
	_shadow.z_index = 5
	entities.add_child(_shadow)

	entities.add_child(_player)
	print(
		"PLAYER_SPAWN cell=%s pos=%.1f,%.1f hero_px=%d sheet=%s hframes=%d"
		% [
			str(HERO_CELL),
			_player.position.x,
			_player.position.y,
			_profile["hero_height_px"],
			_profile["hero_sheet"],
			int(_profile.get("hero_hframes", 0)),
		]
	)


# --- камера, свет, туман, виньетка -------------------------------------------


func _setup_camera() -> void:
	camera.zoom = Vector2(_zoom, _zoom)
	camera.position_smoothing_enabled = false
	camera.limit_left = 0
	camera.limit_top = 0
	camera.limit_right = MAP.x * _tile
	camera.limit_bottom = MAP.y * _tile
	camera.limit_smoothed = false
	camera.offset = Vector2.ZERO
	camera.set("grid_offset", Vector2(_grid_offset(true), _grid_offset(false)))
	camera.global_position = _player.global_position.round()
	camera.set("target", _player)
	camera.set("lookahead", Vector2(0.0, -float(_tile)))
	camera.make_current()
	print(
		"CAMERA_READY zoom=%.1f limits=%d,%d,%d,%d"
		% [_zoom, camera.limit_left, camera.limit_top, camera.limit_right, camera.limit_bottom]
	)


## Половина кадра в мировых пикселях при 270 и zoom 1.0 равна 135 — целая.
## Компенсация оставлена как в основной локации: она не даёт сетке арта
## сместиться на пол-пикселя, если константы когда-нибудь изменятся.
func _grid_offset(horizontal: bool) -> float:
	var view := 480.0 if horizontal else 270.0
	var half_world := view / (2.0 * _zoom)
	return half_world - floorf(half_world)


func _setup_atmosphere() -> void:
	night_tint.color = NIGHT_TINT
	if _no_lights or not _dynamic_lights:
		print(
			"ATMOSPHERE_READY tint=%s dynamic_lights=off baked_glows=%d (режим калибровки: запечённый свет)"
			% [str(NIGHT_TINT), _glows.size()]
		)
		return
	var texture: Texture2D = load(ART + "glow_warm_24.png")
	# Тёплые точечные источники: факелы у врат и окна/портал. Текстура света
	# целочисленно масштабируется и ставится кратно масштабу — иначе дизеринг
	# свечения попадает на дробное смещение и рвёт блоки пикселей.
	var sources := [
		{"pos": Vector2(264, 250), "energy": 1.0, "scale": 1, "color": TORCH_COLOR},
		{"pos": Vector2(384, 250), "energy": 1.0, "scale": 1, "color": TORCH_COLOR},
		{"pos": Vector2(172, 250), "energy": 0.85, "scale": 1, "color": Color(1.0, 0.72, 0.44)},
		{"pos": Vector2(480, 250), "energy": 0.95, "scale": 1, "color": Color(1.0, 0.66, 0.38)},
		{"pos": Vector2(324, 270), "energy": 0.55, "scale": 1, "color": Color(1.0, 0.78, 0.52)},
	]
	for index in sources.size():
		var entry: Dictionary = sources[index]
		var light := PointLight2D.new()
		light.name = "WarmLight_%d" % index
		light.texture = texture
		light.texture_scale = float(entry["scale"])
		light.color = entry["color"]
		light.energy = float(entry["energy"])
		light.blend_mode = Light2D.BLEND_MODE_ADD
		light.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		# Целая позиция при целой сетке текстуры света: дизеринг свечения ложится
		# точно на пиксели арта и не рвёт блоки 2x2 экрана.
		light.position = entry["pos"].round()
		light_root.add_child(light)
		if index < 2:
			_torches[index]["light"] = light
	print(
		"ATMOSPHERE_READY tint=%s lights=%d torches=%d"
		% [str(NIGHT_TINT), light_root.get_child_count(), _torches.size()]
	)


func _setup_fog() -> void:
	if _no_fog:
		print("FOG_SKIPPED (диагностический режим --no-fog)")
		return
	# Три слоя тумана: разные текстуры, альфа и скорость — «дышащая» ночь.
	var layers := [
		{"tex": "fog_a_24.png", "pos": Vector2(120, 150), "alpha": 0.55, "speed": 0.35, "z": 20},
		{"tex": "fog_b_24.png", "pos": Vector2(300, 190), "alpha": 0.45, "speed": -0.27, "z": 21},
		{"tex": "fog_a_24.png", "pos": Vector2(60, 250), "alpha": 0.35, "speed": 0.19, "z": 22},
	]
	for entry in layers:
		var sprite := Sprite2D.new()
		sprite.name = "Fog_%d" % fog_root.get_child_count()
		sprite.texture = load(ART + entry["tex"])
		sprite.centered = true
		sprite.position = entry["pos"]
		sprite.z_index = int(entry["z"])
		sprite.modulate = Color(1, 1, 1, float(entry["alpha"]))
		fog_root.add_child(sprite)
		_fog_sprites.append(sprite)


func _setup_vignette() -> void:
	if _no_vignette:
		print("POSTFX_SKIPPED (диагностический режим --no-vignette)")
		return
	var post := CanvasLayer.new()
	post.name = "PostFX"
	post.layer = 1
	var rect := TextureRect.new()
	rect.name = "Vignette"
	rect.texture = load(ART + "vignette_24.png")
	rect.position = Vector2.ZERO
	rect.size = Vector2(PixelProfiles.VIEWPORT)
	rect.stretch_mode = TextureRect.STRETCH_SCALE
	rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	post.add_child(rect)
	add_child(post)
	print("POSTFX_READY vignette=%dx%d layer=%d" % [PixelProfiles.VIEWPORT.x, PixelProfiles.VIEWPORT.y, post.layer])


func _setup_hud() -> void:
	hud.visible = false
	hud_info.text = PixelProfiles.hud_text(_profile, 0)


# --- анимация и маршрут ------------------------------------------------------


func _process(delta: float) -> void:
	_time += delta
	_frames += 1
	# Огонь: два кадра плюс небольшое изменение энергии света — «живое» пламя.
	for index in _torches.size():
		var torch: Dictionary = _torches[index]
		var sprite: Sprite2D = torch["sprite"]
		var phase: float = torch["phase"]
		var step := int(floor((_time * 7.0 + phase) / 2.0))
		sprite.frame = 0 if step % 2 == 0 else 1
		if torch.has("light"):
			var light: PointLight2D = torch["light"]
			light.energy = 0.92 + 0.16 * sin(_time * 6.3 + phase) + 0.06 * sin(_time * 11.7 + phase)
	for index in _glows.size():
		var glow: Dictionary = _glows[index]
		var glow_sprite: Sprite2D = glow["sprite"]
		var base_alpha: float = glow["alpha"]
		var phase: float = glow["phase"]
		glow_sprite.modulate.a = base_alpha * (0.88 + 0.12 * sin(_time * 5.1 + phase))
	for index in _fog_sprites.size():
		var sprite: Sprite2D = _fog_sprites[index]
		var base: float = _fog_base_alpha[index]
		var speed: float = _fog_speed[index]
		sprite.modulate.a = base + 0.10 * sin(_time * speed + index * 1.7)
	if _walk:
		_advance_walk(delta)
	if _frames % 30 == 0:
		hud_info.text = PixelProfiles.hud_text(_profile, Engine.get_frames_per_second())
	# Тень держится на целом пикселе мира: при целочисленном масштабе камеры
	# каждый пиксель тени попадает в целый блок экрана.
	if _shadow != null and _player != null:
		_shadow.position = _player.global_position.round() + Vector2(0.0, -1.0)


func _advance_walk(delta: float) -> void:
	_walk_time += delta
	if _walk_time >= float(WALK_ROUTE[_walk_index]["time"]):
		_walk_time = 0.0
		_walk_index = (_walk_index + 1) % WALK_ROUTE.size()
		if _walk_index == 0:
			_walk_cycles += 1
		var segment: Dictionary = WALK_ROUTE[_walk_index]
		_player.call("set_scripted_dir", segment["dir"])
		print(
			"WALK_SEGMENT index=%d cycle=%d dir=%s pos=%.1f,%.1f"
			% [_walk_index, _walk_cycles, str(segment["dir"]), _player.global_position.x, _player.global_position.y]
		)
		# Два полных круга маршрута и выход: клип записывается Movie Maker-ом,
		# и сцена должна завершиться сама (оконный `--quit-after` в среде зависает).
		if _walk_cycles >= 2:
			print("WALK_DONE cycles=%d frames=%d" % [_walk_cycles, _frames])
			get_tree().quit()
