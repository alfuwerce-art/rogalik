"""Экспорт калибровочного набора в игру через настоящий Pixelorama CLI.

Порядок для каждого ассета:

    PNG-источник (tools/stage3_calibration/source)
        → .pxo (пайплайн `pixel_pipeline.pxo`, настоящий формат Pixelorama)
        → экспорт **CLI Pixelorama 1.2.3**
        → игровой PNG (game/prototype/art/calibration)

Это тот же путь, которым собраны спрайты героя (задача 3.1): в игру попадает
именно то, что экспортировал Pixelorama, а не файл «похожего писателя PNG».
После экспорта кадры сравниваются с источником попиксельно.

    python tools/stage3_calibration/export_assets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from pixel_pipeline import pixelorama, pxo as pxo_mod  # noqa: E402

SOURCE = ROOT / "tools" / "stage3_calibration" / "source"
PROJECTS = ROOT / "tools" / "stage3_calibration" / "pxo"
TARGET = ROOT / "game" / "prototype" / "art" / "calibration"

# Ассеты с кадрами: (имя, ширина кадра, высота кадра, число кадров)
ASSETS = [
    ("ground_calib_24", 96, 48, 1),
    ("palisade_24", 48, 72, 1),
    ("gate_calib_24", 96, 96, 1),
    ("izba_24", 192, 120, 1),
    ("chapel_24", 168, 120, 1),
    ("dead_tree_24", 120, 144, 1),
    ("banner_24", 24, 48, 1),
    ("forest_24", 200, 100, 1),
    ("puddle_a_24", 54, 18, 1),
    ("puddle_b_24", 36, 14, 1),
    ("puddle_c_24", 72, 24, 1),
    ("torch_24", 24, 72, 2),
    ("glow_warm_24", 128, 128, 1),
    ("glow_cold_24", 128, 128, 1),
    ("fog_a_24", 320, 160, 1),
    ("fog_b_24", 320, 160, 1),
    ("vignette_24", 480, 270, 1),
    ("shadow_24", 44, 16, 1),
    ("props_calib_24", 24, 24, 4),
]


def split_frames(path: Path, frame_w: int, frame_h: int, count: int) -> list[Image.Image]:
    image = Image.open(path).convert("RGBA")
    if image.width != frame_w * count or image.height != frame_h:
        raise SystemExit(
            f"{path.name}: ожидалось {frame_w * count}x{frame_h} ({count} кадров), получено {image.width}x{image.height}"
        )
    return [
        image.crop((index * frame_w, 0, (index + 1) * frame_w, frame_h))
        for index in range(count)
    ]


def main() -> int:
    PROJECTS.mkdir(parents=True, exist_ok=True)
    TARGET.mkdir(parents=True, exist_ok=True)
    report: list[dict] = []
    failures = 0
    for name, frame_w, frame_h, count in ASSETS:
        source = SOURCE / f"{name}.png"
        if not source.is_file():
            report.append({"asset": name, "status": "FAIL", "problem": "нет источника"})
            failures += 1
            continue
        frames = split_frames(source, frame_w, frame_h, count)
        project = PROJECTS / f"{name}.pxo"
        tags = [pxo_mod.frame_tag("frames", 0, count - 1)] if count > 1 else []
        pxo_mod.build_pxo(project, frames, fps=6.0, layer_name=name, tags=tags)
        result = pixelorama.export_project(project, TARGET, spritesheet=True, keep_name=name)
        entry: dict = {
            "asset": name,
            "frames": count,
            "frame_size": [frame_w, frame_h],
            "project": str(project.relative_to(ROOT)).replace("\\", "/"),
            "export_ok": result.ok,
            "exit_code": result.exit_code,
            "files": [str(Path(f).relative_to(ROOT)).replace("\\", "/") for f in result.files],
            "problems": result.problems,
        }
        if not result.ok:
            failures += 1
            entry["status"] = "FAIL"
            report.append(entry)
            print(json.dumps(entry, ensure_ascii=False))
            continue
        exported = Path(result.files[0])
        with Image.open(exported) as image:
            exported_rgba = image.convert("RGBA")
        expected_w, expected_h = frame_w * count, frame_h
        exported_frames = [
            exported_rgba.crop((index * frame_w, 0, (index + 1) * frame_w, frame_h))
            for index in range(count)
        ]
        identical = all(a.tobytes() == b.tobytes() for a, b in zip(exported_frames, frames))
        # Pixelorama пересобирает слой через premultiplied alpha, поэтому у
        # полупрозрачных пикселей RGB может округлиться на 1–2. Полностью
        # непрозрачные и полностью прозрачные пиксели обязаны совпадать точно.
        rounding_only = False
        worst_diff = 0
        if not identical:
            rounding_only = True
            for source_frame, exported_frame in zip(frames, exported_frames):
                for y in range(frame_h):
                    for x in range(frame_w):
                        a = source_frame.getpixel((x, y))
                        b = exported_frame.getpixel((x, y))
                        diff = max(abs(a[i] - b[i]) for i in range(4))
                        worst_diff = max(worst_diff, diff)
                        if diff == 0:
                            continue
                        if a[3] in (0, 255) or b[3] in (0, 255) or diff > 2:
                            rounding_only = False
        size_ok = exported_rgba.size == (expected_w, expected_h)
        entry.update(
            {
                "status": "PASS" if size_ok and (identical or rounding_only) else "FAIL",
                "exported_size": list(exported_rgba.size),
                "expected_size": [expected_w, expected_h],
                "export_matches_source": identical,
                "alpha_rounding_only": rounding_only,
                "max_channel_diff": worst_diff,
                "bytes": exported.stat().st_size,
            }
        )
        if entry["status"] == "FAIL":
            failures += 1
        report.append(entry)
        print(
            f"{entry['status']} {name} {expected_w}x{expected_h} frames={count} "
            f"identical={identical} alpha_rounding_only={entry.get('alpha_rounding_only')} "
            f"max_diff={entry.get('max_channel_diff')}"
        )

    summary = {
        "status": "PASS" if failures == 0 else "FAIL",
        "assets": len(ASSETS),
        "failed": failures,
        "target": str(TARGET.relative_to(ROOT)).replace("\\", "/"),
        "report": report,
    }
    (ROOT / "reports" / "stage3b_export.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"EXPORT status={summary['status']} assets={summary['assets']} failed={failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
