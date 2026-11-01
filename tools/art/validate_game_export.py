#!/usr/bin/env python3
"""D26: validate structural readiness of generated Rogalik PNG game assets.

This does not validate artistic quality, seamlessness, or actual Godot rendering.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def validate(paths, kind, figure_height, pivot, tile_size):
    errors, records, canvas = [], [], None
    if kind in ("sprite", "animation", "object", "vfx") and pivot is None:
        errors.append("Missing --pivot X Y: origin must be recorded, not guessed")
    for path in paths:
        rec = {"file": str(path)}
        if not path.is_file():
            errors.append(f"{path}: file missing")
            records.append(rec)
            continue
        try:
            im = Image.open(path)
            im.load()
        except Exception as exc:
            errors.append(f"{path}: cannot decode image: {exc}")
            records.append(rec)
            continue
        w, h = im.size
        rec.update({"format": im.format, "mode": im.mode, "canvas": [w, h],
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        if im.format != "PNG":
            errors.append(f"{path}: expected PNG")
        if im.mode != "RGBA":
            errors.append(f"{path}: expected RGBA, got {im.mode}")
        alpha = im.convert("RGBA").getchannel("A")
        bbox = alpha.getbbox()
        rec["alpha_bbox"] = list(bbox) if bbox else None
        if bbox is None:
            errors.append(f"{path}: image is empty/fully transparent")
        else:
            rec["figure_height_px"] = bbox[3] - bbox[1]
            if figure_height is not None and rec["figure_height_px"] != figure_height:
                errors.append(f"{path}: figure height {rec['figure_height_px']} != {figure_height}")
            if kind in ("sprite", "animation", "object", "vfx"):
                if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == w or bbox[3] == h:
                    errors.append(f"{path}: painted pixels touch the canvas border")
        if kind in ("sprite", "animation", "object", "vfx"):
            corners = [alpha.getpixel(pt) for pt in
                       [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]]
            rec["corner_alpha"] = corners
            if any(corners):
                errors.append(f"{path}: corner alpha nonzero — background may remain")
        if kind in ("tile", "tileset") and (w % tile_size or h % tile_size):
            errors.append(f"{path}: dimensions {w}x{h} are not {tile_size}px-grid aligned")
        if pivot is not None and not (0 <= pivot[0] < w and 0 <= pivot[1] < h):
            errors.append(f"{path}: pivot {pivot} outside {w}x{h}")
        if canvas is None:
            canvas = [w, h]
        elif kind == "animation" and canvas != [w, h]:
            errors.append(f"{path}: animation canvas {[w, h]} != {canvas}")
        records.append(rec)
    return {
        "qa_status": "TECHNICAL_EXPORT_PASS" if not errors else "NOT_GAME_READY",
        "kind": kind, "pivot": list(pivot) if pivot else None,
        "target_figure_height": figure_height, "tile_size": tile_size,
        "assets": records, "errors": errors, "art_status": "ART_REVIEW_PENDING",
        "godot_status": "GODOT_NOT_TESTED",
        "limits": "Does not prove artistic quality, pixel readability, tile seams, pose consistency or Godot integration."
    }


def main():
    p = argparse.ArgumentParser(description="Rogalik D26: validate exported PNG files")
    p.add_argument("--png", type=Path, nargs="+", required=True)
    p.add_argument("--kind", choices=("sprite", "animation", "object", "tile", "tileset", "vfx"),
                   required=True)
    p.add_argument("--figure-height", type=int)
    p.add_argument("--pivot", type=int, nargs=2, metavar=("X", "Y"))
    p.add_argument("--tile-size", type=int, default=24)
    p.add_argument("--json-out", type=Path)
    args = p.parse_args()
    result = validate(args.png, args.kind, args.figure_height, args.pivot, args.tile_size)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
