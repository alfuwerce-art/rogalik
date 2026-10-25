"""Deterministic placeholder sprite used by the pipeline smoke test.

The artwork is deliberately simple: it exists to prove the Pixelorama project ->
PNG sheet -> validation -> Godot import chain, not to represent final game art.
Palette follows docs/PIXEL_ART_STYLE_GUIDE.md section 4.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

PALETTE = {
    "night": (27, 34, 48, 255),
    "slate": (57, 66, 76, 255),
    "ash": (119, 115, 109, 255),
    "gold": (170, 144, 104, 255),
    "crimson": (108, 39, 57, 255),
    "ivory": (198, 193, 181, 255),
    "shadow": (18, 22, 31, 255),
}

SIZE = 32
FRAMES = 4


def _draw_hero(frame: int) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    bob = 1 if frame in (1, 3) else 0
    top = 6 + bob

    # cloak / body silhouette
    d.rectangle([11, top + 8, 20, top + 18], fill=PALETTE["crimson"])
    d.rectangle([12, top + 9, 19, top + 17], fill=PALETTE["slate"])
    # shoulder line
    d.rectangle([11, top + 8, 20, top + 9], fill=PALETTE["crimson"])

    # head + hood
    d.rectangle([12, top, 19, top + 7], fill=PALETTE["ivory"])
    d.rectangle([12, top - 1, 19, top + 1], fill=PALETTE["crimson"])
    d.rectangle([11, top, 12, top + 3], fill=PALETTE["crimson"])
    d.rectangle([19, top, 20, top + 3], fill=PALETTE["crimson"])

    # eyes
    d.point((14, top + 3), fill=PALETTE["night"])
    d.point((17, top + 3), fill=PALETTE["night"])

    # belt
    d.rectangle([11, top + 13, 20, top + 14], fill=PALETTE["gold"])

    # legs alternate between the two walk poses
    left_lift = 1 if frame in (1, 2) else 0
    right_lift = 1 if frame in (3, 0) else 0
    d.rectangle([12, top + 18, 14, top + 21 - left_lift], fill=PALETTE["slate"])
    d.rectangle([17, top + 18, 19, top + 21 - right_lift], fill=PALETTE["slate"])
    d.rectangle([12, top + 21 - left_lift, 14, top + 22 - left_lift], fill=PALETTE["shadow"])
    d.rectangle([17, top + 21 - right_lift, 19, top + 22 - right_lift], fill=PALETTE["shadow"])

    # ground shadow keeps the character anchored
    d.rectangle([12, 30, 19, 30], fill=(*PALETTE["shadow"][:3], 90))
    return img


def make_frames() -> list[Image.Image]:
    return [_draw_hero(index) for index in range(FRAMES)]


def save_sheet(path: str | Path) -> Path:
    frames = make_frames()
    sheet = Image.new("RGBA", (SIZE * len(frames), SIZE), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.paste(frame, (index * SIZE, 0))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "hero_sheet.png"
    print(save_sheet(target))
