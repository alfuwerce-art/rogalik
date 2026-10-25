"""Диагностика слоёв героя: какая форма владеет каждым пикселем.

Пишет `reports/tmp_owner.png` — карта владельцев (каждый вызов paint своим цветом)
рядом с готовым спрайтом. Нужен только для отладки художественного рендера.

    python tools/res_study/debug_owner.py [height]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import res_study.form_render as fr  # noqa: E402
import res_study.author_hero as ah  # noqa: E402

TINTS = {
    "skin": (60, 110, 230), "skin_deep": (20, 40, 120), "pants": (40, 160, 60),
    "linen": (210, 200, 70), "red_cloth": (230, 40, 50), "hair": (220, 60, 220),
    "outline": (10, 10, 10),
}


def main() -> int:
    height = int(sys.argv[1]) if len(sys.argv) > 1 else 96
    owner = {"ids": None}
    ramps: list[str] = []
    original = fr.Canvas.paint

    def patched(self, sdf_fn, ramp, **kw):
        if owner["ids"] is None:
            owner["ids"] = np.full((self.height, self.width), -1)
        owner["ids"][self.coverage(sdf_fn) >= 0.5] = len(ramps)
        ramps.append(ramp)
        return original(self, sdf_fn, ramp, **kw)

    fr.Canvas.paint = patched
    canvas = ah.draw_hero(height)
    ids = owner["ids"]
    # контур: пиксели, которые есть в alpha, но не принадлежат ни одному paint
    ids[canvas.alpha & (ids < 0)] = len(ramps)
    ramps.append("outline")

    h, w = canvas.height, canvas.width
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[ids < 0] = (28, 24, 32)
    for index, ramp in enumerate(ramps):
        rgb[ids == index] = TINTS.get(ramp, (255, 255, 255))
    owner_img = Image.fromarray(rgb, "RGB")

    scale = 10 if height >= 96 else 14
    big = owner_img.resize((w * scale, h * scale), Image.NEAREST)
    sprite = canvas.to_image().resize((w * scale, h * scale), Image.NEAREST)
    sheet = Image.new("RGB", (big.width * 2 + 24, big.height + 16), (28, 24, 32))
    sheet.paste(big, (8, 8))
    sheet.paste(sprite, (big.width + 16, 8), sprite)
    sheet.save(ROOT / "reports" / "tmp_owner.png")
    print(f"owner map: reports/tmp_owner.png ({sheet.width}x{sheet.height}), layers={len(ramps)}")

    from collections import Counter
    for index, ramp in enumerate(ramps):
        area = int((ids == index).sum())
        if area:
            ys, xs = np.where(ids == index)
            print(f"{index:3d} {ramp:11s} area={area:4d} bbox=({xs.min()},{ys.min()},{xs.max()},{ys.max()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
