"""Замер героя в игровом look-референсе: пропорции ракурса three-quarter.

Мерить нужно именно игровой ракурс, а не фронтальную ортографию: при камере
сверху под углом голова занимает бо́льшую долю высоты, плечи шире относительно
роста, а корпус сжат. Скрипт вырезает героя из `gameplay_look_reference.png`,
строит силуэт по цвету (герой теплее и светлее мутной земли) и печатает
нормированные пропорции, которые затем переносятся в автор спрайта.

    python tools/res_study/measure_look_hero.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "assets" / "references" / "gameplay" / "gameplay_look_reference.png"

# Область героя в look-референсе (без врагов и меча справа)
BOX = (598, 330, 1018, 660)


def main() -> int:
    image = Image.open(REF).convert("RGB")
    crop = image.crop(BOX)
    arr = np.asarray(crop, dtype=np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    lum = (r + g + b) / 3.0
    warm = r - b
    # кожа/ткань героя: заметно теплее и светлее мокрой земли вокруг
    mask = (lum > 62) & (warm > 16)
    # убираем мелкие пятна: оставляем связную область вокруг центра фигуры
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        print("FAIL: силуэт не найден")
        return 1
    cx0, cy0 = int(np.median(xs)), int(np.median(ys))
    keep = np.zeros_like(mask)
    keep[cy0, cx0] = True
    for _ in range(4000):
        grown = keep.copy()
        padded = np.pad(keep, 1, mode="constant", constant_values=False)
        grown = (padded[:-2, 1:-1] | padded[2:, 1:-1] | padded[1:-1, :-2] |
                 padded[1:-1, 2:] | keep)
        grown &= mask
        if np.array_equal(grown, keep):
            break
        keep = grown
    ys, xs = np.nonzero(keep)
    top, bottom = int(ys.min()), int(ys.max())
    height = bottom - top + 1
    print(f"фигура в look-референсе: bbox x[{xs.min()}..{xs.max()}] y[{top}..{bottom}], "
          f"высота {height} px, ширина {xs.max() - xs.min() + 1} px")

    rows = []
    for y in range(top, bottom + 1):
        row = np.nonzero(keep[y])[0]
        if len(row):
            rows.append((y, int(row.min()), int(row.max()), int(row.max() - row.min() + 1)))
    widths = np.array([r_[3] for r_ in rows], dtype=np.float32)
    v = (np.array([r_[0] for r_ in rows]) - top) / height

    def widest(v0: float, v1: float) -> tuple[float, int]:
        sel = (v >= v0) & (v <= v1)
        idx = int(np.argmax(widths[sel]))
        return float(v[sel][idx]), int(widths[sel][idx])

    head_v, head_w = widest(0.02, 0.22)
    shoulder_v, shoulder_w = widest(0.22, 0.40)
    hip_v, hip_w = widest(0.42, 0.60)
    print(f"голова+волосы: v≈{head_v:.3f}, ширина {head_w} px = {head_w / height:.3f} H")
    print(f"плечи/руки:    v≈{shoulder_v:.3f}, ширина {shoulder_w} px = "
          f"{shoulder_w / height:.3f} H")
    print(f"бёдра:         v≈{hip_v:.3f}, ширина {hip_w} px = {hip_w / height:.3f} H")
    print(f"голова / плечи: {head_w / shoulder_w:.2f}")
    print(f"доля головы в высоте (до сужения): {head_v:.3f}")
    for label, vv in [("0.10", 0.10), ("0.20", 0.20), ("0.30", 0.30), ("0.40", 0.40),
                      ("0.50", 0.50), ("0.60", 0.60), ("0.70", 0.70), ("0.80", 0.80),
                      ("0.90", 0.90)]:
        i = int(np.argmin(np.abs(v - float(vv))))
        print(f"  v={label}: ширина {widths[i]:.0f} px = {widths[i] / height:.3f} H")
    return 0


if __name__ == "__main__":
    sys.exit(main())
