"""Сравнительный лист калибровки (Этап 3, задача 3.1b).

Собирает один лист:

    1. текущий вид прототипа (кадр задачи 3.1a, Этап 2-3);
    2. новый калибровочный кадр (реальный запуск Godot);
    3. look-референс владельца `gameplay_look_reference.png`;
    4. герой 3.1a → герой 3.1b → утверждённый референс героя.

Все панели — реальные файлы репозитория: кадры взяты из запусков Godot, референсы —
из `assets/references/`. Лист только компонует их и подписывает; он ничего не
дорисовывает и не «улучшает».

    python tools/stage3_calibration/make_compare.py --out reports/stage3b_calibration_compare.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BACKGROUND = (14, 17, 23, 255)
LABEL = (198, 193, 181, 255)
NOTE = (140, 138, 130, 255)

# Шрифт с кириллицей: стандартный шрифт PIL её не содержит и рисует «квадратики».
FONT_CANDIDATES = (
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def fit(image: Image.Image, width: int, height: int) -> Image.Image:
    """Вписать без искажения пропорций и без сглаживания (целочисленное уменьшение)."""
    scale = min(width / image.width, height / image.height)
    if scale >= 1.0:
        step = int(scale)
        return image.resize((image.width * step, image.height * step), Image.NEAREST)
    # Уменьшение — целочисленным коэффициентом, чтобы пиксели остались пикселями.
    divisor = max(1, int(round(1.0 / scale)))
    return image.resize((image.width // divisor, image.height // divisor), Image.NEAREST)


def panel(
    sheet: Image.Image,
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    box,
    title: str,
    note: str = "",
    fonts: tuple = None,
) -> None:
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    fitted = fit(image, width - 8, height - 40)
    px = x0 + (width - fitted.width) // 2
    py = y0 + 28 + (height - 40 - fitted.height) // 2
    sheet.alpha_composite(fitted, (px, py))
    draw.rectangle((x0, y0, x1, y1), outline=(52, 58, 68, 255))
    label_font, note_font = fonts if fonts else (None, None)
    draw.text((x0 + 6, y0 + 5), title, fill=LABEL, font=label_font)
    if note:
        draw.text((x0 + 6, y0 + 17), note, fill=NOTE, font=note_font)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="reports/stage3b_calibration_compare.png")
    args = parser.parse_args(argv)

    prototype = Image.open(ROOT / "reports" / "stage3a_frame_down.png").convert("RGBA")
    calibration = Image.open(ROOT / "reports" / "stage3b_calib_frame.png").convert("RGBA")
    reference = Image.open(ROOT / "assets" / "references" / "gameplay" / "gameplay_look_reference.png").convert("RGBA")
    hero_new = Image.open(ROOT / "reports" / "stage3b_hero_sheet_x6.png").convert("RGBA")
    hero_old = Image.open(ROOT / "reports" / "stage3a_preview_final.png").convert("RGBA")
    hero_ref = Image.open(ROOT / "assets" / "references" / "hero" / "hero_reference_front_back.png").convert("RGBA")

    panel_width, panel_height = 940, 560
    gap = 16
    margin = 18
    header = 64
    footer = 190
    width = margin * 2 + panel_width * 2 + gap
    height = margin * 2 + header + panel_height * 2 + gap + footer
    sheet = Image.new("RGBA", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(17)
    label_font = load_font(13)
    note_font = load_font(12)
    fonts = (label_font, note_font)

    draw.text((margin, margin), "Rogalik — калибровка игрового кадра (Этап 3, задача 3.1b)", fill=LABEL, font=title_font)
    draw.text(
        (margin, margin + 22),
        "Все панели — реальные файлы: кадры из запущенной игры Godot 4.7.2 и референсы владельца. Не концепт-арт.",
        fill=NOTE,
        font=note_font,
    )
    draw.text(
        (margin, margin + 38),
        "D16 неизменны: тайл 24 px · герой 48 px · zoom 1.0 · 480x270 · окно 960x540 · 4 направления · арт — ASSET_DRAFT",
        fill=NOTE,
        font=note_font,
    )

    top = margin + header
    left = margin
    right = left + panel_width + gap
    panel(sheet, draw, prototype, (left, top, left + panel_width, top + panel_height),
          "1. Прототип Этапа 2/3 (кадр 3.1a): процедурные прокси, плоский свет",
          "было · заглушка тайлов PROXY_TECHNICAL", fonts)
    panel(sheet, draw, calibration, (right, top, right + panel_width, top + panel_height),
          "2. Калибровочный кадр 3.1b (реальный запуск, 960x540, 2x)",
          "стало · арт нарисован и прогнан через Pixelorama CLI", fonts)
    second = top + panel_height + gap
    panel(sheet, draw, reference, (left, second, left + panel_width, second + panel_height),
          "3. Look-референс владельца (gameplay_look_reference.png)",
          "ориентир настроения: ночь, тёплые пятна, мокрый двор", fonts)
    panel(sheet, draw, hero_new, (right, second, right + panel_width, second + panel_height),
          "4. Герой 3.1b в игре = лист 48 px (показан x6)",
          "новый силуэт: плечи 20 px, талия 8 px, повязка 3 ряда", fonts)

    footer_top = second + panel_height + gap
    hero_panel_w = panel_width // 2
    panel(sheet, draw, hero_old, (left, footer_top, left + hero_panel_w, footer_top + footer - 8),
          "Было: герой 3.1a", "", fonts)
    panel(sheet, draw, hero_ref, (left + hero_panel_w + 8, footer_top, left + panel_width, footer_top + footer - 8),
          "Референс героя (VISUAL_APPROVED, D7)", "", fonts)
    draw.text(
        (right + 6, footer_top + 8),
        "Ограничения: врагов, боя и HUD в калибровке нет (Этап 5); верх построек обрезан кадром;",
        fill=NOTE,
        font=note_font,
    )
    draw.text(
        (right + 6, footer_top + 26),
        "24 px тайл всё ещё даёт заметный повтор рисунка; динамический PointLight2D отключён",
        fill=NOTE,
        font=note_font,
    )
    draw.text(
        (right + 6, footer_top + 44),
        "из-за 5-6 неодноцветных блоков 2x2 (замер check_pixel_scale.py).",
        fill=NOTE,
        font=note_font,
    )
    draw.text(
        (right + 6, footer_top + 68),
        "Художественное качество автотестом не доказывается: статус ASSET_DRAFT.",
        fill=LABEL,
        font=label_font,
    )

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out, quality=92)
    print(f"compare={out} size={sheet.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
