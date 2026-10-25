"""Замер пропорций утверждённого референса героя.

Читает `assets/references/hero/hero_reference_front_back.png`, выделяет силуэт
передней фигуры по яркости и печатает нормированные пропорции (в долях высоты
фигуры): где плечи, талия, бёдра, колени, какова ширина головы.

Нужен, чтобы анатомия в спрайте опиралась на утверждённый референс, а не на
приблизительный глазомер. Только чтение, изображение не изменяется.

    python tools/res_study/measure_reference.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "assets" / "references" / "hero" / "hero_reference_front_back.png"


def main() -> int:
    image = Image.open(REF).convert("RGB")
    data = np.asarray(image, dtype=np.float32)
    lum = data.mean(axis=2)
    # Фон очень тёмный; фигура светлее.
    mask = lum > 70
    # Передняя фигура — левая половина кадра.
    half = mask[:, : mask.shape[1] // 2]
    ys, xs = np.nonzero(half)
    if len(xs) == 0:
        print("FAIL: силуэт не найден")
        return 1
    top, bottom = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())
    height = bottom - top + 1
    print(f"передняя фигура: bbox x[{left}..{right}] y[{top}..{bottom}], высота {height} px, "
          f"ширина {right - left + 1} px ({image.width}×{image.height})")

    # профиль ширины по строкам
    rows = []
    for y in range(top, bottom + 1):
        row = np.nonzero(half[y])[0]
        if len(row):
            rows.append((y, int(row.min()), int(row.max()), int(row.max() - row.min() + 1)))
    widths = np.array([r[3] for r in rows], dtype=np.float32)
    v = (np.array([r[0] for r in rows]) - top) / height  # 0 — макушка, 1 — стопы

    def at(vv: float) -> tuple[float, int]:
        i = int(np.argmin(np.abs(v - vv)))
        y, x0, x1, w = rows[i]
        return float(v[i]), w

    # голова: самая узкая часть верхних 20 % (шея) и ширина черепа
    head_zone = widths[(v > 0.02) & (v < 0.16)]
    print(f"ширина головы (макс. в верхних 16 %): {head_zone.max():.0f} px = "
          f"{head_zone.max() / height:.3f} H")
    neck_i = int(np.argmin(widths[(v > 0.10) & (v < 0.22)]))
    print(f"шея: минимум ширины в 0.10–0.22 → {widths[(v > 0.10) & (v < 0.22)][neck_i]:.0f} px = "
          f"{widths[(v > 0.10) & (v < 0.22)][neck_i] / height:.3f} H")

    for label, vv in [("верх плеч", 0.20), ("плечи (макс)", 0.24), ("грудь", 0.28),
                      ("талия", 0.40), ("бёдра", 0.46), ("бёдра/кушак", 0.50),
                      ("колено", 0.66), ("низ штанов", 0.82), ("щиколотка", 0.92),
                      ("стопы", 0.97)]:
        vv2, w = at(vv)
        print(f"{label:16s} v≈{vv2:.3f} ширина {w:4d} px = {w / height:.3f} H")

    shoulder_w = float(widths[(v > 0.16) & (v < 0.30)].max())
    waist_w = float(widths[(v > 0.36) & (v < 0.44)].min())
    print(f"\nплечи/талия: {shoulder_w:.0f}/{waist_w:.0f} px = {shoulder_w / waist_w:.2f}")
    print(f"плечи в головах: {shoulder_w / head_zone.max():.2f}; фигура в головах: "
          f"{height / (head_zone.max() * 1.0):.2f} (условно)")
    # высота головы: от макушки до сужения у шеи
    neck_v = float(v[(v > 0.10) & (v < 0.22)][int(np.argmin(widths[(v > 0.10) & (v < 0.22)]))])
    print(f"высота головы до шеи: {neck_v:.3f} H; фигура ≈ {1 / neck_v:.1f} головы")
    return 0


if __name__ == "__main__":
    sys.exit(main())
