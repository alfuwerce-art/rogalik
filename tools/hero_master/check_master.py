"""Технические проверки мастер-спрайта героя (задача 3.1e).

Проверяется только то, что можно измерить: прозрачность, палитра, привязка,
высота фигуры, профиль силуэта и попиксельное совпадение с экспортом
**реального Pixelorama CLI** из редактируемого `.pxo`.

Художественное качество этими проверками НЕ доказывается (D20): ответ гейта
даёт человек/агент по наблюдаемому изображению, а не скрипт.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART = os.path.join(ROOT, "game", "experiments", "res_study", "art", "hero_master")
REPORTS = os.path.join(ROOT, "reports")


def load(path: str) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGBA"))


def profile(alpha: np.ndarray) -> dict:
    """Профиль силуэта: ширина фигуры по строкам и ключевые доли высоты."""
    body = alpha > 0
    rows = np.where(body.any(axis=1))[0]
    widths = body.sum(axis=1)
    top, bottom = int(rows.min()), int(rows.max())
    height = bottom - top + 1

    def widest_between(a: float, b: float) -> tuple[float, int]:
        lo = top + int(a * height)
        hi = top + int(b * height)
        seg = widths[lo:hi + 1]
        idx = int(np.argmax(seg))
        return round((lo + idx - top) / height, 3), int(seg[idx])

    return {
        "figure_rows": [top, bottom],
        "figure_height_px": height,
        "feet_row": bottom,
        "bbox_cols": [int(np.where(body.any(axis=0))[0].min()),
                      int(np.where(body.any(axis=0))[0].max())],
        "widest_row_head_0_0_0_22": widest_between(0.0, 0.22),
        "widest_row_shoulders_0_22_0_40": widest_between(0.22, 0.40),
        "widest_row_hips_0_46_0_60": widest_between(0.46, 0.60),
        "widest_row_legs_0_60_1_00": widest_between(0.60, 1.0),
        "min_width_row_0_40_0_50": int(widths[top + int(0.40 * height):
                                             top + int(0.50 * height)].min()),
    }


def check(height: int) -> dict:
    src_path = os.path.join(ART, f"hero_master_{height}.png")
    rt_path = os.path.join(REPORTS, f"hero_master_{height}_rt.png")
    src = load(src_path)
    result: dict = {
        "height": height,
        "source": os.path.relpath(src_path, ROOT).replace("\\", "/"),
        "size": [int(src.shape[1]), int(src.shape[0])],
        "pxo": f"tools/hero_master/pxo/hero_master_{height}.pxo",
    }
    alpha = src[:, :, 3]
    result["semi_transparent_px"] = int(((alpha > 0) & (alpha < 255)).sum())
    solid = src[alpha == 255]
    colors = np.unique(solid[:, :3], axis=0)
    result["colors_opaque"] = int(len(colors))
    result["palette_hex"] = sorted(
        "#%02X%02X%02X" % tuple(int(v) for v in c) for c in colors)
    result.update(profile(alpha))

    if os.path.exists(rt_path):
        rt = load(rt_path)
        same_shape = rt.shape == src.shape
        identical = bool(same_shape and np.array_equal(rt, src))
        diff = (int(np.abs(rt.astype(int) - src.astype(int)).max())
                if same_shape else -1)
        opaque_diff = -1
        if same_shape:
            op = alpha == 255
            opaque_diff = int(np.abs(rt[:, :, :3].astype(int)[op]
                                     - src[:, :, :3].astype(int)[op]).max()) if op.any() else 0
        result["pxo_roundtrip"] = {
            "path": os.path.relpath(rt_path, ROOT).replace("\\", "/"),
            "same_shape": bool(same_shape),
            "pixel_identical": identical,
            "max_channel_diff": diff,
            "max_channel_diff_opaque_only": opaque_diff,
        }
    else:
        result["pxo_roundtrip"] = {"status": "NOT_VERIFIED",
                                   "reason": "экспорт Pixelorama не найден"}
    return result


def main() -> int:
    report = {
        "task": "3.1e",
        "what_is_checked": "прозрачность, палитра, привязка, высота, профиль, "
                           "попиксельное совпадение с экспортом Pixelorama",
        "what_is_NOT_checked": "художественное качество (D20: отвечает "
                               "REFERENCE_FIDELITY_GATE, а не скрипт)",
        "sprites": {},
    }
    ok = True
    for height in (96, 48):
        item = check(height)
        report["sprites"][str(height)] = item
        if item["semi_transparent_px"] != 0:
            ok = False
        if not item["pxo_roundtrip"].get("pixel_identical", False):
            ok = False
    report["status"] = "PASS" if ok else "FAIL"
    out = os.path.join(REPORTS, "stage3e_checks.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
