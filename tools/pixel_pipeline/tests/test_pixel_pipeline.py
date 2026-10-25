"""Unit tests for the Rogalik pixel pipeline (no Pixelorama required).

Run from the repository root:

    set PYTHONPATH=tools
    python -m unittest discover -s tools/pixel_pipeline/tests -v

The end-to-end Pixelorama export test is skipped unless ROGALIK_SLOW_TESTS=1.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
import unittest
import zipfile
import uuid
from pathlib import Path

from PIL import Image

from pixel_pipeline import atlas, pixelorama, pxo, validate
from pixel_pipeline.examples import make_test_sprite


@contextlib.contextmanager
def _tempdir():
    """Workspace-local scratch directory.

    ``tempfile`` helpers either chmod during cleanup or create directories with a
    restrictive mode, and the Windows sandbox denies both. A plain ``mkdir`` of a
    unique name under the checkout stays writable, so tests use that instead.
    """
    base = Path(os.environ.get("ROGALIK_TEST_TMP", "build/test-tmp"))
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case-{uuid.uuid4().hex[:10]}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sheet(path: Path, frames: int = 4, size: int = 32) -> Path:
    images = make_test_sprite.make_frames()[:frames]
    sheet = Image.new("RGBA", (size * len(images), size), (0, 0, 0, 0))
    for index, frame in enumerate(images):
        sheet.paste(frame, (index * size, 0))
    sheet.save(path)
    return path


class PxoTests(unittest.TestCase):
    def test_build_pxo_structure(self):
        with _tempdir() as tmp_path:
            tmp = str(tmp_path)
            sheet = _sheet(tmp_path / "walk.png")
            with Image.open(sheet) as image:
                frames = [
                    image.convert("RGBA").crop((i * 32, 0, i * 32 + 32, 32)) for i in range(4)
                ]
            project = pxo.build_pxo(
                tmp_path / "walk.pxo",
                frames,
                fps=8.0,
                tags=[pxo.frame_tag("walk", 0, 3)],
            )
            self.assertTrue(project.is_file())
            with zipfile.ZipFile(project) as archive:
                names = archive.namelist()
                self.assertEqual(names[0], "mimetype")
                self.assertEqual(archive.read("mimetype"), b"application/x-pixelorama")
                data = json.loads(archive.read("data.json"))
                self.assertEqual(data["size_x"], 32)
                self.assertEqual(data["size_y"], 32)
                self.assertEqual(len(data["frames"]), 4)
                self.assertEqual(data["tags"][0]["name"], "walk")
                layer = archive.read("image_data/frames/1/layer_1")
                self.assertEqual(len(layer), 32 * 32 * 4)
                self.assertIn("preview.png", names)

    def test_mismatched_frame_size_is_rejected(self):
        with _tempdir() as tmp_path:
            frames = [Image.new("RGBA", (32, 32)), Image.new("RGBA", (16, 16))]
            with self.assertRaises(ValueError):
                pxo.build_pxo(tmp_path / "bad.pxo", frames)


class SheetValidationTests(unittest.TestCase):
    def test_valid_sheet_passes(self):
        with _tempdir() as tmp_path:
            sheet = _sheet(tmp_path / "walk.png")
            report = validate.validate_sheet(sheet, 32, expected_frames=4)
            self.assertEqual(report.status, validate.PASS, report.as_dict())
            self.assertEqual(report.metrics["frames"], 4)

    def test_wrong_divisor_fails(self):
        with _tempdir() as tmp_path:
            sheet = _sheet(tmp_path / "walk.png")
            report = validate.validate_sheet(sheet, 30)
            self.assertEqual(report.status, validate.FAIL)
            names = {check.name for check in report.checks if check.status == validate.FAIL}
            self.assertIn("frame_geometry", names)

    def test_wrong_frame_count_fails(self):
        with _tempdir() as tmp_path:
            sheet = _sheet(tmp_path / "walk.png")
            report = validate.validate_sheet(sheet, 32, expected_frames=6)
            self.assertEqual(report.status, validate.FAIL)

    def test_empty_frame_fails(self):
        with _tempdir() as tmp_path:
            sheet = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
            sheet.paste(make_test_sprite.make_frames()[0], (0, 0))
            path = tmp_path / "half.png"
            sheet.save(path)
            report = validate.validate_sheet(path, 32)
            self.assertEqual(report.status, validate.FAIL)
            self.assertIn("empty_frames", {check.name for check in report.checks})

    def test_missing_file_fails(self):
        report = validate.validate_png(Path(tempfile.gettempdir()) / "definitely-absent.png")
        self.assertEqual(report.status, validate.FAIL)


class AtlasTests(unittest.TestCase):
    def test_atlas_round_trip(self):
        with _tempdir() as tmp_path:
            tmp = str(tmp_path)
            sheet = _sheet(tmp_path / "walk.png")
            info = atlas.build_atlas(sheet, 32, 32, tmp_path / "atlas", columns=2)
            validation = atlas.validate_atlas(info["metadata"])
            self.assertEqual(validation["status"], "PASS", validation)
            with Image.open(info["atlas"]) as image:
                self.assertEqual(image.size, (64, 64))
            metadata = json.loads(Path(info["metadata"]).read_text(encoding="utf-8"))
            self.assertEqual(len(metadata["frames"]), 4)
            self.assertEqual(metadata["frames"][3]["y"], 32)

    def test_atlas_detects_broken_metadata(self):
        with _tempdir() as tmp_path:
            tmp = str(tmp_path)
            sheet = _sheet(tmp_path / "walk.png")
            info = atlas.build_atlas(sheet, 32, 32, tmp_path / "atlas")
            metadata_path = Path(info["metadata"])
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["frames"][0]["x"] = 9999
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            self.assertEqual(atlas.validate_atlas(metadata_path)["status"], "FAIL")


class TilesetTests(unittest.TestCase):
    def test_seamless_tile_passes(self):
        with _tempdir() as tmp_path:
            tile = Image.new("RGBA", (16, 16), (40, 40, 40, 255))
            path = tmp_path / "tiles.png"
            tile.save(path)
            report = validate.validate_tileset(path, 16)
            self.assertEqual(report.status, validate.PASS)
            self.assertEqual(report.metrics["worst_seam"], 0)

    def test_seamed_tile_is_reported(self):
        with _tempdir() as tmp_path:
            tile = Image.new("RGBA", (16, 16), (40, 40, 40, 255))
            for y in range(16):
                tile.putpixel((15, y), (200, 10, 10, 255))
            path = tmp_path / "tiles.png"
            tile.save(path)
            report = validate.validate_tileset(path, 16)
            self.assertGreater(report.metrics["worst_seam"], 0)


@unittest.skipUnless(os.environ.get("ROGALIK_SLOW_TESTS") == "1", "set ROGALIK_SLOW_TESTS=1")
class PixeloramaIntegrationTests(unittest.TestCase):
    def test_export_through_pixelorama(self):
        with _tempdir() as tmp_path:
            tmp = str(tmp_path)
            sheet = _sheet(tmp_path / "walk.png")
            with Image.open(sheet) as image:
                frames = [
                    image.convert("RGBA").crop((i * 32, 0, i * 32 + 32, 32)) for i in range(4)
                ]
            project = pxo.build_pxo(tmp_path / "walk.pxo", frames, tags=[pxo.frame_tag("walk", 0, 3)])
            result = pixelorama.export_project(project, tmp_path / "out", spritesheet=True, keep_name="walk")
            self.assertTrue(result.ok, result.as_dict())
            self.assertEqual(len(result.files), 1)
            with Image.open(result.files[0]) as exported:
                self.assertEqual(exported.size, (128, 32))


if __name__ == "__main__":
    unittest.main()


