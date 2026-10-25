"""Малый участок древнерусской локации — три собственных разрешения (3.1c).

Один и тот же кадр (двор перед срубом, белокаменная часовня, факел, лужи,
вытоптанная земля) рисуется в трёх логических разрешениях:

    A 480×270, тайл 24 px
    B 640×360, тайл 32 px
    C 960×540, тайл 48 px

Композиция задана в ТАЙЛАХ, поэтому поле зрения во всех вариантах одинаково
(20 × 11.25 тайла), а различается только исходная детализация: при 48 px на
тайл видны отдельные брёвна, швы кладки, стёкла травы и блики на воде; при
24 px — только крупные формы.

Свет намеренно НЕ запекается: фон рисуется в нейтральном материале, а ночную
атмосферу и тёплый факел даёт Godot (`CanvasModulate` + `PointLight2D`).
Поэтому в наборе есть радиальный градиент света в собственном разрешении
каждого варианта.

    python tools/res_study/author_scene.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from res_study.form_render import (  # noqa: E402
    Canvas, hash_noise, ramp_rgb, sdf_capsule, sdf_ellipse, sdf_poly, sdf_round_box,
    smooth_union, union, value_noise,
)

OUT = ROOT / "game" / "experiments" / "res_study" / "art"
REPORTS = ROOT / "reports"

# Логическое разрешение и тайл для каждого варианта (задача 3.1c).
VARIANTS: dict[str, dict] = {
    "a": {"tile": 24, "cols": 20.0, "rows": 11.25},
    "b": {"tile": 32, "cols": 20.0, "rows": 11.25},
    "c": {"tile": 48, "cols": 20.0, "rows": 11.25},
}

# Раскладка в тайлах — общая для всех вариантов.
LAYOUT = {
    "izba": {"left": 0.0, "right": 8.6, "wall_top": 2.55, "wall_bottom": 6.35,
             "window": (3.1, 4.7, 3.55, 4.95)},
    "chapel": {"left": 12.6, "right": 20.0, "top": 1.45, "bottom": 6.15,
               "niche": (15.95, 17.15, 3.45, 5.85)},
    "roof": {"top": 0.55, "bottom": 2.55},
    "torch": {"x": 8.9, "base_y": 7.55, "flame_y": 5.35},
    "hero": {"x": 10.45, "feet_y": 9.62},
    "puddles": [(14.6, 8.75, 2.6, 0.62), (6.9, 9.05, 1.7, 0.42), (11.9, 10.5, 1.2, 0.3)],
    "barrel": (12.5, 7.35),
}


def _texture(fn):
    """Обёртка: текстурная функция получает холст и возвращает сдвиг индекса рампы."""
    return fn


def build(variant: str) -> dict:
    cfg = VARIANTS[variant]
    tile = cfg["tile"]
    width = int(round(cfg["cols"] * tile))
    height = int(round(cfg["rows"] * tile))
    canvas = Canvas(width, height)
    gx, gy = canvas.grid(1)
    px, py = canvas.grid(1)
    X = lambda t: t * tile  # noqa: E731
    Y = lambda t: t * tile  # noqa: E731
    detail = 0 if tile <= 24 else (1 if tile <= 32 else 2)

    # --- земля ------------------------------------------------------------
    # Крупная структура — очень мягкая, иначе земля превращается в камуфляж.
    base_noise = (value_noise(px, py, tile * 1.7, 11) * 0.6 +
                  value_noise(px, py, tile * 0.7, 5) * 0.4)
    rows = np.clip(2 + np.round(base_noise * 0.55).astype(np.int32), 2, 3)
    # мокрый тёмный след у основания построек — узкий, в одну ступень
    wet = np.clip(1.0 - np.abs(py - Y(6.65)) / (tile * 0.45), 0.0, 1.0)
    rows = np.clip(rows - (wet > 0.5).astype(np.int32), 0, 5)

    canvas.paint(lambda x, y: np.full_like(x, -1.0), "dirt", level=2)
    canvas.color = ramp_rgb("dirt")[rows].astype(np.float32)
    canvas.alpha[:] = True
    # мелкое зерно почвы: комочки и камешки, тем больше, чем крупнее тайл
    if detail >= 1:
        grain = hash_noise(px, py, 77)
        speck = (grain > (0.88 if detail == 2 else 0.94)) & (rows < 3)
        canvas.color[speck] = ramp_rgb("dirt")[np.minimum(rows[speck] + 1, 5)]
        grain2 = hash_noise(px, py, 91)
        dark = (grain2 > (0.92 if detail == 2 else 0.96)) & (rows > 1)
        canvas.color[dark] = ramp_rgb("dirt")[np.maximum(rows[dark] - 1, 0)]

    # солома/сор: короткие штрихи, количество растёт с детализацией
    for k in range((70, 130, 210)[detail]):
        h1 = float(hash_noise(np.array(k * 1.7), np.array(k * 2.3), 3))
        h2 = float(hash_noise(np.array(k * 3.1), np.array(k * 0.7), 9))
        cx_ = h1 * width
        cy_ = Y(6.9) + h2 * (height - Y(6.9))
        length = tile * (0.18 + 0.25 * h2)
        ang = (h1 - 0.5) * 1.4
        canvas.paint(lambda x, y, a=cx_, b=cy_, c=length, d=ang: sdf_capsule(
            x, y, a, b, a + c * np.cos(d), b + c * np.sin(d), 0.55, 0.4),
            "straw", level=3 if h2 > 0.5 else 2)
    # мелкие камни
    for k in range((6, 10, 16)[detail]):
        h1 = float(hash_noise(np.array(k * 4.1), np.array(k * 1.3), 21))
        h2 = float(hash_noise(np.array(k * 2.9), np.array(k * 3.7), 33))
        cx_ = h1 * width
        cy_ = Y(7.1) + h2 * (height - Y(7.4))
        r = tile * (0.06 + 0.05 * h1)
        canvas.paint(lambda x, y, a=cx_, b=cy_, rr=r: sdf_ellipse(x, y, a, b, rr, rr * 0.7),
                     "stone", ambient=0.2, radius=r * 1.4)

    # --- лужи -------------------------------------------------------------
    for (tx, ty, tw, th) in LAYOUT["puddles"]:
        cx_, cy_, rx_, ry_ = X(tx), Y(ty), X(tw) * 0.5, Y(th) * 0.5
        canvas.paint(lambda x, y, a=cx_, b=cy_, r1=rx_, r2=ry_: sdf_ellipse(
            x, y, a, b, r1, r2), "water", ambient=0.3, radius=ry_)
        # блик по верхнему краю воды
        canvas.paint(lambda x, y, a=cx_, b=cy_, r1=rx_, r2=ry_: sdf_capsule(
            x, y, a - r1 * 0.45, b - r2 * 0.45, a + r1 * 0.35, b - r2 * 0.5,
            0.55, 0.5), "water", level=4)

    # --- сруб (изба) ------------------------------------------------------
    iz = LAYOUT["izba"]
    log_h = Y(0.42)
    log_top = Y(iz["wall_top"])
    log_bottom = Y(iz["wall_bottom"])
    n_logs = int(round((log_bottom - log_top) / log_h))
    for i in range(n_logs):
        y0 = log_top + i * log_h + 0.5
        canvas.paint(lambda x, y, yy=y0: sdf_round_box(
            x, y, (X(iz["left"]) + X(iz["right"])) / 2, yy + log_h / 2,
            (X(iz["right"]) - X(iz["left"])) / 2, log_h / 2, log_h * 0.28),
            "wood", ambient=0.18, contrast=1.0, radius=log_h * 0.55)
        # тёмный шов между брёвнами
        canvas.paint(lambda x, y, yy=y0: sdf_capsule(
            x, y, X(iz["left"]), yy + log_h, X(iz["right"]), yy + log_h, 0.4, 0.4),
            "wood", level=0)
    # продольные волокна на брёвнах
    for k in range((0, 3, 6)[detail]):
        h = float(hash_noise(np.array(k * 5.3), np.array(1.1), 17))
        yy = log_top + (0.35 + 0.5 * h) * log_h + log_h * (k % 3)
        if yy > log_bottom - log_h * 0.3:
            continue
        canvas.paint(lambda x, y, y_at=yy, hh=h: sdf_capsule(
            x, y, X(iz["left"] + 0.3 + hh), y_at, X(iz["right"] - 0.4), y_at, 0.45, 0.35),
            "wood", level=1)
    # мох у основания
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, (X(iz["left"]) + X(iz["right"])) / 2, log_bottom + log_h * 0.15,
        (X(iz["right"]) - X(iz["left"])) / 2, log_h * 0.22, log_h * 0.1),
        "straw", level=1)

    # окно с тёплым светом
    wx0, wx1, wy0, wy1 = iz["window"]
    win = lambda x, y, a=wx0, b=wx1, c=wy0, d=wy1: sdf_round_box(  # noqa: E731
        x, y, (X(a) + X(b)) / 2, (Y(c) + Y(d)) / 2, (X(b) - X(a)) / 2, (Y(d) - Y(c)) / 2, 1.5)
    # тёмная колода вокруг окна и тень под наличником
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, (X(wx0) + X(wx1)) / 2, (Y(wy0) + Y(wy1)) / 2,
        (X(wx1) - X(wx0)) / 2 + tile * 0.10, (Y(wy1) - Y(wy0)) / 2 + tile * 0.10, 2.0),
        "wood", level=0)
    # тёплый свет в окне: приглушённый, не «фонарь»
    canvas.paint(win, "flame", ambient=0.30, contrast=0.55, radius=Y(0.55))
    # переплёт
    canvas.paint(lambda x, y: sdf_capsule(x, y, (X(wx0) + X(wx1)) / 2, Y(wy0),
                                         (X(wx0) + X(wx1)) / 2, Y(wy1), 0.5, 0.5),
                 "wood", level=1)
    canvas.paint(lambda x, y: sdf_capsule(x, y, X(wx0), (Y(wy0) + Y(wy1)) / 2,
                                         X(wx1), (Y(wy0) + Y(wy1)) / 2, 0.5, 0.5),
                 "wood", level=1)
    # резной наличник
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, (X(wx0) + X(wx1)) / 2, Y(wy0) - tile * 0.09,
        (X(wx1) - X(wx0)) / 2 + tile * 0.12, tile * 0.06, 0.6), "wood_light", level=2)

    # --- кровля -----------------------------------------------------------
    rf = LAYOUT["roof"]
    canvas.paint(lambda x, y: sdf_poly(x, y, [
        (X(iz["left"]) - tile * 0.3, Y(rf["bottom"])),
        (X(iz["left"]) + tile * 0.3, Y(rf["top"])),
        (X(iz["right"]) - tile * 0.2, Y(rf["top"])),
        (X(iz["right"]) + tile * 0.4, Y(rf["bottom"])),
    ]), "wood", ambient=0.12, contrast=0.9, radius=Y(0.5))
    # дранка: поперечные полосы тёмных швов
    shingle = Y(0.30)
    y_sh = Y(rf["top"]) + shingle
    while y_sh < Y(rf["bottom"]):
        canvas.paint(lambda x, y, yy=y_sh: sdf_capsule(
            x, y, X(iz["left"]), yy, X(iz["right"]), yy, 0.45, 0.45), "wood", level=0)
        y_sh += shingle
    if detail >= 1:
        # светлый гребень кровли
        canvas.paint(lambda x, y: sdf_capsule(
            x, y, X(iz["left"]) + tile * 0.4, Y(rf["top"]) + 1, X(iz["right"]) - tile * 0.1,
            Y(rf["top"]) + 1, 0.6, 0.6), "wood_light", level=3)

    # --- белокаменная часовня --------------------------------------------
    ch = LAYOUT["chapel"]
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, (X(ch["left"]) + X(ch["right"])) / 2, (Y(ch["top"]) + Y(ch["bottom"])) / 2,
        (X(ch["right"]) - X(ch["left"])) / 2, (Y(ch["bottom"]) - Y(ch["top"])) / 2, 1.5),
        "stone", ambient=0.12, contrast=0.70, radius=Y(1.4))
    # кладка: ряды блоков со смещением
    block_h = Y(0.62) if detail >= 1 else Y(0.8)
    row = 0
    y_b = Y(ch["top"]) + block_h
    while y_b < Y(ch["bottom"]):
        canvas.paint(lambda x, y, yy=y_b: sdf_capsule(
            x, y, X(ch["left"]), yy, X(ch["right"]), yy, 0.45, 0.45), "stone", level=0)
        # вертикальные швы со смещением через ряд
        x_b = X(ch["left"]) + (1.1 + (0.55 if row % 2 else 0.0)) * tile
        while x_b < X(ch["right"]) - tile * 0.3:
            canvas.paint(lambda x, y, xx=x_b, yy=y_b, hh=block_h: sdf_capsule(
                x, y, xx, yy - hh, xx, yy, 0.4, 0.4), "stone", level=0)
            x_b += 1.1 * tile
        y_b += block_h
        row += 1
    if detail >= 1:
        # выветривание: тёмные потёки
        for k in range((0, 4, 9)[detail]):
            h = float(hash_noise(np.array(k * 3.7), np.array(2.1), 41))
            xx = X(ch["left"] + 0.6 + h * 6.4)
            canvas.paint(lambda x, y, x_at=xx, hh=h: sdf_capsule(
                x, y, x_at, Y(ch["top"] + 0.4), x_at, Y(ch["top"] + 1.2 + hh * 1.6),
                0.45, 0.35), "stone", level=1)
    # ниша с аркой: тёмный проём и слабый тёплый отсвет у порога
    n0, n1, ny0, ny1 = ch["niche"]
    arch_r = (X(n1) - X(n0)) / 2
    canvas.paint(lambda x, y: union(
        sdf_round_box(x, y, (X(n0) + X(n1)) / 2, (Y(ny0) + Y(ny1)) / 2 + arch_r * 0.35,
                      arch_r, (Y(ny1) - Y(ny0)) / 2 - arch_r * 0.35, arch_r * 0.35),
        sdf_ellipse(x, y, (X(n0) + X(n1)) / 2, Y(ny0) + arch_r * 0.6, arch_r, arch_r * 0.75),
    ), "wood", ambient=0.10, contrast=0.5, radius=arch_r)
    # свеча у порога: маленькое тёплое пятно, а не «фонарь» на всю нишу
    canvas.paint(lambda x, y: sdf_ellipse(
        x, y, (X(n0) + X(n1)) / 2, Y(ny1) - arch_r * 0.22, arch_r * 0.26, arch_r * 0.20),
        "flame", ambient=0.30, contrast=0.6, radius=arch_r * 0.3)
    canvas.paint(lambda x, y: sdf_capsule(
        x, y, (X(n0) + X(n1)) / 2, Y(ny1) - arch_r * 0.30, (X(n0) + X(n1)) / 2,
        Y(ny1) - arch_r * 0.16, 0.6, 0.5), "flame", level=5)
    # архивольт: узкая светлая кромка по дуге
    canvas.paint(lambda x, y: np.abs(sdf_ellipse(
        x, y, (X(n0) + X(n1)) / 2, Y(ny0) + arch_r * 0.6, arch_r * 1.06, arch_r * 0.82)
    ) - tile * 0.03, "stone", ambient=0.42, contrast=0.5, radius=tile * 0.08)
    # камни у входа
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, (X(n0) + X(n1)) / 2, Y(ch["bottom"]) + tile * 0.18,
        arch_r * 1.15, tile * 0.18, 1.0), "stone", ambient=0.24, radius=Y(0.4))

    # --- факельный столб --------------------------------------------------
    tf = LAYOUT["torch"]
    post_r = tile * 0.16
    canvas.paint(lambda x, y: sdf_capsule(
        x, y, X(tf["x"]), Y(tf["base_y"]), X(tf["x"]), Y(tf["flame_y"]) + tile * 0.45,
        post_r, post_r * 0.8), "wood", ambient=0.2, radius=post_r)
    # железная чаша
    canvas.paint(lambda x, y: sdf_poly(x, y, [
        (X(tf["x"]) - tile * 0.26, Y(tf["flame_y"]) + tile * 0.30),
        (X(tf["x"]) + tile * 0.26, Y(tf["flame_y"]) + tile * 0.30),
        (X(tf["x"]) + tile * 0.16, Y(tf["flame_y"]) + tile * 0.62),
        (X(tf["x"]) - tile * 0.16, Y(tf["flame_y"]) + tile * 0.62),
    ]), "metal", ambient=0.22, radius=tile * 0.2)
    # пламя: три вложенные формы
    fy = Y(tf["flame_y"]) + tile * 0.22
    for (rx, ry, ramp, lvl) in [(0.30, 0.52, "flame", 2), (0.21, 0.38, "flame", 3),
                                (0.12, 0.24, "flame", 5)]:
        canvas.paint(lambda x, y, r1=rx * tile, r2=ry * tile, yy=fy: sdf_ellipse(
            x, y, X(tf["x"]), yy, r1, r2), ramp, level=lvl)
    canvas.paint(lambda x, y: sdf_ellipse(x, y, X(tf["x"]), fy - tile * 0.06,
                                         tile * 0.06, tile * 0.10), "flame", level=5)

    # --- бочка ------------------------------------------------------------
    bx, by = LAYOUT["barrel"]
    barrel_r = tile * 0.34
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, X(bx), Y(by), barrel_r, barrel_r * 1.15, barrel_r * 0.45),
        "wood_light", ambient=0.2, radius=barrel_r)
    for k in (-0.45, 0.0, 0.45):
        canvas.paint(lambda x, y, o=k: sdf_capsule(
            x, y, X(bx) + o * barrel_r * 2, Y(by) - barrel_r,
            X(bx) + o * barrel_r * 2, Y(by) + barrel_r, 0.45, 0.45), "metal", level=1)

    # --- контактная тень героя и построек --------------------------------
    hx = X(LAYOUT["hero"]["x"])
    hy = Y(LAYOUT["hero"]["feet_y"])
    shadow = sdf_ellipse(gx, gy, hx, hy - tile * 0.12, tile * 0.42, tile * 0.16)
    dark = ramp_rgb("dirt")[0] * 0.55
    sel = shadow <= 0
    canvas.color[sel] = np.minimum(canvas.color[sel], dark)
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, (X(iz["left"]) + X(iz["right"])) / 2, Y(iz["wall_bottom"]) + tile * 0.22,
        (X(iz["right"]) - X(iz["left"])) / 2, tile * 0.22, tile * 0.1),
        "dirt", level=0)
    canvas.paint(lambda x, y: sdf_round_box(
        x, y, (X(ch["left"]) + X(ch["right"])) / 2, Y(ch["bottom"]) + tile * 0.26,
        (X(ch["right"]) - X(ch["left"])) / 2, tile * 0.2, tile * 0.1),
        "dirt", level=0)

    target = OUT / variant / f"world_{tile}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.to_image().save(target)

    # --- градиент света факела (в собственном разрешении) ----------------
    light_px = int(round(10 * tile))
    yy, xx = np.meshgrid(np.arange(light_px) + 0.5, np.arange(light_px) + 0.5, indexing="ij")
    cx_l = cy_l = light_px / 2
    dist = np.sqrt((xx - cx_l) ** 2 + (yy - cy_l) ** 2) / (light_px / 2)
    falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 1.6
    rgba = np.zeros((light_px, light_px, 4), dtype=np.uint8)
    rgba[..., 0] = 255
    rgba[..., 1] = 255
    rgba[..., 2] = 255
    rgba[..., 3] = np.clip(falloff * 255, 0, 255).astype(np.uint8)
    light_path = OUT / variant / f"light_torch_{tile}.png"
    Image.fromarray(rgba, "RGBA").save(light_path)

    data = {
        "variant": variant,
        "tile": tile,
        "viewport": [width, height],
        "content_scale": {0: 4, 1: 3, 2: 2}[detail],
        "hero_png": f"hero_down_{48 if variant == 'a' else (64 if variant == 'b' else 96)}.png",
        "hero_pos": [LAYOUT["hero"]["x"] * tile, LAYOUT["hero"]["feet_y"] * tile],
        "hero_height": {0: 48, 1: 64, 2: 96}[detail],
        # масштаб спрайта в логических координатах ВСЕГДА 1.0: увеличение делает
        # content_scale логического разрешения, иначе масштаб применяется дважды
        "hero_scale": 1,
        "hero_screen_height": {0: 48 * 4, 1: 64 * 3, 2: 96 * 2}[detail],
        "light_png": f"light_torch_{tile}.png",
        "light_pos": [LAYOUT["torch"]["x"] * tile, (LAYOUT["torch"]["flame_y"] + 0.22) * tile],
        "light_scale": 1.0,
        "world_png": f"world_{tile}.png",
    }
    print(f"{variant.upper()} {width}x{height} тайл {tile}px → "
          f"{target.relative_to(ROOT).as_posix()}")
    return data


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    layout = {v: build(v) for v in VARIANTS}
    path = OUT / "layout.json"
    path.write_text(json.dumps(layout, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"layout: {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
