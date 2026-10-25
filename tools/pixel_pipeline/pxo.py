"""Build a Pixelorama `.pxo` project from RGBA frames.

A `.pxo` file is a ZIP archive:

    mimetype                     application/x-pixelorama
    data.json                    project metadata (Pixelorama 1.2.x, pxo_version 7)
    preview.png                  thumbnail shown in file browsers
    image_data/frames/<n>/layer_<i>          raw RGBA8 pixels, row-major
    image_data/frames/<n>/indices_layer_<i>  indexed-colour indices (1 byte in RGBA mode)

Pixelorama itself opens and exports these projects, so generated artwork still
goes through the real editor/CLI instead of a look-alike PNG writer.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image

PXO_VERSION = 7
PIXELORAMA_VERSION = "v1.2.3-stable"
COLOR_MODE_RGBA = 5

_EMPTY_UI_COLOR = "(0.0, 0.0, 0.0, 0.0)"


def _palette_json(colors: Sequence[tuple[int, int, int]]) -> str:
    entries = []
    for index, (r, g, b) in enumerate(colors):
        entries.append(
            {
                "color": f"({r / 255:.4f}, {g / 255:.4f}, {b / 255:.4f}, 1.0)",
                "index": index,
            }
        )
    payload = {"colors": entries}
    return json.dumps(payload, indent=1)


def _layer(name: str) -> dict:
    return {
        "animated_params": 'Dictionary[String, Dictionary]({\n"opacity": {}\n})',
        "blend_mode": 0,
        "clipping_mask": False,
        "effects": [],
        "locked": False,
        "metadata": {},
        "name": name,
        "new_cels_linked": False,
        "opacity": 1.0,
        "parent": -1,
        "type": 0,
        "ui_color": _EMPTY_UI_COLOR,
        "visible": True,
    }


def _cel() -> dict:
    return {
        "metadata": {},
        "opacity": 1.0,
        "ui_color": _EMPTY_UI_COLOR,
        "z_index": 0,
    }


def _project_data(
    width: int,
    height: int,
    frame_count: int,
    fps: float,
    layer_name: str,
    tags: Iterable[dict],
    palette: Sequence[tuple[int, int, int]],
    export_name: str,
) -> dict:
    return {
        "author_company": "",
        "author_contact": "",
        "author_display_name": "",
        "author_real_name": "",
        "brushes": [],
        "color_mode": COLOR_MODE_RGBA,
        "current_frame": 0,
        "current_layer": 0,
        "export_profile": {
            "crop_mode": "0",
            "current_tab": "0",
            "direction": "0",
            "directory_path": '""',
            "erase_unselected_area": "false",
            "export_json": "false",
            "export_layers": "0",
            "file_format": "0",
            "file_name": json.dumps(export_name),
            "frame_current_tag": "0",
            "include_tag_in_filename": "false",
            "interpolation": "0",
            "lines_count": "1",
            "new_dir_for_each_frame_tag": "false",
            "number_of_digits": "4",
            "number_of_frames": str(frame_count),
            "orientation": "0",
            "repeat_count": "0",
            "resize": "100",
            "save_quality": "0.75",
            "separator_character": '"_"',
            "sheet_layers_as_separate_files": "false",
            "split_layers": "false",
        },
        "fps": float(fps),
        "frames": [
            {"cels": [_cel()], "duration": 1.0, "metadata": {}}
            for _ in range(frame_count)
        ],
        "guides": [],
        "layers": [_layer(layer_name)],
        "license": "",
        "metadata": {},
        "next_keyframe_id": 0,
        "palettes": [{"Default": _palette_json(palette)}],
        "pixelorama_version": PIXELORAMA_VERSION,
        "project_current_palette_name": "Default",
        "pxo_version": PXO_VERSION,
        "reference_images": [],
        "size_x": width,
        "size_y": height,
        "symmetry_points": [],
        "tags": list(tags),
        "tile_mode_x_basis_x": 1.0,
        "tile_mode_x_basis_y": 0.0,
        "tile_mode_y_basis_x": 0.0,
        "tile_mode_y_basis_y": 1.0,
        "tilesets": [],
        "user_data": "",
        "vanishing_points": [],
    }


def build_pxo(
    output: str | Path,
    frames: Sequence[Image.Image],
    *,
    fps: float = 8.0,
    layer_name: str = "Layer 1",
    tags: Sequence[dict] | None = None,
    palette: Sequence[tuple[int, int, int]] | None = None,
) -> Path:
    """Write ``frames`` (equal-size RGBA images) as a Pixelorama project."""
    if not frames:
        raise ValueError("at least one frame is required")

    output = Path(output)
    size = frames[0].size
    for index, frame in enumerate(frames):
        if frame.size != size:
            raise ValueError(
                f"frame {index} is {frame.size[0]}x{frame.size[1]}, expected {size[0]}x{size[1]}"
            )
        if frame.mode != "RGBA":
            raise ValueError(f"frame {index} must be RGBA, got {frame.mode}")

    if palette is None:
        palette = _extract_palette(frames)
    export_name = output.stem

    data = _project_data(
        size[0],
        size[1],
        len(frames),
        fps,
        layer_name,
        tags or [],
        palette,
        export_name,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        # mimetype first and uncompressed, as the format expects.
        archive.writestr(
            zipfile.ZipInfo("mimetype"), "application/x-pixelorama", zipfile.ZIP_STORED
        )
        archive.writestr("data.json", json.dumps(data, indent=1))
        archive.writestr("preview.png", _preview_png(frames))
        for index, frame in enumerate(frames, start=1):
            archive.writestr(f"image_data/frames/{index}/layer_1", frame.tobytes())
            archive.writestr(f"image_data/frames/{index}/indices_layer_1", b"\x00")
    return output


def _preview_png(frames: Sequence[Image.Image]) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    frames[0].save(buffer, format="PNG")
    return buffer.getvalue()


def _extract_palette(frames: Sequence[Image.Image], limit: int = 32):
    seen: list[tuple[int, int, int]] = []
    for frame in frames:
        for _count, color in sorted(frame.getcolors(maxcolors=1 << 24) or [], reverse=True):
            rgb = color[:3]
            if color[3] == 0:
                continue
            if rgb not in seen:
                seen.append(rgb)
            if len(seen) >= limit:
                return seen
    return seen or [(0, 0, 0)]


def frame_tag(name: str, start: int, end: int, color: str = "(1, 1, 1, 1)") -> dict:
    """Animation tag spanning ``start``..``end`` frames (inclusive, 0-based)."""
    if start < 0 or end < start:
        raise ValueError("invalid tag range")
    return {"color": color, "from": start, "name": name, "to": end}
