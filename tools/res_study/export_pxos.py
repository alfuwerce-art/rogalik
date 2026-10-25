"""Экспорт экспериментальных ассетов через настоящий Pixelorama CLI (3.1c).

Каждый PNG-источник превращается в проект `.pxo` (формат Pixelorama) и
экспортируется **CLI Pixelorama 1.2.3** обратно в PNG игры. Так владелец может
открыть любой ассет в Pixelorama и доработать его руками, а не только смотреть
на картинку.

    python tools/res_study/export_pxos.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from pixel_pipeline import pixelorama, pxo as pxo_mod  # noqa: E402

ART = ROOT / "game" / "experiments" / "res_study" / "art"
PROJECTS = ROOT / "tools" / "res_study" / "pxo"

# (вариант, файл, имя проекта)
ASSETS = [
    ("a", "hero_down_48.png", "hero_down_48"),
    ("b", "hero_down_64.png", "hero_down_64"),
    ("c", "hero_down_96.png", "hero_down_96"),
    ("a", "world_24.png", "world_24"),
    ("b", "world_32.png", "world_32"),
    ("c", "world_48.png", "world_48"),
]


def main() -> int:
    PROJECTS.mkdir(parents=True, exist_ok=True)
    report: list[dict] = []
    failures = 0
    for variant, name, stem in ASSETS:
        source = ART / variant / name
        if not source.is_file():
            report.append({"asset": name, "status": "FAIL", "problem": "нет источника"})
            failures += 1
            continue
        with Image.open(source) as image:
            frame = image.convert("RGBA")
        project = PROJECTS / f"{stem}.pxo"
        pxo_mod.build_pxo(project, [frame], fps=6.0, layer_name=stem)
        result = pixelorama.export_project(project, ART / variant, spritesheet=True,
                                           keep_name=stem)
        entry: dict = {"asset": f"{variant}/{name}",
                       "project": Path(project).relative_to(ROOT).as_posix(),
                       "export_ok": result.ok, "files": [Path(f).name for f in result.files],
                       "problems": result.problems}
        if not result.ok:
            entry["status"] = "FAIL"
            failures += 1
            report.append(entry)
            print("FAIL", variant, name, result.problems)
            continue
        exported = Path(result.files[0])
        with Image.open(exported) as image:
            back = image.convert("RGBA")
        identical = back.size == frame.size and back.tobytes() == frame.tobytes()
        worst = 0
        if not identical and back.size == frame.size:
            for y in range(frame.height):
                for x in range(frame.width):
                    a = frame.getpixel((x, y))
                    b = back.getpixel((x, y))
                    worst = max(worst, max(abs(a[i] - b[i]) for i in range(4)))
        entry.update({"status": "PASS" if identical or worst <= 2 else "FAIL",
                      "size": list(back.size), "pixels_identical": identical,
                      "max_channel_diff": worst})
        if entry["status"] == "FAIL":
            failures += 1
        report.append(entry)
        print(entry["status"], variant, name, back.size, "identical=", identical,
              "max_diff=", worst)

    summary = {"status": "PASS" if failures == 0 else "FAIL", "assets": len(ASSETS),
               "failed": failures, "report": report}
    (ROOT / "reports" / "stage3c_pxo_export.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"EXPORT status={summary['status']} assets={summary['assets']} failed={failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
