"""Command line entry point for the Rogalik pixel pipeline.

    python -m pixel_pipeline.cli demo --out artifacts/demo
    python -m pixel_pipeline.cli check art/hero.png --frame 32
    python -m pixel_pipeline.cli build art/hero_walk.pxo --sheet art/hero.png --frame 32
    python -m pixel_pipeline.cli export art/hero_walk.pxo --out art/export --sheet
    python -m pixel_pipeline.cli atlas art/export/hero_walk.png --frame 32 --out art/atlas
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from . import atlas as atlas_mod
from . import pixelorama
from . import pxo as pxo_mod
from . import validate as validate_mod
from .examples import make_test_sprite


def _print(report: validate_mod.Report, as_json: bool) -> int:
    if as_json:
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(validate_mod.report_text(report))
    return 0 if report.status == validate_mod.PASS else 1


def _split_sheet(path: Path, frame: int) -> list[Image.Image]:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        if rgba.width % frame or rgba.height % frame:
            raise SystemExit(f"{rgba.width}x{rgba.height} is not divisible by {frame}")
        columns, rows = rgba.width // frame, rgba.height // frame
        return [
            rgba.crop((c * frame, r * frame, (c + 1) * frame, (r + 1) * frame))
            for r in range(rows)
            for c in range(columns)
        ]


def cmd_check(args) -> int:
    if args.tile:
        report = validate_mod.validate_tileset(args.path, args.tile)
    elif args.frame:
        report = validate_mod.validate_sheet(
            args.path, args.frame, args.frame_height, args.frames
        )
    else:
        report = validate_mod.validate_png(args.path)
    if args.json:
        report.save(args.json)
    return _print(report, args.as_json)


def cmd_build(args) -> int:
    sheet = Path(args.sheet)
    frames = _split_sheet(sheet, args.frame)
    tags = [pxo_mod.frame_tag(args.tag, 0, len(frames) - 1)] if args.tag else []
    out = pxo_mod.build_pxo(
        args.out, frames, fps=args.fps, layer_name=args.layer, tags=tags
    )
    print(json.dumps({"status": "PASS", "project": str(out), "frames": len(frames), "bytes": out.stat().st_size}))
    return 0


def cmd_export(args) -> int:
    result = pixelorama.export_project(
        args.project, args.out, spritesheet=args.sheet, scale=args.scale, keep_name=args.name
    )
    print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    return 0 if result.ok else 1


def cmd_atlas(args) -> int:
    info = atlas_mod.build_atlas(
        args.sheet, args.frame, args.frame_height or args.frame, args.out,
        columns=args.columns, name=args.name,
    )
    info["validation"] = atlas_mod.validate_atlas(info["metadata"])
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0 if info["validation"]["status"] == "PASS" else 1


def cmd_demo(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []

    sheet_path = out / "hero_sheet_source.png"
    make_test_sprite.save_sheet(sheet_path)
    steps.append({"step": "generate", "status": "PASS", "artifact": str(sheet_path)})

    frames = _split_sheet(sheet_path, 32)
    project = out / "hero_walk.pxo"
    pxo_mod.build_pxo(
        project, frames, fps=8.0, layer_name="Hero",
        tags=[pxo_mod.frame_tag("walk", 0, len(frames) - 1)],
    )
    steps.append({"step": "build_pxo", "status": "PASS", "artifact": str(project)})

    exported = pixelorama.export_project(project, out / "export", spritesheet=True, keep_name="hero_walk")
    steps.append(
        {
            "step": "pixelorama_export",
            "status": "PASS" if exported.ok else "FAIL",
            "artifact": exported.files,
            "command": " ".join(exported.command[-4:]),
            "exit_code": exported.exit_code,
            "problems": exported.problems,
        }
    )
    if not exported.ok:
        print(json.dumps({"status": "FAIL", "steps": steps}, indent=2, ensure_ascii=False))
        return 1

    exported_sheet = Path(exported.files[0])
    report = validate_mod.validate_sheet(exported_sheet, 32, expected_frames=len(frames))
    report_path = report.save(out / "report.json")
    steps.append(
        {
            "step": "validate",
            "status": report.status,
            "artifact": str(report_path),
            "checks": [check.as_dict() for check in report.checks],
        }
    )

    info = atlas_mod.build_atlas(exported_sheet, 32, 32, out / "atlas", columns=2)
    info["validation"] = atlas_mod.validate_atlas(info["metadata"])
    steps.append({"step": "atlas", "status": info["validation"]["status"], "artifact": info})

    status = "PASS" if all(step["status"] == "PASS" for step in steps) else "FAIL"
    result = {"status": status, "artifacts": str(out), "steps": steps}
    (out / "demo.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if status == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pixel_pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate a PNG, sprite sheet or tileset")
    check.add_argument("path")
    check.add_argument("--frame", type=int, help="frame width for a sprite sheet")
    check.add_argument("--frame-height", type=int)
    check.add_argument("--frames", type=int, help="expected frame count")
    check.add_argument("--tile", type=int, help="tile size for a tileset")
    check.add_argument("--json", help="write the report to this path")
    check.add_argument("--as-json", action="store_true", help="print JSON instead of text")
    check.set_defaults(func=cmd_check)

    build = sub.add_parser("build", help="build a Pixelorama .pxo from an RGBA sheet")
    build.add_argument("out")
    build.add_argument("--sheet", required=True)
    build.add_argument("--frame", type=int, required=True)
    build.add_argument("--fps", type=float, default=8.0)
    build.add_argument("--layer", default="Layer 1")
    build.add_argument("--tag", default="")
    build.set_defaults(func=cmd_build)

    export = sub.add_parser("export", help="export a .pxo through the Pixelorama CLI")
    export.add_argument("project")
    export.add_argument("--out", required=True)
    export.add_argument("--sheet", action="store_true", help="export one sprite sheet instead of frames")
    export.add_argument("--scale", type=int)
    export.add_argument("--name")
    export.set_defaults(func=cmd_export)

    atlas_cmd = sub.add_parser("atlas", help="pack a sheet into an atlas plus JSON metadata")
    atlas_cmd.add_argument("sheet")
    atlas_cmd.add_argument("--frame", type=int, required=True)
    atlas_cmd.add_argument("--frame-height", type=int)
    atlas_cmd.add_argument("--columns", type=int)
    atlas_cmd.add_argument("--out", required=True)
    atlas_cmd.add_argument("--name")
    atlas_cmd.set_defaults(func=cmd_atlas)

    demo = sub.add_parser("demo", help="run the full sprite pipeline smoke test")
    demo.add_argument("--out", default="artifacts/demo")
    demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
