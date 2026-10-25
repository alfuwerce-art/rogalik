class_name PixelProfiles
extends RefCounted
## Кандидатные пиксельные константы для решения D9 (Этап 2, задача 2.1).
##
## ВАЖНО: ни один набор НЕ утверждён владельцем. Значения остаются TEMPORARY,
## пока владелец не выберет вариант (D9). Наборы отличаются размером тайла,
## высотой спрайта героя и масштабом камеры; сетка кадров и игровое разрешение
## остаются общими, поэтому кадры сравнения снимаются с одной и той же сцены.
##
## Производные величины при окне 960x540 (масштаб окна x2, viewport 480x270):
##   пикселей экрана на пиксель арта = camera_zoom * WINDOW_SCALE (всегда целое);
##   видно тайлов = VIEWPORT / camera_zoom / tile_px.

const VIEWPORT := Vector2i(480, 270)
const WINDOW_SCALE := 2
const HERO_FRAMES := 4
const DEFAULT_ID := "b"

const PROFILES := [
	{
		"id": "a",
		"label": "A · близкая камера, крупный пиксель (16 px)",
		"short_label": "A · крупный пиксель",
		"tile_px": 16,
		"hero_height_px": 32,
		"camera_zoom": 2.0,
		"directions": 4,
		"tileset": "res://art/tilesets/tileset_16.png",
		"hero_sheet": "res://art/sprites/hero_proxy_32.png",
		"tree": "res://art/props/tree_16.png",
		"gate": "res://art/props/gate_16.png",
	},
	{
		"id": "b",
		"label": "B · широкий обзор, средний пиксель (24 px)",
		"short_label": "B · широкий обзор",
		"tile_px": 24,
		"hero_height_px": 48,
		"camera_zoom": 1.0,
		"directions": 4,
		"tileset": "res://art/tilesets/tileset_24.png",
		"hero_sheet": "res://art/sprites/hero_proxy_48.png",
		"tree": "res://art/props/tree_24.png",
		"gate": "res://art/props/gate_24.png",
	},
	{
		"id": "c",
		"label": "C · детальная графика, тайл 32 px",
		"short_label": "C · детальная графика",
		"tile_px": 32,
		"hero_height_px": 64,
		"camera_zoom": 1.0,
		"directions": 4,
		"tileset": "res://art/tilesets/tileset_32.png",
		"hero_sheet": "res://art/sprites/hero_proxy_64.png",
		"tree": "res://art/props/tree_32.png",
		"gate": "res://art/props/gate_32.png",
	},
]


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
		"PROFILE_READY id=%s tile_px=%d hero_height_px=%d zoom=%.1f directions=%d visible_tiles=%.2fx%.2f screen_px_per_art_px=%d"
		% [
			profile["id"],
			profile["tile_px"],
			profile["hero_height_px"],
			profile["camera_zoom"],
			profile["directions"],
			tiles.x,
			tiles.y,
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
	if probe:
		return (
			"%s\nПРОБА БОЕВОГО ПРОСТРАНСТВА · маркеры — PROXY_TECHNICAL, не враги и не механика\nромб 1.8т · круг 4.5т · крест 7т · экран/арт %d× · константы кандидатные (D9)"
			% [first, int(screen_px_per_art_px(profile))]
		)
	return (
		"%s\nэкран/арт %d× · PROXY_TECHNICAL · константы кандидатные (D9), не утверждены"
		% [first, int(screen_px_per_art_px(profile))]
	)
