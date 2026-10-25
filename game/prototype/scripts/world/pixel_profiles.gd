class_name PixelProfiles
extends RefCounted
## Пиксельные константы локации (Этап 2).
##
## Решением владельца **D16 (2026-10-25)** утверждён производственный стандарт —
## профиль **B**: тайл 24 px, герой 48 px, камера zoom 1.0, 4 направления,
## логическое разрешение 480×270 (тестовое окно 960×540, масштаб арта 2×).
## Он используется при обычном запуске и является основным.
##
## Профили A (16 px / zoom 2) и C (32 px / zoom 1) сохранены только как
## **диагностические**: они нужны для проверки поведения сетки и масштаба,
## но для производства арта не используются (D16).
##
## Производные величины при окне 960x540 (масштаб окна x2, viewport 480x270):
##   пикселей экрана на пиксель арта = camera_zoom * WINDOW_SCALE (всегда целое);
##   видно тайлов = VIEWPORT / camera_zoom / tile_px.

const VIEWPORT := Vector2i(480, 270)
const WINDOW_SCALE := 2
## Кадров в старом одностороннем прокси-листе (профили A и C, ПРОКСИ Этапа 2).
const HERO_FRAMES := 4
## Раскладка листа героя Этапа 3: 4 направления × 2 кадра idle, один ряд.
## Pixelorama экспортирует лист в один ряд, поэтому hframes = 4 × 2 = 8.
const HERO_DIRECTIONS := 4
const HERO_IDLE_FRAMES := 2
const HERO_SHEET_FRAMES := HERO_DIRECTIONS * HERO_IDLE_FRAMES
## Частота дыхания idle: 1.4 кадра в секунду — спокойное дыхание, не «дрожь».
const HERO_IDLE_FPS := 1.4
## Утверждённый решением D16 профиль — основной игровой стандарт.
const APPROVED_ID := "b"
## Профиль обычного запуска: совпадает с утверждённым.
const DEFAULT_ID := APPROVED_ID

const PROFILES := [
	{
		"id": "a",
		"label": "A · диагностика: крупный пиксель (16 px)",
		"short_label": "A · диагностика 16 px",
		"approved": false,
		"tile_px": 16,
		"hero_height_px": 32,
		"camera_zoom": 2.0,
		"directions": 4,
		"tileset": "res://art/tilesets/tileset_16.png",
		"hero_sheet": "res://art/sprites/hero_proxy_32.png",
		"hero_hframes": HERO_FRAMES,
		"hero_directional": false,
		"hero_frames_per_direction": 1,
		"hero_idle_fps": 9.0,
		"tree": "res://art/props/tree_16.png",
		"gate": "res://art/props/gate_16.png",
	},
	{
		"id": "b",
		"label": "B · УТВЕРЖДЁННЫЙ СТАНДАРТ (D16): тайл 24 px",
		"short_label": "B · стандарт D16, 24 px",
		"approved": true,
		"tile_px": 24,
		"hero_height_px": 48,
		"camera_zoom": 1.0,
		"directions": 4,
		"tileset": "res://art/tilesets/tileset_24.png",
		"hero_sheet": "res://art/sprites/hero_idle_48.png",
		"hero_hframes": HERO_SHEET_FRAMES,
		"hero_directional": true,
		"hero_frames_per_direction": HERO_IDLE_FRAMES,
		"hero_idle_fps": HERO_IDLE_FPS,
		"tree": "res://art/props/tree_24.png",
		"gate": "res://art/props/gate_24.png",
	},
	{
		"id": "c",
		"label": "C · диагностика: детальная графика (32 px)",
		"short_label": "C · диагностика 32 px",
		"approved": false,
		"tile_px": 32,
		"hero_height_px": 64,
		"camera_zoom": 1.0,
		"directions": 4,
		"tileset": "res://art/tilesets/tileset_32.png",
		"hero_sheet": "res://art/sprites/hero_proxy_64.png",
		"hero_hframes": HERO_FRAMES,
		"hero_directional": false,
		"hero_frames_per_direction": 1,
		"hero_idle_fps": 9.0,
		"tree": "res://art/props/tree_32.png",
		"gate": "res://art/props/gate_32.png",
	},
]


static func is_approved(profile: Dictionary) -> bool:
	return bool(profile.get("approved", false))


static func ids() -> PackedStringArray:
	var result := PackedStringArray()
	for profile in PROFILES:
		result.append(profile["id"])
	return result


static func get_profile(id: String) -> Dictionary:
	for profile in PROFILES:
		if profile["id"] == id:
			return profile.duplicate(true)
	push_warning("Неизвестный профиль '%s', используется '%s'" % [id, DEFAULT_ID])
	return get_profile(DEFAULT_ID)


static func visible_tiles(profile: Dictionary) -> Vector2:
	var zoom: float = profile["camera_zoom"]
	var tile: float = profile["tile_px"]
	return Vector2(VIEWPORT.x / zoom / tile, VIEWPORT.y / zoom / tile)


static func screen_px_per_art_px(profile: Dictionary) -> float:
	return float(profile["camera_zoom"]) * WINDOW_SCALE


static func describe(profile: Dictionary) -> String:
	var tiles := visible_tiles(profile)
	return (
		"PROFILE_READY id=%s approved=%s tile_px=%d hero_height_px=%d zoom=%.1f directions=%d visible_tiles=%.2fx%.2f screen_px_per_art_px=%d"
		% [
			profile["id"],
			"YES" if is_approved(profile) else "NO (diagnostic)",
			profile["tile_px"],
			profile["hero_height_px"],
			profile["camera_zoom"],
			profile["directions"],
			tiles.x,
			tiles.y,
			int(screen_px_per_art_px(profile)),
		]
	)


## Строка подтверждения стандарта: печатается при запуске, чтобы проверка
## не зависела от чтения кода.
static func constants_summary(profile: Dictionary) -> String:
	return (
		"CONSTANTS profile=%s status=%s tile_px=%d hero_height_px=%d camera_zoom=%.1f directions=%d viewport=%dx%d window=%dx%d scale=%dx source=D16"
		% [
			profile["id"],
			"APPROVED" if is_approved(profile) else "DIAGNOSTIC",
			profile["tile_px"],
			profile["hero_height_px"],
			profile["camera_zoom"],
			profile["directions"],
			VIEWPORT.x,
			VIEWPORT.y,
			VIEWPORT.x * WINDOW_SCALE,
			VIEWPORT.y * WINDOW_SCALE,
			int(screen_px_per_art_px(profile)),
		]
	)


static func hud_text(profile: Dictionary, fps: int, probe: bool = false) -> String:
	var tiles := visible_tiles(profile)
	var first := (
		"%s · тайл %d · герой %d · zoom %.1f · %.1f×%.1f тайлов · FPS %d"
		% [
			profile["short_label"],
			profile["tile_px"],
			profile["hero_height_px"],
			profile["camera_zoom"],
			tiles.x,
			tiles.y,
			fps,
		]
	)
	var scale_line := (
		"экран/арт %d× · D16 · константы утверждены"
		% int(screen_px_per_art_px(profile))
		if is_approved(profile)
		else "экран/арт %d× · ДИАГНОСТИЧЕСКИЙ профиль, не для арта (D16)" % int(screen_px_per_art_px(profile))
	)
	if probe:
		return (
			"%s\nПРОБА БОЕВОГО ПРОСТРАНСТВА · маркеры — PROXY_TECHNICAL, не враги и не механика\n%s · ромб 1.8т · круг 4.5т · крест 7т"
			% [first, scale_line]
		)
	return "%s\n%s" % [first, scale_line]
