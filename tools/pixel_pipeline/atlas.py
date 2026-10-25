"""Sprite-sheet -> atlas packing with Godot-friendly JSON metadata."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image


def _grid(frames: int, columns: int | None) -> tuple[int, int]:
    columns = columns or math.ceil(math.sqrt(frames))
    columns = max(1, min(columns, frames))
    rows = math.ceil(frames / columns)
    return columns, rows


def build_atlas(
    sheet: str | Path,
    frame_width: int,
    frame_height: int,
    output_dir: str | Path,
    *,
    columns: int | None = None,
    name: str | None = None,
) -> dict:
    """Split a horizontal sheet into frames and repack them into a square-ish atlas."""
    sheet = Path(sheet)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = name or sheet.stem

    with Image.open(sheet) as image:
        rgba = image.convert("RGBA")
        if rgba.width % frame_width or rgba.height % frame_height:
            raise ValueError(
                f"{rgba.width}x{rgba.height} is not divisible by {frame_width}x{frame_height}"
            )
        source_columns = rgba.width // frame_width
        source_rows = rgba.height // frame_height
        frames = [
            rgba.crop(
                (
                    column * frame_width,
                    row * frame_height,
                    (column + 1) * frame_width,
                    (row + 1) * frame_height,
                )
            )
            for row in range(source_rows)
            for column in range(source_columns)
        ]

    columns, rows = _grid(len(frames), columns)
    atlas = Image.new("RGBA", (columns * frame_width, rows * frame_height), (0, 0, 0, 0))
    entries = []
    for index, frame in enumerate(frames):
        column, row = index % columns, index // columns
        x, y = column * frame_width, row * frame_height
        atlas.paste(frame, (x, y))
        entries.append(
            {
                "index": index,
                "name": f"frame_{index:02d}",
                "x": x,
                "y": y,
                "w": frame_width,
                "h": frame_height,
            }
        )

    png_path = output_dir / f"{name}_atlas.png"
    json_path = output_dir / f"{name}_atlas.json"
    atlas.save(png_path)
    metadata = {
        "texture": png_path.name,
        "frame_width": frame_width,
        "frame_height": frame_height,
        "columns": columns,
        "rows": rows,
        "frames": entries,
    }
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {
        "atlas": str(png_path),
        "metadata": str(json_path),
        "frames": len(entries),
        "size": [atlas.width, atlas.height],
    }


def validate_atlas(metadata_path: str | Path) -> dict:
    """Verify atlas metadata against the texture it points at."""
    metadata_path = Path(metadata_path)
    problems: list[str] = []
    if not metadata_path.is_file():
        return {"status": "FAIL", "problems": [f"metadata not found: {metadata_path}"]}

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    texture = metadata_path.parent / metadata.get("texture", "")
    if not texture.is_file():
        problems.append(f"texture not found: {texture}")
        return {"status": "FAIL", "problems": problems, "metadata": str(metadata_path)}

    with Image.open(texture) as image:
        width, height = image.size
    for frame in metadata.get("frames", []):
        if frame["x"] < 0 or frame["y"] < 0:
            problems.append(f"frame {frame['index']} has a negative origin")
        if frame["x"] + frame["w"] > width or frame["y"] + frame["h"] > height:
            problems.append(f"frame {frame['index']} exceeds the {width}x{height} texture")

    expected = metadata.get("columns", 0) * metadata.get("rows", 0)
    if expected and expected != len(metadata.get("frames", [])):
        problems.append(f"declared grid holds {expected} cells but {len(metadata['frames'])} frames exist")

    return {
        "status": "FAIL" if problems else "PASS",
        "problems": problems,
        "metadata": str(metadata_path),
        "texture": str(texture),
        "frames": len(metadata.get("frames", [])),
    }
