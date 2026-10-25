"""Сравнительный лист задачи 3.1e.

Все фигуры приведены к ОДНОЙ высоте — 192 px, то есть ровно к тому размеру,
который герой занимает на экране 1920×1080 при масштабе эксперимента
(96 px × 2 и 48 px × 4). Высота нормируется по ИЗМЕРЕННОМУ силуэту, а не по
размеру файла: иначе прозрачные поля спрайта и поля референса давали бы
нечестное сравнение.

Панели:
  1. утверждённый референс D7 (живописный, не пиксельный);
  2. герой 3.1d, 96 px (предыдущая версия, гейт NO);
  3. новый мастер-образ 3.1e, 96 px;
  4. новый мастер-образ 3.1e, 48 px (производственный размер D16);
  5. реальный кадр Godot (факел, динамическая тень) — 1:1.
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS = os.path.join(ROOT, "reports")

BG = (18, 16, 22)
PANEL_BG = (26, 24, 32)
TEXT = (226, 220, 210)
DIM = (150, 144, 136)
ACCENT = (206, 79, 52)
FLOOR = (74, 68, 78)

FIGURE_H = 192
PANEL_W = 236
PANEL_H = 268
LABEL_H = 44
GAP = 14

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def silhouette(image: Image.Image) -> Image.Image:
    """Обрезка по измеренному силуэту: альфа для спрайтов, отличие от фона для живописи."""
    if image.mode == "RGBA":
        mask = np.array(image)[:, :, 3] > 0
    else:
        arr = np.array(image.convert("RGB")).astype(int)
        border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
        bg = np.median(border, axis=0)
        mask = (np.abs(arr - bg).max(axis=2) > 22)
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    box = (int(cols.min()), int(rows.min()), int(cols.max()) + 1,
           int(rows.max()) + 1)
    return image.crop(box)


def to_height(image: Image.Image, target_h: int) -> Image.Image:
    ratio = target_h / image.height
    width = max(1, round(image.width * ratio))
    return image.resize((width, target_h), Image.NEAREST)


def panels() -> list[tuple[str, str, Image.Image]]:
    items: list[tuple[str, str, Image.Image]] = []

    ref = os.path.join(ROOT, "assets", "references", "hero",
                       "hero_reference_front_back.png")
    with Image.open(ref) as im:
        front = im.convert("RGB").crop((250, 8, 700, 1010))   # вид спереди
    items.append(("РЕФЕРЕНС D7", "утверждённая внешность", to_height(silhouette(front), FIGURE_H)))

    old = os.path.join(ROOT, "game", "experiments", "res_study", "art",
                       "hero34", "hero34_96.png")
    with Image.open(old) as im:
        items.append(("3.1d · 96 px", "предыдущая версия · гейт NO",
                      to_height(silhouette(im.convert("RGBA")), FIGURE_H)))

    for height in (96, 48):
        path = os.path.join(ROOT, "game", "experiments", "res_study", "art",
                            "hero_master", f"hero_master_{height}.png")
        with Image.open(path) as im:
            items.append((f"3.1e · {height} px", "новый мастер-образ",
                          to_height(silhouette(im.convert("RGBA")), FIGURE_H)))

    # кадр Godot: координаты из layout.json — ступни на логическом y=461.76,
    # окно 1920×1080, content_scale 2× → экранные (1003, 923), рост 192 px.
    shot = os.path.join(REPORTS, "stage3e_game_hero_master_96.png")
    with Image.open(shot) as im:
        frame = im.convert("RGB").crop((1003 - 52, 923 - FIGURE_H - 4,
                                        1003 + 52, 923 + 6))
    items.append(("КАДР GODOT", "факел · динамическая тень · 1:1",
                  to_height(frame, FIGURE_H)))
    return items


def main() -> int:
    items = panels()
    width = GAP + len(items) * (PANEL_W + GAP)
    height = GAP + 34 + LABEL_H + PANEL_H + GAP + 44
    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    head = font(24)
    name = font(16)
    small = font(13)

    draw.text((GAP + 4, 8), "ROGALIK · Этап 3 · задача 3.1e — мастер-образ героя",
              font=head, fill=TEXT)
    top = GAP + 30
    floor_y = top + LABEL_H + PANEL_H - 8

    for index, (title, subtitle, image) in enumerate(items):
        x = GAP + index * (PANEL_W + GAP)
        draw.rectangle([x, top, x + PANEL_W, top + LABEL_H + PANEL_H],
                       fill=PANEL_BG, outline=(58, 54, 64))
        draw.text((x + 9, top + 6), title, font=name,
                  fill=ACCENT if "3.1e" in title else TEXT)
        draw.text((x + 9, top + 25), subtitle, font=small, fill=DIM)
        px = x + (PANEL_W - image.width) // 2
        py = floor_y - image.height
        if image.mode == "RGBA":
            sheet.paste(image, (px, py), image)
        else:
            sheet.paste(image, (px, py))
        draw.line([x + 10, floor_y + 2, x + PANEL_W - 10, floor_y + 2],
                  fill=FLOOR, width=1)

    draw.text((GAP + 4, top + LABEL_H + PANEL_H + 14),
              f"Все фигуры — {FIGURE_H} px на экране (кадр 1920×1080): 96 px ×2, 48 px ×4. "
              "Увеличение целочисленное, без сглаживания; высота нормирована по силуэту.",
              font=small, fill=DIM)
    out = os.path.join(REPORTS, "stage3e_compare_sheet.png")
    sheet.save(out)
    print(out, sheet.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
