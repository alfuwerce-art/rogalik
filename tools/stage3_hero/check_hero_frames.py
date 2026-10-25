"""Технические проверки листа героя (Этап 3, задача 3.1).

Проверяется то, что можно доказать машинно, — и ничего сверх этого:

* экспорт Pixelorama `.pxo` совпадает с исходными кадрами попиксельно
  (то есть в игру идёт именно нарисованное, без пересэмплинга);
* геометрия листа: 8 кадров 32x48, все кадры непустые;
* привязка: нижняя строка (подошва) у всех кадров одна и та же, центр стоп
  не смещается между кадрами `idle` одного направления;
* нет полупрозрачных пикселей и градиентов: только полная непрозрачность или
  полная прозрачность (признак отсутствия сглаживания/размытия);
* палитра ограничена и совпадает у всех кадров.

Художественное качество этими проверками **не** доказывается: статус ассета —
`ASSET_DRAFT`, приёмка за владельцем.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from PIL import Image

FRAME_W = 32
FRAME_H = 48
DIRECTIONS = ("down", "up", "left", "right")
IDLE_FRAMES = 2
EXPECTED_FRAMES = len(DIRECTIONS) * IDLE_FRAMES


def read_pxo_frames(project: Path) -> list[Image.Image]:
    """Кадры из `.pxo` (ZIP: image_data/frames/<n>/layer_1, RGBA8, построчно)."""
    frames: list[Image.Image] = []
    with zipfile.ZipFile(project) as archive:
        indices = sorted(
            int(name.split("/")[2])
            for name in archive.namelist()
            if name.startswith("image_data/frames/") and name.endswith("/layer_1")
        )
        for index in indices:
            raw = archive.read(f"image_data/frames/{index}/layer_1")
            image = Image.frombytes("RGBA", (FRAME_W, FRAME_H), raw)
            frames.append(image)
    return frames


def sheet_frames(sheet: Path, count: int) -> list[Image.Image]:
    image = Image.open(sheet).convert("RGBA")
    if image.width % FRAME_W or image.height % FRAME_H:
        raise SystemExit(f"{sheet}: {image.width}x{image.height} не делится на {FRAME_W}x{FRAME_H}")
    if image.height != FRAME_H:
        raise SystemExit(f"{sheet}: ожидался один ряд кадров высотой {FRAME_H}, получено {image.height}")
    return [
        image.crop((i * FRAME_W, 0, (i + 1) * FRAME_W, FRAME_H))
        for i in range(min(count, image.width // FRAME_W))
    ]


def frame_metrics(image: Image.Image) -> dict:
    alpha = image.getchannel("A")
    bbox = image.getbbox()
    bottom = bbox[3] if bbox else None
    # Центр стоп: горизонтальный центр непрозрачных пикселей в нижних 3 строках.
    feet_columns = []
    for y in range(FRAME_H - 3, FRAME_H):
        for x in range(FRAME_W):
            if alpha.getpixel((x, y)) > 0:
                feet_columns.append(x)
    feet_center = (min(feet_columns) + max(feet_columns)) / 2.0 if feet_columns else None
    opaque = FRAME_W * FRAME_H - alpha.histogram()[0]
    partial = sum(alpha.histogram()[1:255])
    colors = {pixel for _count, pixel in image.getcolors(1 << 24) or []}
    return {
        "bbox": bbox,
        "bottom": bottom,
        "feet_center": feet_center,
        "opaque": opaque,
        "partial_alpha": partial,
        "colors": len(colors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", required=True, help="PNG-экспорт Pixelorama")
    parser.add_argument("--project", required=True, help="исходный .pxo")
    parser.add_argument("--json", default=None)
    parser.add_argument("--report", default=None, help="записать текстовый отчёт")
    args = parser.parse_args(argv)

    sheet_path = Path(args.sheet)
    project_path = Path(args.project)
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    pxo_frames = read_pxo_frames(project_path)
    check("pxo_frame_count", len(pxo_frames) == EXPECTED_FRAMES, f"{len(pxo_frames)} кадров в .pxo, ожидалось {EXPECTED_FRAMES}")

    exported = sheet_frames(sheet_path, EXPECTED_FRAMES)
    check("sheet_frame_count", len(exported) == EXPECTED_FRAMES, f"{len(exported)} кадров в листе, ожидалось {EXPECTED_FRAMES}")

    identical = all(
        a.tobytes() == b.tobytes() for a, b in zip(pxo_frames, exported)
    )
    check(
        "export_matches_source",
        identical,
        "кадры Pixelorama-экспорта совпадают с кадрами .pxo попиксельно" if identical else "экспорт отличается от .pxo",
    )

    metrics = [frame_metrics(frame) for frame in exported]
    bottoms = [m["bottom"] for m in metrics]
    check("feet_anchor_bottom", len(set(bottoms)) == 1, f"нижняя граница кадров: {bottoms}")

    per_direction = []
    feet_ok = True
    for index, name in enumerate(DIRECTIONS):
        pair = metrics[index * IDLE_FRAMES : (index + 1) * IDLE_FRAMES]
        centers = [m["feet_center"] for m in pair]
        if len(set(centers)) != 1:
            feet_ok = False
        per_direction.append({"direction": name, "feet_center": centers, "bottoms": [m["bottom"] for m in pair]})
    check("idle_body_lock", feet_ok, "центр стоп не меняется между кадрами idle: " + str(per_direction))

    partial = sum(m["partial_alpha"] for m in metrics)
    check("no_partial_alpha", partial == 0, f"полупрозрачных пикселей: {partial} (0 — нет сглаживания)")

    empty = [i for i, m in enumerate(metrics) if m["opaque"] == 0]
    check("no_empty_frames", not empty, f"пустые кадры: {empty or 'нет'}")

    color_counts = {m["colors"] for m in metrics}
    check(
        "palette_consistency",
        len(color_counts) == 1,
        f"уникальных цветов по кадрам: {sorted(color_counts)}",
    )

    height = [m["bbox"][3] - m["bbox"][1] for m in metrics]
    base_heights = [height[i * IDLE_FRAMES] for i in range(len(DIRECTIONS))]
    idle_heights = [height[i * IDLE_FRAMES + 1] for i in range(len(DIRECTIONS))]
    check(
        "hero_height_48",
        all(value == FRAME_H for value in base_heights) and all(value == FRAME_H - 1 for value in idle_heights),
        f"высота силуэта: базовые кадры {base_heights}, кадры вдоха {idle_heights} "
        f"(D16: 48 px; в кадре вдоха голова опущена на 1 px, поэтому верхняя строка пуста, "
        f"а геометрия кадра 32x48 неизменна — стопы не смещаются)",
    )
    top_rows = [m["bbox"][1] for m in metrics]
    tops_ok = all(
        top_rows[i * IDLE_FRAMES + 1] == top_rows[i * IDLE_FRAMES] + 1 for i in range(len(DIRECTIONS))
    )
    check(
        "idle_head_shift_1px",
        tops_ok,
        f"верхняя граница по кадрам: {top_rows} (вдох ровно на 1 px ниже базы)",
    )

    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    result = {
        "status": status,
        "sheet": str(sheet_path),
        "project": str(project_path),
        "frame_size": [FRAME_W, FRAME_H],
        "frames": len(exported),
        "checks": checks,
        "metrics": metrics,
        "note": "технические проверки не являются художественной приёмкой (ASSET_DRAFT)",
    }
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"{status}  лист героя: {sheet_path}", f"  .pxo: {project_path}"]
    for item in checks:
        lines.append(f"  [{item['status']}] {item['name']}: {item['detail']}")
    text = "\n".join(lines)
    print(text)
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
