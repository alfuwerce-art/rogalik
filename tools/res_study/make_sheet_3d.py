"""Сравнительный лист задачи 3.1d: новый герой 3/4 против утверждённого референса.

Собирает:
  * утверждённый образ героя (front/back) и вырезку героя из look-референса
    (именно игровой ракурс three-quarter — что и было целью);
  * два реальных кадра Godot 1920×1080: герой 48 px (логическое 480×270, 4×)
    и 96 px (960×540, 2×) — на экране оба 192 px;
  * фрагменты 1:1 вокруг героя (без масштабирования) и сами спрайты ×4;
  * динамический свет: кадр со светом и без него.

    python tools/res_study/make_sheet_3d.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
ART = ROOT / "game" / "experiments" / "res_study" / "art"
BG = (20, 18, 22)
FG = (236, 230, 218)
DIM = (156, 148, 136)
WARN = (232, 176, 92)

FONTS = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONTS:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def frame(tag: str) -> Image.Image:
    return Image.open(REPORTS / f"stage3d_{tag}_1920.png").convert("RGB")


def main() -> int:
    layout = json.loads((ART / "layout.json").read_text(encoding="utf-8"))
    ref = Image.open(ROOT / "assets" / "references" / "hero" /
                     "hero_reference_front_back.png").convert("RGB")
    look = Image.open(ROOT / "assets" / "references" / "gameplay" /
                      "gameplay_look_reference.png").convert("RGB")
    look_hero = look.crop((660, 395, 800, 600))

    f_title, f_head, f_body, f_small = font(26), font(19), font(15), font(13)
    pad = 22
    thumb_w, thumb_h = 520, 293
    crop_w, crop_h = 420, 360
    width = 1340
    height = 1770
    sheet = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(sheet)

    y = 14
    d.text((pad, y), "ROGALIK — 3.1d: герой в ракурсе three-quarter top-down",
           fill=FG, font=f_title)
    y += 36
    d.text((pad, y), "Слева — утверждённый образ и герой из look-референса (тот же ракурс). "
                     "Справа — варианты 48 и 96 px в реальных кадрах Godot 1920×1080.",
           fill=DIM, font=f_body)
    y += 30

    # --- референсы --------------------------------------------------------
    ref_h = 300
    ref_w = int(ref_h * ref.width / ref.height)
    sheet.paste(ref.resize((ref_w, ref_h), Image.LANCZOS), (pad, y))
    d.text((pad, y + ref_h + 4), "Утверждённый герой (D7): front/back", fill=FG, font=f_body)

    look_h = 300
    look_w = int(look_h * look_hero.width / look_hero.height)
    lx = pad + ref_w + 30
    sheet.paste(look_hero.resize((look_w, look_h), Image.LANCZOS), (lx, y))
    d.text((lx, y + look_h + 4), "Герой в игровом look-референсе: камера сверху, "
                                 "только клин лица", fill=FG, font=f_body)

    tx = lx + look_w + 40
    notes = [
        ("Что взять из ракурса:", FG, f_body),
        ("• голова читается СВЕРХУ: масса волос,", DIM, f_small),
        ("  пробор, блик на макушке;", DIM, f_small),
        ("• повязка лежит по передней нижней части", DIM, f_small),
        ("  головы, а не по лбу фронтального портрета;", DIM, f_small),
        ("• лицо — узкий клин: нос, скула, челюсть;", DIM, f_small),
        ("• плечи широкие, видны сверху, корпус сжат;", DIM, f_small),
        ("• тёплый свет слева, холодная кромка справа;", DIM, f_small),
        ("• тень падает на землю и уходит от источника.", DIM, f_small),
    ]
    ny = y
    for text, colour, fnt in notes:
        d.text((tx, ny), text, fill=colour, font=fnt)
        ny += 20
    y += ref_h + 34

    # --- кадры ------------------------------------------------------------
    for index, tag in enumerate(("48", "96")):
        x = pad + index * (thumb_w + pad)
        img = frame(tag)
        sheet.paste(img.resize((thumb_w, thumb_h), Image.NEAREST), (x, y))
        d.rectangle([x, y, x + thumb_w - 1, y + thumb_h - 1], outline=(60, 54, 48))
        info = layout[f"hero34_{tag}"]
        d.text((x, y + thumb_h + 5),
               f"{tag} px исходник → {info['content_scale']}× → 192 px на экране 1920×1080; "
               f"логическое {info['viewport'][0]}×{info['viewport'][1]}", fill=FG, font=f_body)
    y += thumb_h + 30

    # --- фрагменты 1:1 и спрайты -----------------------------------------
    d.text((pad, y), "Фрагменты 1:1 вокруг героя (без масштабирования) и сами спрайты ×4",
           fill=FG, font=f_head)
    y += 28
    centers = {}
    for tag in ("48", "96"):
        img = frame(tag)
        info = layout[f"hero34_{tag}"]
        hx, hy = info["hero_pos"]
        scale = info["content_scale"]
        # экранные координаты героя и центр силуэта
        cx = int(hx * scale)
        cy = int((hy - info["hero_height"] * 0.5) * scale)
        centers[tag] = (cx, cy)
        box = (cx - crop_w // 2, cy - crop_h // 2, cx + crop_w // 2, cy + crop_h // 2)
        sheet.paste(img.crop(box), (pad + (0 if tag == "48" else crop_w + pad), y))
        d.rectangle([pad + (0 if tag == "48" else crop_w + pad), y,
                     pad + (0 if tag == "48" else crop_w + pad) + crop_w - 1, y + crop_h - 1],
                    outline=(60, 54, 48))
    d.text((pad, y + crop_h + 4),
           f"1 экранный пиксель = 1/4 исходного (48 px)", fill=DIM, font=f_small)
    d.text((pad + crop_w + pad, y + crop_h + 4),
           f"1 экранный пиксель = 1/2 исходного (96 px)", fill=DIM, font=f_small)

    # спрайты ×4 справа
    sx = pad + crop_w * 2 + pad * 2
    sy = y
    for tag in ("48", "96"):
        sprite = Image.open(ART / "hero34" / f"hero34_{tag}.png").convert("RGBA")
        sprite = sprite.crop(sprite.getbbox())
        factor = 4 if tag == "48" else 2
        big = sprite.resize((sprite.width * factor, sprite.height * factor), Image.NEAREST)
        sheet.paste(big, (sx, sy), big)
        d.text((sx, sy + big.height + 3), f"{tag} px ×{factor}", fill=DIM, font=f_small)
        sx += big.width + 26
    y += crop_h + 30

    # --- динамический свет -----------------------------------------------
    d.text((pad, y), "Динамический свет и настоящая тень от факела "
                     "(PointLight2D + LightOccluder2D по альфе спрайта)",
           fill=FG, font=f_head)
    y += 28
    for index, (path, label) in enumerate([
            ("stage3d_96_1920_nolight.png", "без света: только ночная тонировка"),
            ("stage3d_96_1920.png", "с факелом: тёплый свет и падающая тень героя")]):
        img = Image.open(REPORTS / path).convert("RGB")
        cx, cy = centers["96"]
        box = (cx - crop_w // 2, cy - crop_h // 2, cx + crop_w // 2, cy + crop_h // 2)
        x = pad + index * (crop_w + pad)
        sheet.paste(img.crop(box), (x, y))
        d.rectangle([x, y, x + crop_w - 1, y + crop_h - 1], outline=(60, 54, 48))
        d.text((x, y + crop_h + 4), label, fill=DIM, font=f_small)
    y += crop_h + 36

    # --- вердикт ---------------------------------------------------------
    verdict = [
        ("REFERENCE_FIDELITY_GATE (самооценка агента, не приёмка владельца)", FG, f_head),
        ("48 px — NO: ракурс и пропорции стали верными, но лицо, кисти, волосы и ткань\n"
         "остаются схемой; силуэт читается как «фигурка», а не как персонаж.", WARN, f_body),
        ("96 px — NO: деталей больше (пробор, витки обмоток, пальцы, шрамы), но\n"
         "художественный язык референса не достигнут: нет вылепленной анатомии и лица.",
         WARN, f_body),
        ("Три крупнейших расхождения: (1) анатомия — мышцы нарисованы линиями, а не объёмом;\n"
         "(2) лицо и кисти — минимальны, нет характера; (3) ткань и волосы не ведут себя как\n"
         "материал: нет складок по форме и прядей с направлением.", DIM, f_body),
    ]
    for text, colour, fnt in verdict:
        d.text((pad, y), text, fill=colour, font=fnt)
        y += 20 + text.count("\n") * 19

    path = REPORTS / "stage3d_compare_sheet.png"
    sheet.crop((0, 0, width, min(height, y + 16))).save(path)
    print(f"sheet: {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
