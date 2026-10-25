"""Убирает запечённую контактную тень героя из фона (для кадров 3.1d).

В эксперименте 3.1c в фон была запечена тёмная контактная тень на месте героя.
Теперь тень героя даёт динамический свет (`PointLight2D` + `LightOccluder2D`),
поэтому запечённое пятно только мешает: оно висит под героем независимо от
источника. Скрипт аккуратно заменяет пятно чистым участком той же земли,
скопированным из соседней области того же изображения (текстура не «рисуется»
заново, поэтому зерно совпадает).

    python tools/res_study/patch_world_shadow.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "game" / "experiments" / "res_study" / "art"
LAYOUT = json.loads((ART / "layout.json").read_text(encoding="utf-8"))


def patch(variant: str) -> Path | None:
    info = LAYOUT[variant]
    tile = int(info["tile"])
    source = ART / variant / info["world_png"]
    if not source.is_file():
        print(f"нет {source}")
        return None
    image = Image.open(source).convert("RGB")
    arr = np.asarray(image).copy()
    h, w = arr.shape[:2]
    hx, hy = info["hero_pos"]
    # пятно: эллипс ~0.42×0.16 тайла вокруг точки стоп
    rx = int(tile * 0.55)
    ry = int(tile * 0.30)
    cx_, cy_ = int(hx), int(hy - tile * 0.12)
    y0, y1 = max(0, cy_ - ry), min(h, cy_ + ry)
    x0, x1 = max(0, cx_ - rx), min(w, cx_ + rx)
    # донор: тот же диапазон строк, сдвинутый на 4 тайла вправо (чистая земля)
    dxs = int(tile * 4)
    if x1 + dxs >= w:
        dxs = -int(tile * 4)
    donor = arr[y0:y1, x0 + dxs:x1 + dxs]
    if donor.shape != arr[y0:y1, x0:x1].shape:
        print(f"{variant}: донор не совпал по размеру, пропуск")
        return None
    # мягкая маска-эллипс, чтобы не было шва
    yy, xx = np.mgrid[y0:y1, x0:x1]
    mask = (((xx - cx_) / rx) ** 2 + ((yy - cy_) / ry) ** 2) <= 1.0
    edge = (((xx - cx_) / (rx * 1.25)) ** 2 + ((yy - cy_) / (ry * 1.3)) ** 2) <= 1.0
    sel = edge & ~mask
    target = arr[y0:y1, x0:x1]
    target[sel] = ((target[sel].astype(np.int16) + donor[sel].astype(np.int16)) // 2)
    target[mask] = donor[mask]
    arr[y0:y1, x0:x1] = target
    out = source.with_name(source.stem + "_ns.png")
    Image.fromarray(arr, "RGB").save(out)
    print(f"{variant}: {source.name} → {out.name} (пятно {x0}..{x1} × {y0}..{y1}, "
          f"донор сдвиг {dxs} px)")
    return out


def main() -> int:
    for variant in ("a", "c"):
        patch(variant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
