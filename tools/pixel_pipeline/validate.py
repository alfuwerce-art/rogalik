"""Read-only checks for PNG sprites, sprite sheets and tilesets.

Every check returns a structured record so the same report can be printed, stored
as JSON, or returned from a Cordis tool. Nothing here writes to the files except
an explicit report path chosen by the caller.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


@dataclass
class Check:
    name: str
    status: str
    detail: str

    def as_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass
class Report:
    target: str
    kind: str
    checks: list[Check] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def status(self) -> str:
        if any(check.status == FAIL for check in self.checks):
            return FAIL
        return PASS

    def add(self, name: str, status: str, detail: str) -> None:
        self.checks.append(Check(name, status, detail))

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "kind": self.kind,
            "target": self.target,
            "checks": [check.as_dict() for check in self.checks],
            "metrics": self.metrics,
            "artifacts": self.artifacts,
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path


def _alpha_summary(image: Image.Image) -> dict:
    alpha = image.getchannel("A")
    histogram = alpha.histogram()
    transparent = histogram[0]
    opaque = histogram[255]
    total = image.width * image.height
    return {
        "has_alpha": True,
        "transparent_pixels": transparent,
        "opaque_pixels": opaque,
        "partial_pixels": total - transparent - opaque,
    }


def inspect_png(path: str | Path) -> dict:
    path = Path(path)
    with Image.open(path) as image:
        image.load()
        rgba = image.convert("RGBA")
        info = {
            "path": str(path),
            "exists": True,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "bytes": path.stat().st_size,
            "unique_colors": len(rgba.getcolors(maxcolors=1 << 24) or []),
        }
        info.update(_alpha_summary(rgba))
        return info


def validate_png(path: str | Path) -> Report:
    """Single-image sanity check: exists, decodes, square pixels, real palette."""
    path = Path(path)
    report = Report(target=str(path), kind="png")
    if not path.is_file():
        report.add("file_exists", FAIL, f"file not found: {path}")
        return report
    report.add("file_exists", PASS, f"{path.stat().st_size} bytes")

    try:
        info = inspect_png(path)
    except Exception as exc:  # pragma: no cover - corrupt file path
        report.add("decodes", FAIL, f"Pillow cannot open the file: {exc}")
        return report

    report.metrics.update(info)
    report.add("decodes", PASS, f"{info['width']}x{info['height']} {info['mode']}")

    if info["transparent_pixels"] == 0:
        report.add(
            "transparency",
            WARN,
            "no fully transparent pixels: sprites normally need an alpha background",
        )
    else:
        share = info["transparent_pixels"] / (info["width"] * info["height"]) * 100
        report.add("transparency", PASS, f"{share:.1f}% of pixels fully transparent")

    if info["unique_colors"] > 256:
        report.add("palette", WARN, f"{info['unique_colors']} colours: not an indexed pixel-art palette")
    else:
        report.add("palette", PASS, f"{info['unique_colors']} distinct colours")
    return report


def validate_sheet(
    path: str | Path,
    frame_width: int,
    frame_height: int | None = None,
    expected_frames: int | None = None,
    require_transparency: bool = True,
) -> Report:
    """Validate a horizontal sprite sheet and equal frame geometry."""
    path = Path(path)
    frame_height = frame_height or frame_width
    report = Report(target=str(path), kind="sprite_sheet")

    base = validate_png(path)
    report.checks.extend(base.checks)
    report.metrics.update(base.metrics)
    if base.status == FAIL:
        return report

    width, height = base.metrics["width"], base.metrics["height"]
    if frame_width <= 0 or frame_height <= 0:
        report.add("frame_size", FAIL, "frame size must be positive")
        return report

    if width % frame_width != 0 or height % frame_height != 0:
        report.add(
            "frame_geometry",
            FAIL,
            f"{width}x{height} is not divisible by {frame_width}x{frame_height}",
        )
        return report

    columns = width // frame_width
    rows = height // frame_height
    frames = columns * rows
    report.metrics.update(
        {
            "frame_width": frame_width,
            "frame_height": frame_height,
            "columns": columns,
            "rows": rows,
            "frames": frames,
        }
    )
    report.add("frame_geometry", PASS, f"{frames} frames of {frame_width}x{frame_height} ({columns}x{rows})")

    if expected_frames is not None and frames != expected_frames:
        report.add(
            "frame_count",
            FAIL,
            f"expected {expected_frames} frames, sheet contains {frames}",
        )
    elif expected_frames is not None:
        report.add("frame_count", PASS, f"{frames} frames as expected")

    if require_transparency and base.metrics["transparent_pixels"] == 0:
        report.add("frame_transparency", FAIL, "sheet has no transparent background")

    # Every frame must contain some opaque pixel, otherwise an empty/misaligned
    # frame silently ships to the engine.
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        empty = []
        for row in range(rows):
            for column in range(columns):
                box = (
                    column * frame_width,
                    row * frame_height,
                    (column + 1) * frame_width,
                    (row + 1) * frame_height,
                )
                alpha = rgba.crop(box).getchannel("A")
                if alpha.getextrema()[1] == 0:
                    empty.append(row * columns + column)
        if empty:
            report.add("empty_frames", FAIL, f"frames without pixels: {empty}")
        else:
            report.add("empty_frames", PASS, "every frame contains visible pixels")

        # Frame anchors: the bottom row of each frame should be shared so the
        # sprite does not jitter vertically when frames are swapped.
        bottoms = []
        for column in range(columns):
            box = (column * frame_width, 0, (column + 1) * frame_width, height)
            bbox = rgba.crop(box).getbbox()
            bottoms.append(bbox[3] if bbox else None)
        report.metrics["frame_bottoms"] = bottoms
        if len(set(bottoms)) > 1:
            report.add("frame_anchor", WARN, f"frame bottoms differ: {bottoms}")
        else:
            report.add("frame_anchor", PASS, f"all frames end at y={bottoms[0]}")
    return report


def validate_tileset(path: str | Path, tile_size: int) -> Report:
    """Check a square tileset for consistent geometry and seamless wrapping.

    A tile is considered repeatable when the pixels on its right edge are close
    to the pixels on its left edge (and bottom/top respectively). That is the
    property a tilemap needs for a corridor or a wall run not to show a seam.
    """
    path = Path(path)
    report = Report(target=str(path), kind="tileset")
    base = validate_png(path)
    report.checks.extend(base.checks)
    report.metrics.update(base.metrics)
    if base.status == FAIL:
        return report

    width, height = base.metrics["width"], base.metrics["height"]
    if tile_size <= 0 or width % tile_size or height % tile_size:
        report.add("tile_geometry", FAIL, f"{width}x{height} is not divisible by {tile_size}")
        return report

    columns, rows = width // tile_size, height // tile_size
    report.metrics.update(
        {"tile_size": tile_size, "columns": columns, "rows": rows, "tiles": columns * rows}
    )
    report.add("tile_geometry", PASS, f"{columns * rows} tiles of {tile_size}x{tile_size}")

    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        seam_scores = []
        for row in range(rows):
            for column in range(columns):
                left = (column * tile_size, row * tile_size)
                tile = rgba.crop(
                    (left[0], left[1], left[0] + tile_size, left[1] + tile_size)
                )
                edge_x = _edge_difference(tile, vertical=True)
                edge_y = _edge_difference(tile, vertical=False)
                seam_scores.append(
                    {"column": column, "row": row, "x": round(edge_x, 2), "y": round(edge_y, 2)}
                )
        report.metrics["seams"] = seam_scores
        worst = max(max(seam["x"], seam["y"]) for seam in seam_scores) if seam_scores else 0.0
        report.metrics["worst_seam"] = round(worst, 2)
        if worst == 0:
            report.add("tile_repeat", PASS, "every tile wraps without a seam")
        elif worst <= 12:
            report.add("tile_repeat", WARN, f"maximum edge difference {worst:.1f}/255")
        else:
            report.add("tile_repeat", WARN, f"tiles are not seamless (max edge difference {worst:.1f}/255)")
    return report


def _edge_difference(tile: Image.Image, vertical: bool) -> float:
    """Mean absolute difference between the two opposite edges of a tile."""
    width, height = tile.size
    total = 0.0
    count = 0
    if vertical:
        for y in range(height):
            left = tile.getpixel((0, y))
            right = tile.getpixel((width - 1, y))
            total += sum(abs(a - b) for a, b in zip(left, right)) / 4
            count += 1
    else:
        for x in range(width):
            top = tile.getpixel((x, 0))
            bottom = tile.getpixel((x, height - 1))
            total += sum(abs(a - b) for a, b in zip(top, bottom)) / 4
            count += 1
    return total / count if count else 0.0


def report_text(report: Report) -> str:
    lines = [f"{report.status}  {report.kind}: {report.target}"]
    for check in report.checks:
        lines.append(f"  [{check.status}] {check.name}: {check.detail}")
    for artifact in report.artifacts:
        lines.append(f"  artifact: {artifact}")
    return "\n".join(lines)


def validate_many(paths: Iterable[str | Path]) -> list[Report]:
    return [validate_png(path) for path in paths]
