class_name TilesetFactory
extends RefCounted
## Сборка TileSet из PNG-атласа модульного тайлсета во время запуска.
##
## Атлас: 4 тайла в строке, 12 тайлов, индексы соответствуют
## tools/stage2_location/make_pixel_proxies.py. Коллизия задаётся физическим
## слоем TileSet, поэтому проходимость проверяется на настоящем тайлсете,
## а не на отдельных StaticBody2D.

const SOURCE_ID := 0
const COLUMNS := 4
const TILE_COUNT := 12

const T_DIRT_A := 0
const T_DIRT_B := 1
const T_PATH := 2
const T_GRASS := 3
const T_MUD := 4
const T_PLANKS := 5
const T_WALL_A := 6
const T_WALL_B := 7
const T_FENCE := 8
const T_POST := 9
const T_STONE_DARK := 10
const T_VOID := 11

## Непроходимые тайлы: стены, частокол, столб, камень, «пустота».
const SOLID_TILES := [T_WALL_A, T_WALL_B, T_FENCE, T_POST, T_STONE_DARK, T_VOID]

const ATLAS_COORDS := [
	Vector2i(0, 0), Vector2i(1, 0), Vector2i(2, 0), Vector2i(3, 0),
	Vector2i(0, 1), Vector2i(1, 1), Vector2i(2, 1), Vector2i(3, 1),
	Vector2i(0, 2), Vector2i(1, 2), Vector2i(2, 2), Vector2i(3, 2),
]


static func atlas_coord(tile: int) -> Vector2i:
	return ATLAS_COORDS[clampi(tile, 0, TILE_COUNT - 1)]


static func build(sheet: Texture2D, tile_px: int) -> TileSet:
	var tile_set := TileSet.new()
	tile_set.tile_size = Vector2i(tile_px, tile_px)
	var source := TileSetAtlasSource.new()
	source.texture = sheet
	source.texture_region_size = Vector2i(tile_px, tile_px)
	for tile in TILE_COUNT:
		source.create_tile(atlas_coord(tile))
	tile_set.add_source(source, SOURCE_ID)
	tile_set.add_physics_layer()
	tile_set.set_physics_layer_collision_layer(0, 1)
	tile_set.set_physics_layer_collision_mask(0, 1)
	var half := float(tile_px) * 0.5
	var square := PackedVector2Array([
		Vector2(-half, -half),
		Vector2(half, -half),
		Vector2(half, half),
		Vector2(-half, half),
	])
	for tile in SOLID_TILES:
		var data: TileData = source.get_tile_data(atlas_coord(tile), 0)
		data.add_collision_polygon(0)
		data.set_collision_polygon_points(0, 0, square)
	return tile_set


static func dirt_variant(cell: Vector2i) -> int:
	return T_DIRT_B if (cell.x * 7 + cell.y * 13) % 5 == 0 else T_DIRT_A


static func base_tile(ch: String, cell: Vector2i) -> int:
	match ch:
		"g", "T":
			return T_GRASS
		"m":
			return T_MUD
		"p":
			return T_PLANKS
		"f", "#":
			return dirt_variant(cell)
		"=", "@":
			return dirt_variant(cell)
		_:
			return dirt_variant(cell)


static func detail_tile(ch: String) -> int:
	if ch == "=" or ch == "@":
		return T_PATH
	return -1


static func obstacle_tile(ch: String, cell: Vector2i) -> int:
	match ch:
		"#":
			return T_WALL_B if (cell.x * 5 + cell.y * 11) % 4 == 0 else T_WALL_A
		"f":
			return T_FENCE
		_:
			return -1
