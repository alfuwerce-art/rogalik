"""Сборка сравнительных листов и проверок для исследования разрешений (3.1c).

1. `reports/stage3c_compare_sheet.png` — большой лист: утверждённый референс
   героя, look-референс Rogalik, три кадра 1920×1080 из реального Godot и
   фрагменты одного и того же участка экрана в трёх вариантах.
2. `reports/stage3c_hero_scale_sheet.png` — герой A/B/C в одинаковом экранном
   масштабе и его исходные пиксели ×4.
3. `reports/stage3c_light_demo.png` — динамический свет и тот же кадр без него.
4. `reports/stage3c_checks.json` — размеры, одинаковое поле зрения и высота
   героя на экране, отсутствие полупрозрачных пикселей в игровых ассетах.

    python tools/res_study/make_sheet.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
ART = ROOT / "game" / "experiments" / "res_study" / "art"
LAYOUT = json.loads((ART / "layout.json").read_text(encoding="utf-8"))

VARIANTS = ["a", "b", "c"]
BG = (18, 16, 20)
FG = (236, 230, 218)
DIM = (158, 150, 138)
WARN = (230, 170, 90)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def frame_path(variant: str, suffix: str = "") -> Path:
    return REPORTS / f"stage3c_{variant.upper()}_1920{suffix}.png"


def sheet_compare() -> Path:
    ref_hero = Image.open(ROOT / "assets" / "references" / "hero" /
                          "hero_reference_front_back.png").convert("RGB")
    ref_look = Image.open(ROOT / "assets" / "references" / "gameplay" /
                          "gameplay_look_reference.png").convert("RGB")
    frames = {v: Image.open(frame_path(v)).convert("RGB") for v in VARIANTS
              if frame_path(v).is_file()}

    f_title, f_head, f_body, f_small = font(26), font(18), font(15), font(13)
    pad = 20
    thumb_w = 620
    thumb_h = int(thumb_w * 1080 / 1920)
    crop_w, crop_h = 470, 330

    ref_w = 250
    ref_h = int(ref_w * ref_hero.height / ref_hero.width)
    look_h = 168
    look_w = int(look_h * ref_look.width / ref_look.height)

    col_w = max(thumb_w, crop_w)
    width = pad + (col_w + pad) * 3
    y_title = 16
    y_sub = y_title + 34
    y_refs = y_sub + 34
    refs_h = max(ref_h, look_h) + 24
    y_frames_label = y_refs + refs_h + 18
    y_frames = y_frames_label + 28
    y_crops_label = y_frames + thumb_h + 42
    y_crops = y_crops_label + 28
    height = y_crops + crop_h + 60

    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, y_title), "ROGALIK — исследование разрешений 3.1c: один кадр, три исходных "
                             "разрешения", fill=FG, font=f_title)
    draw.text((pad, y_sub),
              "A: 480×270 / тайл 24 px / герой 48 px (4×)     "
              "B: 640×360 / тайл 32 px / герой 64 px (3×)     "
              "C: 960×540 / тайл 48 px / герой 96 px (2×)", fill=DIM, font=f_body)

    # референсы: герой и look-референс в один ряд
    sheet.paste(ref_hero.resize((ref_w, ref_h), Image.LANCZOS), (pad, y_refs))
    draw.text((pad + ref_w + 14, y_refs), "Утверждённый образ героя (D7)", fill=FG, font=f_head)
    draw.text((pad + ref_w + 14, y_refs + 24),
              "assets/references/hero/hero_reference_front_back.png", fill=DIM, font=f_small)
    draw.text((pad + ref_w + 14, y_refs + 44),
              "Цель: объёмная анатомия, отдельные пряди волос, красная", fill=DIM, font=f_small)
    draw.text((pad + ref_w + 14, y_refs + 62),
              "повязка, широкие рваные штаны, кушак, льняные обмотки,", fill=DIM, font=f_small)
    draw.text((pad + ref_w + 14, y_refs + 80), "босые стопы.", fill=DIM, font=f_small)

    look_x = pad + ref_w + 420
    sheet.paste(ref_look.resize((look_w, look_h), Image.LANCZOS), (look_x, y_refs))
    draw.text((look_x + look_w + 14, y_refs), "Игровой look-референс Rogalik", fill=FG, font=f_head)
    draw.text((look_x + look_w + 14, y_refs + 24),
              "assets/references/gameplay/gameplay_look_reference.png", fill=DIM, font=f_small)
    draw.text((look_x + look_w + 14, y_refs + 44),
              "Цель: живописный объём, материалы (дерево, белый камень,", fill=DIM, font=f_small)
    draw.text((look_x + look_w + 14, y_refs + 62),
              "мокрая земля), тёплый факел против холодного тумана.", fill=DIM, font=f_small)

    # кадры
    draw.text((pad, y_frames_label),
              "Кадры сняты реальным запуском Godot 4.7.2 в окне 1920×1080 "
              "(--variant=a|b|c, --shot), без масштабирования при вставке.",
              fill=DIM, font=f_body)
    for index, variant in enumerate(VARIANTS):
        x = pad + index * (col_w + pad)
        if variant not in frames:
            continue
        sheet.paste(frames[variant].resize((thumb_w, thumb_h), Image.NEAREST), (x, y_frames))
        draw.rectangle([x, y_frames, x + thumb_w - 1, y_frames + thumb_h - 1],
                       outline=(62, 56, 50))
        info = LAYOUT[variant]
        draw.text((x, y_frames + thumb_h + 6),
                  f"{variant.upper()} — логическое {info['viewport'][0]}×{info['viewport'][1]}, "
                  f"тайл {info['tile']} px, герой {info['hero_height']} px "
                  f"= {info['hero_screen_height']} px на экране", fill=FG, font=f_body)

    # фрагменты одного и того же участка экрана — с центром на герое
    boxes = [hero_bbox_from_diff(v) for v in VARIANTS]
    centers = [((b["hero_bbox_screen"][0] + b["hero_bbox_screen"][2]) // 2,
                (b["hero_bbox_screen"][1] + b["hero_bbox_screen"][3]) // 2)
               for b in boxes if b]
    cx = int(sum(c[0] for c in centers) / len(centers)) if centers else 960
    cy = int(sum(c[1] for c in centers) / len(centers)) if centers else 540
    draw.text((pad, y_crops_label),
              "Один и тот же участок экрана 1:1 (без масштабирования), центр — на герое: видно, "
              "из какого размера исходных пикселей собран кадр", fill=DIM, font=f_body)
    for index, variant in enumerate(VARIANTS):
        x = pad + index * (col_w + pad)
        if variant not in frames:
            continue
        box = (max(0, cx - crop_w // 2), max(0, cy - crop_h // 2),
               max(0, cx - crop_w // 2) + crop_w, max(0, cy - crop_h // 2) + crop_h)
        sheet.paste(frames[variant].crop(box), (x, y_crops))
        draw.rectangle([x, y_crops, x + crop_w - 1, y_crops + crop_h - 1],
                       outline=(62, 56, 50))
        draw.text((x, y_crops + crop_h + 6),
                  f"{variant.upper()}: 1 экранный пиксель = 1/{LAYOUT[variant]['content_scale']} "
                  f"исходного", fill=DIM, font=f_small)

    path = REPORTS / "stage3c_compare_sheet.png"
    sheet.save(path)
    return path


def sheet_hero_scale() -> Path:
    tiles = []
    for variant in VARIANTS:
        info = LAYOUT[variant]
        img = Image.open(ART / variant / info["hero_png"]).convert("RGBA")
        img = img.crop(img.getbbox())
        screen = img.resize((img.width * info["content_scale"],
                             img.height * info["content_scale"]), Image.NEAREST)
        raw = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
        tiles.append((variant, int(info["hero_height"]), screen, raw))

    f_head, f_body = font(18), font(14)
    pad = 24
    screen_w = max(t[2].width for t in tiles)
    raw_w = max(t[3].width for t in tiles)
    width = pad * 2 + screen_w * 3 + pad * 2 + raw_w * 3
    height = max(t[2].height for t in tiles) + 120
    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 14), "Герой: одинаковый экранный масштаб (слева) и исходные пиксели ×4 "
                         "(справа)", fill=FG, font=f_head)
    x = pad
    for variant, height_px, screen, _raw in tiles:
        draw.text((x, 46), f"{variant.upper()} — {height_px} px исходник", fill=FG, font=f_body)
        sheet.paste(screen, (x, 70), screen)
        x += screen_w + pad
    x += pad
    for variant, height_px, _screen, raw in tiles:
        draw.text((x, 46), f"{variant.upper()} ×4", fill=DIM, font=f_body)
        sheet.paste(raw, (x, 70), raw)
        x += raw_w + pad
    path = REPORTS / "stage3c_hero_scale_sheet.png"
    sheet.save(path)
    return path


def sheet_light() -> Path:
    on, off = frame_path("a"), frame_path("a", "_nolight")
    if not (on.is_file() and off.is_file()):
        return Path()
    box = (560, 300, 1560, 880)
    crop_on = Image.open(on).convert("RGB").crop(box)
    crop_off = Image.open(off).convert("RGB").crop(box)
    w, h = crop_on.size
    f_head, f_body = font(20), font(14)
    sheet = Image.new("RGB", (w * 2 + 60, h + 90), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 14), "Динамический свет Rogalik: PointLight2D факела на логическом разрешении "
                        "480×270", fill=FG, font=f_head)
    sheet.paste(crop_off, (20, 66))
    sheet.paste(crop_on, (w + 40, 66))
    draw.text((20, 44), "без света (только CanvasModulate)", fill=DIM, font=f_body)
    draw.text((w + 40, 44),
              "с факелом: тёплый свет ложится на сруб, землю и героя", fill=DIM, font=f_body)
    path = REPORTS / "stage3c_light_demo.png"
    sheet.save(path)
    return path


def hero_bbox_from_diff(variant: str) -> dict | None:
    """Точный замер силуэта героя: разница кадра с героем и кадра без него.

    Это объективная проверка «высота героя на экране одинакова»: сравниваются
    два кадра одного и того же варианта, различающиеся только спрайтом героя.
    """
    with_hero = frame_path(variant)
    without = frame_path(variant, "_nohero")
    if not (with_hero.is_file() and without.is_file()):
        return None
    a = np.asarray(Image.open(with_hero).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(without).convert("RGB"), dtype=np.int16)
    diff = np.abs(a - b).sum(axis=2) > 6
    ys, xs = np.where(diff)
    if len(ys) == 0:
        return None
    return {"hero_bbox_screen": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "hero_height_screen_measured": int(ys.max() - ys.min() + 1),
            "hero_width_screen_measured": int(xs.max() - xs.min() + 1),
            "diff_pixels": int(diff.sum())}


def checks() -> dict:
    report: dict = {"variants": {}, "problems": []}
    for variant in VARIANTS:
        path = frame_path(variant)
        entry: dict = {"expected_view": LAYOUT[variant]["viewport"],
                       "tile": LAYOUT[variant]["tile"],
                       "hero_height": LAYOUT[variant]["hero_height"],
                       "hero_screen_height_expected": LAYOUT[variant]["hero_screen_height"],
                       "fov_tiles": [LAYOUT[variant]["viewport"][0] / LAYOUT[variant]["tile"],
                                     LAYOUT[variant]["viewport"][1] / LAYOUT[variant]["tile"]]}
        if not path.is_file():
            entry["problem"] = "нет кадра"
            report["problems"].append(f"{variant}: нет кадра {path.name}")
            report["variants"][variant] = entry
            continue
        image = Image.open(path).convert("RGB")
        entry["size"] = list(image.size)
        if image.size != (1920, 1080):
            report["problems"].append(f"{variant}: кадр {image.size} вместо 1920×1080")
        measured = hero_bbox_from_diff(variant)
        if measured is None:
            report["problems"].append(f"{variant}: нет кадра без героя для замера силуэта")
        else:
            entry.update(measured)
            # Допуск: крайние ряды спрайта — почти чёрный контур, он совпадает с
            # ночным фоном и в разнице кадров не детектируется. Замер поэтому
            # даёт нижнюю границу (≈188 из 192 px), а высота по построению
            # равна hero_height × content_scale и проверяется логом запуска.
            expected = LAYOUT[variant]["hero_screen_height"]
            tolerance = 10
            entry["hero_screen_height_expected"] = expected
            if abs(measured["hero_height_screen_measured"] - expected) > tolerance:
                report["problems"].append(
                    f"{variant}: измеренная высота героя "
                    f"{measured['hero_height_screen_measured']} px вне допуска "
                    f"{expected}±{tolerance} px")
        for name in (LAYOUT[variant]["world_png"], LAYOUT[variant]["hero_png"]):
            asset = Image.open(ART / variant / name).convert("RGBA")
            alpha = np.asarray(asset)[..., 3]
            semi = int(((alpha > 0) & (alpha < 255)).sum())
            entry[f"asset_{name}"] = {"size": list(asset.size), "semi_transparent_px": semi}
            if semi:
                report["problems"].append(f"{variant}/{name}: {semi} полупрозрачных пикселей")
        report["variants"][variant] = entry

    fovs = {tuple(round(x, 3) for x in (e.get("fov_tiles") or []))
            for e in report["variants"].values()}
    report["all_variants_same_fov"] = len(fovs) == 1
    heights = sorted({e.get("hero_height_screen_measured")
                      for e in report["variants"].values() if e.get("hero_height_screen_measured")})
    report["hero_screen_heights_measured"] = heights
    report["hero_screen_height_identical"] = (
        len(heights) <= 1 or (max(heights) - min(heights)) <= 2)
    report["status"] = "PASS" if not report["problems"] else "FAIL"
    return report


def main() -> int:
    sheet = sheet_compare()
    hero_sheet = sheet_hero_scale()
    light = sheet_light()
    report = checks()
    (REPORTS / "stage3c_checks.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"sheet: {sheet.relative_to(ROOT).as_posix()}")
    print(f"hero:  {hero_sheet.relative_to(ROOT).as_posix()}")
    if light.parts:
        print(f"light: {light.relative_to(ROOT).as_posix()}")
    print(f"checks: status={report['status']} same_fov={report['all_variants_same_fov']} "
          f"hero_screen_heights={report.get('hero_screen_heights_measured')} "
          f"problems={len(report['problems'])}")
    for problem in report["problems"]:
        print("  -", problem)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
