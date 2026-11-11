#!/usr/bin/env python3
"""Smoke tests for scripts/verify_ui_artifact.py, using synthetic PNGs only."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_ui_artifact.py"


class VerifyUiArtifactTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.dir = Path(self.work.name)
        self.before = self.dir / "accepted.png"
        self.after = self.dir / "revised.png"
        Image.new("RGBA", (32, 24), (230, 235, 240, 255)).save(self.before)
        Image.open(self.before).save(self.after)

    def run_checker(self, *extra):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--image", str(self.after), *extra],
            capture_output=True, text=True, check=False
        )
        return proc.returncode, json.loads(proc.stdout)

    def alter(self, coordinates, fill):
        with Image.open(self.after) as im:
            clone = im.convert("RGBA")
        clone.putpixel(coordinates, fill)
        clone.save(self.after)

    def test_png_and_dimensions_pass_without_claiming_preservation(self):
        code, result = self.run_checker("--width", "32", "--height", "24")
        self.assertEqual(code, 0)
        self.assertTrue(result["image_ok"])
        self.assertFalse(result["preservation_verified"])
        self.assertTrue(result["manual_visual_review_required"])

    def test_allowed_edit_passes_with_exact_outside_freeze(self):
        self.alter((10, 10), (20, 50, 120, 255))
        code, result = self.run_checker(
            "--before", str(self.before), "--region", "8,8,6,6",
            "--width", "32", "--height", "24", "--require-change"
        )
        self.assertEqual(code, 0)
        self.assertEqual(result["changed_pixels_inside"], 1)
        self.assertEqual(result["changed_pixels_outside"], 0)
        self.assertTrue(result["preservation_verified"])

    def test_edit_outside_region_fails(self):
        self.alter((0, 0), (100, 80, 60, 255))
        code, result = self.run_checker(
            "--before", str(self.before), "--region", "8,8,6,6"
        )
        self.assertEqual(code, 1)
        self.assertFalse(result["preservation_verified"])
        self.assertEqual(result["changed_pixels_outside"], 1)
        self.assertEqual(result["changed_outside_bbox"], [0, 0, 1, 1])

    def test_alpha_change_is_detected(self):
        self.alter((0, 0), (230, 235, 240, 200))
        code, result = self.run_checker(
            "--before", str(self.before), "--region", "8,8,6,6"
        )
        self.assertEqual(code, 1)
        self.assertEqual(result["changed_pixels_outside"], 1)

    def test_no_change_when_change_required_fails(self):
        code, result = self.run_checker(
            "--before", str(self.before), "--region", "8,8,6,6",
            "--require-change"
        )
        self.assertEqual(code, 1)
        self.assertIn("authorized region did not change", result["errors"])

    def test_wrong_dimensions_fails(self):
        code, result = self.run_checker("--width", "1920", "--height", "1080")
        self.assertEqual(code, 1)
        self.assertTrue(result["image_ok"])

    def test_corrupt_png_fails(self):
        self.after.write_bytes(b"not a real PNG")
        code, result = self.run_checker()
        self.assertEqual(code, 1)
        self.assertFalse(result["image_ok"])

    def test_invalid_region_fails(self):
        code, result = self.run_checker(
            "--before", str(self.before), "--region", "30,20,8,8"
        )
        self.assertEqual(code, 1)
        self.assertIn("region exceeds image bounds", result["errors"])

    def test_missing_baseline_with_region_is_argument_error(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--image", str(self.after),
             "--region", "0,0,1,1"],
            capture_output=True, text=True, check=False
        )
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
