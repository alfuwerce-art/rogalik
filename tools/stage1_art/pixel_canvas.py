"""Small deterministic pixel-art canvas used to author Rogalik stage-1 sprites.

Everything is drawn at final resolution (1 px = 1 px) with hard edges; the
result is written as PNG and then imported into Pixelorama through
``tools/pixel_pipeline`` before the game ever sees it.  No antialiasing, no
sub-pixel coordinates, no font rendering.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

RGBA = tuple[int, int, int, int]
CLEAR: RGBA = (0, 0, 0, 0)


@dataclass(frozen=True)
class Palette:
    """Four-step ramp plus an explicit outline colour for one material."""

    outline: RGBA
    shadow: RGBA
    base: RGBA
    light: RGBA
    highlight: RGBA


def hex_rgba(value: str, alpha: int = 255) -> RGBA:
    value = value.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        alpha,
    )


def shade(color: RGBA, factor: float) -> RGBA:
    return (
        max(0, min(255, round(color[0] * factor))),
        max(0, min(255, round(color[1] * factor))),
        max(0, min(255, round(color[2] * factor))),
        color[3],
    )


def mix(a: RGBA, b: RGBA, t: float) -> RGBA:
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
        round(a[3] + (b[3] - a[3]) * t),
    )


class Region:
    """A set of integer pixels, built from simple primitives."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.pixels: set[tuple[int, int]] = set()

    def add(self, x: int, y: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels.add((x, y))

    def rect(self, x0: float, y0: float, x1: float, y1: float) -> "Region":
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.add(x, y)
        return self

    def ellipse(self, cx: float, cy: float, rx: float, ry: float) -> "Region":
        if rx <= 0 or ry <= 0:
            return self
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                dx = (x - cx) / rx
                dy = (y - cy) / ry
                if dx * dx + dy * dy <= 1.0:
                    self.add(x, y)
        return self

    def capsule(self, x0: float, y0: float, x1: float, y1: float, radius: float) -> "Region":
        steps = max(2, int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1)
        for step in range(steps + 1):
            t = step / steps
            self.ellipse(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, radius, radius)
        return self

    def polygon(self, points: list[tuple[float, float]]) -> "Region":
        """Fill a convex polygon (points in any winding order)."""
        if len(points) < 3:
            return self
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                if _inside_convex(points, x + 0.5, y + 0.5):
                    self.add(x, y)
        return self

    def line(self, x0: int, y0: int, x1: int, y1: int) -> "Region":
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.add(x, y)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return self

    def union(self, other: "Region") -> "Region":
        self.pixels |= other.pixels
        return self

    def shifted(self, dx: int, dy: int) -> "Region":
        out = Region(self.width, self.height)
        for x, y in self.pixels:
            out.add(x + dx, y + dy)
        return out

    def mirrored_h(self) -> "Region":
        out = Region(self.width, self.height)
        for x, y in self.pixels:
            out.add(self.width - 1 - x, y)
        return out

    def translated_into(self, width: int, height: int, dx: int, dy: int) -> "Region":
        out = Region(width, height)
        for x, y in self.pixels:
            out.add(x + dx, y + dy)
        return out

    def erase(self, other: "Region") -> "Region":
        self.pixels -= other.pixels
        return self

    def empty(self) -> bool:
        return not self.pixels


def _inside_convex(points: list[tuple[float, float]], px: float, py: float) -> bool:
    sign = 0
    count = len(points)
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if abs(cross) < 1e-9:
            continue
        current = 1 if cross > 0 else -1
        if sign == 0:
            sign = current
        elif sign != current:
            return False
    return True


def _hash(x: int, y: int, seed: int) -> int:
    value = (x * 374761393 + y * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    value = (value ^ (value >> 13)) * 1274126177 & 0xFFFFFFFF
    return (value ^ (value >> 16)) & 0xFFFFFFFF


@dataclass
class Material:
    palette: Palette
    texture: int = 0  # 0 = flat ramp, higher = more speckle
    outline: bool = True


class Canvas:
    """RGBA pixel canvas with multi-material bevelled shading."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.image = Image.new("RGBA", (width, height), CLEAR)
        self.pixels = self.image.load()

    # -- low level -----------------------------------------------------
    def put(self, x: int, y: int, color: RGBA) -> None:
        if 0 <= x < self.width and 0 <= y < self.height and color[3] > 0:
            self.pixels[x, y] = color

    def outline_region(
        self,
        region: Region,
        color: RGBA,
        *,
        diagonals: bool = False,
    ) -> None:
        """Put a 1 px outline around (not inside) ``region``."""
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonals:
            offsets += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        ring: set[tuple[int, int]] = set()
        for x, y in region.pixels:
            for dx, dy in offsets:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in region.pixels:
                    ring.add((nx, ny))
        for x, y in sorted(ring, key=lambda p: (p[1], p[0])):
            self.put(x, y, color)

    def paint(
        self,
        region: Region,
        material: Material,
        *,
        seed: int = 0,
        light_dir: tuple[int, int] = (-1, -1),
        speckle_mix: float = 0.0,
    ) -> None:
        """Paint ``region`` as a bevelled volume lit from ``light_dir``."""
        palette = material.palette
        lx, ly = light_dir
        if material.outline:
            self.outline_region(region, palette.outline, diagonals=True)
        for x, y in sorted(region.pixels, key=lambda p: (p[1], p[0])):
            if (x + lx, y + ly) not in region.pixels:
                color = palette.highlight
            elif (x + lx * 2, y + ly * 2) not in region.pixels:
                color = palette.light
            elif (x - lx, y - ly) not in region.pixels or (x - lx * 2, y - ly * 2) not in region.pixels:
                color = palette.shadow
            else:
                color = palette.base
            if material.texture and _hash(x, y, seed + 17) % 100 < material.texture:
                color = palette.shadow if color == palette.base else color
            if speckle_mix > 0 and _hash(x, y, seed + 91) % 100 < speckle_mix * 100:
                color = mix(color, palette.highlight, 0.35)
            self.put(x, y, color)

    def fill_region(self, region: Region, color: RGBA) -> None:
        for x, y in region.pixels:
            self.put(x, y, color)

    def stamp(self, other: Canvas, dx: int = 0, dy: int = 0) -> None:
        for y in range(other.height):
            for x in range(other.width):
                pixel = other.pixels[x, y]
                if pixel[3] > 0:
                    self.put(x + dx, y + dy, pixel)

    def save(self, path) -> None:
        self.image.save(path)


def sheet_variant(canvas: Canvas, width: int, height: int) -> Image.Image:
    """Crop/pad a canvas to a fixed cell size (top-left anchored)."""
    out = Image.new("RGBA", (width, height), CLEAR)
    out.paste(canvas.image, (0, 0))
    return out
