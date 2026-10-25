extends Node2D
## Экспериментальный кадр исследования разрешений (задача 3.1c).
##
## Один и тот же участок локации и один и тот же герой показываются в трёх
## вариантах исходной детализации. Окно всегда 1920×1080, поэтому высота героя
## на экране одинакова (192 px), а масштаб разный:
##
##   A: логическое 480×270, тайл 24 px, герой 48 px, масштаб 4×
##   B: логическое 640×360, тайл 32 px, герой 64 px, масштаб 3×
##   C: логическое 960×540, тайл 48 px, герой 96 px, масштаб 2×
##
## Флаги:  --variant=a|b|c   --no-lights   --no-flicker   --shot=<абсолютный путь>
## Скриншот снимается из реального окна рендера (не headless).

const WINDOW_SIZE := Vector2i(1920, 1080)
const LAYOUT_PATH := "res://art/layout.json"

var variant: String = "a"
var data: Dictionary = {}
var lights_on: bool = true
var hero_on: bool = true
var flicker: bool = true
var shot_path: String = ""
var frames_until_shot: int = 8
var elapsed: float = 0.0

var world_sprite: Sprite2D
var hero_sprite: Sprite2D
var torch_light: PointLight2D
var base_energy: float = 1.50


func _ready() -> void:
    _parse_args()
    _load_layout()
    _configure_window()
    _build_scene()
    _report()
    if shot_path != "":
        set_process(true)


func _parse_args() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--variant="):
            variant = arg.get_slice("=", 1).strip_edges().to_lower()
        elif arg == "--no-lights":
            lights_on = false
        elif arg == "--no-hero":
            hero_on = false
        elif arg == "--no-flicker":
            flicker = false
        elif arg.begins_with("--shot="):
            shot_path = arg.get_slice("=", 1)


func _load_layout() -> void:
    var file := FileAccess.open(LAYOUT_PATH, FileAccess.READ)
    if file == null:
        push_error("нет %s" % LAYOUT_PATH)
        get_tree().quit(2)
        return
    var parsed = JSON.parse_string(file.get_as_text())
    if typeof(parsed) != TYPE_DICTIONARY:
        push_error("layout.json не разобран")
        get_tree().quit(2)
        return
    var all: Dictionary = parsed
    if not all.has(variant):
        push_error("вариант %s отсутствует в layout.json" % variant)
        get_tree().quit(2)
        return
    data = all[variant]


func _configure_window() -> void:
    var viewport_size: Array = data["viewport"]
    var logical := Vector2i(int(viewport_size[0]), int(viewport_size[1]))
    var window := get_window()
    window.size = WINDOW_SIZE
    window.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
    window.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_KEEP
    window.content_scale_size = logical


func _build_scene() -> void:
    var base := "res://art/%s/" % variant

    world_sprite = Sprite2D.new()
    world_sprite.name = "World"
    world_sprite.texture = load(base + String(data["world_png"]))
    world_sprite.centered = false
    world_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
    add_child(world_sprite)

    var scale_factor := float(data["hero_scale"])
    var hero_height := float(data["hero_height"])
    var hero_pos: Array = data["hero_pos"]
    if hero_on:
        hero_sprite = Sprite2D.new()
        hero_sprite.name = "Hero"
        hero_sprite.texture = load(base + String(data["hero_png"]))
        hero_sprite.centered = true
        hero_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
        # Увеличение делает content_scale логического разрешения. Спрайт остаётся
        # в логических пикселях 1:1, иначе масштаб применился бы дважды.
        hero_sprite.scale = Vector2(scale_factor, scale_factor)
        # центр спрайта ставим так, чтобы ступни стояли в точке hero_pos
        hero_sprite.position = Vector2(float(hero_pos[0]),
                                       float(hero_pos[1]) - hero_height * scale_factor * 0.5)
        add_child(hero_sprite)
    else:
        print("STUDY hero=disabled (--no-hero): кадр-эталон для замера силуэта")

    # ночная тонировка: холодный синий, чтобы тёплый факел читался
    var night := CanvasModulate.new()
    night.name = "Night"
    night.color = Color(0.50, 0.56, 0.70)
    add_child(night)

    if lights_on:
        var light_pos: Array = data["light_pos"]
        torch_light = PointLight2D.new()
        torch_light.name = "TorchLight"
        torch_light.texture = load(base + String(data["light_png"]))
        torch_light.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
        torch_light.texture_scale = float(data["light_scale"])
        torch_light.position = Vector2(float(light_pos[0]), float(light_pos[1]))
        torch_light.color = Color(1.0, 0.70, 0.38)
        torch_light.energy = base_energy
        torch_light.blend_mode = Light2D.BLEND_MODE_ADD
        add_child(torch_light)


func _report() -> void:
    var window := get_window()
    var logical := window.content_scale_size
    var scale_x := float(window.size.x) / float(logical.x)
    var hero_px := float(data["hero_height"])
    var hero_scale := float(data["hero_scale"])
    var hero_screen := hero_px * scale_x
    print("STUDY variant=%s logical=%dx%d window=%dx%d scale=%.2fx tile=%dpx"
            % [variant.to_upper(), logical.x, logical.y, window.size.x, window.size.y,
               scale_x, int(data["tile"])])
    print("STUDY hero=%s hero_height=%dpx sprite_scale=%.2f on_screen=%dpx lights=%s flicker=%s"
            % [data["hero_png"], int(hero_px), hero_scale, int(hero_screen), lights_on, flicker])


func _process(delta: float) -> void:
    elapsed += delta
    if torch_light != null and flicker:
        # мягкое мерцание: два несинхронных колебания, без дрожания пикселей
        var f := sin(elapsed * 7.3) * 0.06 + sin(elapsed * 3.1 + 1.7) * 0.05
        torch_light.energy = base_energy * (1.0 + f)
    if shot_path != "":
        frames_until_shot -= 1
        if frames_until_shot <= 0:
            _capture()


func _capture() -> void:
    set_process(false)
    await RenderingServer.frame_post_draw
    var image := get_viewport().get_texture().get_image()
    var error := image.save_png(shot_path)
    if error != OK:
        push_error("не удалось сохранить %s (код %d)" % [shot_path, error])
        get_tree().quit(3)
        return
    print("SHOT %s %dx%d energy=%.3f"
            % [shot_path, image.get_width(), image.get_height(),
               base_energy if torch_light == null else torch_light.energy])
    get_tree().quit(0)
