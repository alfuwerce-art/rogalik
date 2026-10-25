"""Превью сгенерированных PROXY_TECHNICAL-ассетов (для просмотра человеком).

Складывает тайлсеты, спрайт-листы героя и пропсы всех трёх сеток в один PNG
с увеличением nearest-neighbour.

    python tools/stage2_location/make_preview.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "game" / "prototype" / "art"
OUT = ROOT / "reports" / "stage2_2_1_assets_preview.png"

GRIDS = (16, 24, 32)
PAD = 12


def scaled(path: Path, factor: int) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    return img.resize((img.width * factor, img.height * factor), Image.NEAREST)


def main() -> None:
    rows: list[Image.Image] = []
    for tile in GRIDS:
        hero = tile * 2
        parts = [
            scaled(ART / "tilesets" / f"tileset_{tile}.png", 4),
            scaled(ART / "sprites" / f"hero_proxy_{hero}.png", 2),
            scaled(ART / "props" / f"tree_{tile}.png", 2),
            scaled(ART / "props" / f"gate_{tile}.png", 2),
        ]
        width = sum(p.width for p in parts) + PAD * (len(parts) + 1)
        height = max(p.height for p in parts) + PAD * 2
        row = Image.new("RGBA", (width, height), (24, 28, 36, 255))
        x = PAD
        for part in parts:
            row.alpha_composite(part, (x, height - PAD - part.height))
            x += part.width + PAD
        rows.append(row)

    width = max(r.width for r in rows)
    height = sum(r.height for r in rows) + PAD * (len(rows) + 1)
    sheet = Image.new("RGBA", (width, height), (16, 19, 26, 255))
    y = PAD
    for row in rows:
        sheet.alpha_composite(row, (0, y))
        y += row.height + PAD
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"preview -> {OUT.relative_to(ROOT)} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
