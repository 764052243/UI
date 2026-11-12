"""Synthetic-only tests: original login design and user screenshot are not stored in repo."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_micro_edit.py"
spec = importlib.util.spec_from_file_location("verify_micro_edit", SCRIPT)
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)


class PreciseMicroEditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.before = Image.new("RGBA", (80, 40), (12, 44, 48, 255))
        # Left side: CONNECT word approximated as white ink; right warm panel.
        for x in range(10, 42):
            for y in range(8, 15):
                self.before.putpixel((x, y), (185, 204, 210, 255))
        for x in range(10, 42):
            for y in range(23, 25):
                self.before.putpixel((x, y), (52, 85, 88, 255))
        for x in range(50, 80):
            for y in range(40):
                self.before.putpixel((x, y), (242, 239, 228, 255))
        self.after = self.before.copy()
        self.plan = {
            "schema_version": "1.0", "baseline_reference_id": "approved-login",
            "target_id": "connect-underline",
            "allowed_regions": [[10, 23, 32, 2]],
            "protected_regions": [[10, 8, 32, 7], [50, 0, 30, 40]],
            "color_direction": "darken",
            "pixel_tolerance": 0,
            "min_changed_pixels": 32,
            "max_changed_pixels": 64,
            "max_channel_delta": 35,
        }
        self.darken()

    def darken(self):
        for x in range(10, 42):
            for y in range(23, 25):
                self.after.putpixel((x, y), (38, 65, 67, 255))

    def result(self):
        return lib.check(self.before, self.after, self.plan)

    def test_only_darkened_connect_underline_passes(self):
        r = self.result()
        self.assertEqual(r["status"], "PASS", r["errors"])
        self.assertEqual(r["target_changed_pixels"], 64)
        self.assertEqual(r["changed_pixels_outside_target"], 0)
        self.assertLess(r["mean_target_luminance_delta"], 0)

    def test_unchanged_image_must_fail(self):
        self.after = self.before.copy()
        self.assertTrue(any("target unchanged" in e for e in self.result()["errors"]))

    def test_line_brightened_instead_of_darkened_fails(self):
        for x in range(10, 42):
            for y in range(23, 25):
                self.after.putpixel((x, y), (80, 110, 115, 255))
        self.assertTrue(any("wrong luminance direction" in e for e in self.result()["errors"]))

    def test_other_left_background_color_change_fails(self):
        self.after.putpixel((5, 5), (0, 24, 34, 255))
        r = self.result()
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["changed_pixels_outside_target"], 1)

    def test_right_login_panel_gray_gradient_fails(self):
        for y in range(40):
            self.after.putpixel((60, y), (145, 144, 145, 255))
        self.assertEqual(self.result()["status"], "FAIL")
        self.assertGreater(self.result()["changed_pixels_in_protected_regions"], 0)

    def test_connect_word_modified_fails(self):
        self.after.putpixel((20, 10), (0, 15, 18, 255))
        self.assertTrue(any("outside authorized" in e for e in self.result()["errors"]))

    def test_shifted_line_cannot_pass_as_same_edit(self):
        for x in range(10, 42):
            self.after.putpixel((x, 23), self.before.getpixel((x, 23)))
        for x in range(10, 42):
            self.after.putpixel((x, 26), (38, 65, 67, 255))
        self.assertEqual(self.result()["status"], "FAIL")

    def test_line_overpaint_too_dark_fails_delta_gate(self):
        for x in range(10, 42):
            for y in range(23, 25):
                self.after.putpixel((x, y), (0, 0, 0, 255))
        self.assertTrue(any("RGBA change exceeds" in e for e in self.result()["errors"]))

    def test_not_allowed_to_widen_line_to_more_pixels(self):
        self.plan["allowed_regions"] = [[10, 22, 32, 3]]
        for x in range(10, 42):
            self.after.putpixel((x, 22), (20, 25, 30, 255))
        self.assertTrue(any("modified too many" in e for e in self.result()["errors"]))

    def test_overlap_protected_area_still_cannot_change(self):
        self.plan["protected_regions"].append([25, 23, 10, 2])
        self.assertEqual(self.result()["status"], "FAIL")
        self.assertEqual(self.result()["changed_pixels_in_protected_regions"], 20)

    def test_canvas_change_fails(self):
        with self.assertRaisesRegex(ValueError, "dimensions must match"):
            lib.check(self.before, self.after.resize((90, 40)), self.plan)

    def test_ill_formed_allowed_roi_rejected(self):
        self.plan["allowed_regions"] = [[10, 22, 100, 2]]
        with self.assertRaisesRegex(ValueError, "exceeds canvas"):
            self.result()

    def test_no_approved_baseline_reference_rejected(self):
        self.plan["baseline_reference_id"] = ""
        with self.assertRaisesRegex(ValueError, "baseline_reference_id"):
            self.result()

    def test_pixel_tolerance_invalid_rejected(self):
        self.plan["pixel_tolerance"] = -1
        with self.assertRaisesRegex(ValueError, "pixel_tolerance"):
            self.result()

    def test_multiple_narrow_regions_not_whole_rectangle(self):
        self.plan["allowed_regions"] = [[10, 23, 10, 2], [30, 23, 12, 2]]
        self.after = self.before.copy()
        for x in list(range(10, 20)) + list(range(30, 42)):
            for y in range(23, 25):
                self.after.putpixel((x, y), (38, 65, 67, 255))
        self.plan["min_changed_pixels"] = 20
        r = self.result()
        self.assertEqual(r["status"], "PASS", r["errors"])
        self.after.putpixel((25, 23), (38, 65, 67, 255))
        self.assertEqual(self.result()["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
