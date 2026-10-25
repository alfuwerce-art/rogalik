#!/usr/bin/env python
"""Build small labelled contact sheets for visual review of imported references.

These sheets are review artifacts only: they are downscaled copies used to
confirm the PNGs open and depict the documented subject. Originals in
assets/references are never modified.
"""

from __future__ import annotations

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

TILE = 460
PAD = 10
LABEL_H = 44
BG = (18, 16, 20)
FG = (230, 224, 214)

GROUPS = {
    "bosses": ["bosses/"],
    "enemies": ["enemies/"],
    "weapons": ["weapons/"],
    "locations": ["locations/"],
}


def main() -> int:
    repo = sys.argv[1]
    report = json.load(open(os.path.join(repo, "reports", "reference_import.json"), encoding="utf-8"))
    out_dir = os.path.join(repo, "reports", "reference_import_sheets")
    os.makedirs(out_dir, exist_ok=True)

    try:
        font = ImageFont.load_default(size=15)
        font_bold = ImageFont.load_default(size=17)
    except TypeError:
        font = font_bold = ImageFont.load_default()

    entries = [(f["relative"], os.path.join(repo, "assets", "references", *f["relative"].split("/")))
               for f in report["files"]]

    for group, prefixes in GROUPS.items():
        items = [(rel, path) for rel, path in entries if any(rel.startswith(p) for p in prefixes)]
        cols = 3 if len(items) > 2 else len(items)
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (TILE + PAD) + PAD, rows * (TILE + LABEL_H + PAD) + PAD), BG)
        draw = ImageDraw.Draw(sheet)
        for idx, (rel, path) in enumerate(items):
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((TILE, TILE), Image.LANCZOS)
                cx = PAD + (idx % cols) * (TILE + PAD) + (TILE - im.width) // 2
                cy = PAD + (idx // cols) * (TILE + LABEL_H + PAD) + (TILE - im.height) // 2
                sheet.paste(im, (cx, cy))
                name = os.path.basename(rel)
                draw.text((PAD + (idx % cols) * (TILE + PAD), cy + im.height + 6), name[:52], fill=FG, font=font)
        out = os.path.join(out_dir, f"{group}.png")
        sheet.save(out, optimize=True)
        print(f"{out}  {sheet.width}x{sheet.height}  {len(items)} tiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
