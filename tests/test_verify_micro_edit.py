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
        # Synthetic foreground label and adjacent light panel for protected-region regression.
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

    def configure_underline_move(self):
        # Text ends at y=15. Old underline y=23..24 (gap 8px),
        # new underline y=17..18 (gap 2px) is closer and darker.
        self.plan["allowed_regions"] = [[10, 23, 32, 2], [10, 17, 32, 2]]
        self.plan["required_changed_regions"] = [
            {"id": "remove-old-line", "rect": [10, 23, 32, 2], "min_changed_pixels": 64},
            {"id": "paint-new-line", "rect": [10, 17, 32, 2], "min_changed_pixels": 64},
        ]
        self.plan["color_direction"] = "any"
        self.plan["min_changed_pixels"] = 128
        self.plan["max_changed_pixels"] = 128
        self.plan["max_channel_delta"] = 90

    def test_underline_moved_closer_and_darkened_passes_two_region_gate(self):
        self.configure_underline_move()
        self.after = self.before.copy()
        for x in range(10, 42):
            for y in (23, 24):
                self.after.putpixel((x, y), (12, 44, 48, 255))
            for y in (17, 18):
                self.after.putpixel((x, y), (35, 65, 67, 255))
        result = self.result()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual([r["actual_changed_pixels"] for r in result["required_changed_regions"]], [64, 64])
        self.assertLess(17-15, 23-15)  # specific synthetic visual gap is shorter
        self.assertLess(lib.luminance((35, 65, 67, 255)),
                        lib.luminance((52, 85, 88, 255)))

    def test_only_darkening_line_without_moving_fails_mandatory_new_region(self):
        self.configure_underline_move()
        result = self.result()  # setUp darkens old line but does not move it
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("paint-new-line" in e for e in result["errors"]))

    def test_moving_line_without_removing_old_line_fails_mandatory_old_region(self):
        self.configure_underline_move()
        for x in range(10, 42):
            for y in (17, 18):
                self.after.putpixel((x, y), (35, 65, 67, 255))
        # The old line has darkened in setup; make old line unchanged to
        # model a newly drawn second underline.
        for x in range(10, 42):
            for y in (23, 24):
                self.after.putpixel((x, y), self.before.getpixel((x, y)))
        result = self.result()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("remove-old-line" in e for e in result["errors"]))

    def test_moved_line_but_right_panel_recolored_still_fails(self):
        self.configure_underline_move()
        self.after = self.before.copy()
        for x in range(10, 42):
            for y in (23, 24):
                self.after.putpixel((x, y), (12, 44, 48, 255))
            for y in (17, 18):
                self.after.putpixel((x, y), (35, 65, 67, 255))
        self.after.putpixel((55, 12), (140, 140, 145, 255))
        self.assertTrue(any("outside authorized" in e for e in self.result()["errors"]))

    def test_mandatory_subregion_cannot_escape_allowed_regions(self):
        self.configure_underline_move()
        self.plan["required_changed_regions"][1]["rect"] = [10, 16, 32, 3]
        with self.assertRaisesRegex(ValueError, "cannot exceed allowed"):
            self.result()

    def test_mandatory_subregion_cannot_override_protection(self):
        self.configure_underline_move()
        self.plan["protected_regions"].append([10, 17, 32, 2])
        with self.assertRaisesRegex(ValueError, "overlap protected"):
            self.result()

    def test_mandatory_subregion_ids_cannot_duplicate(self):
        self.configure_underline_move()
        self.plan["required_changed_regions"][1]["id"] = "remove-old-line"
        with self.assertRaisesRegex(ValueError, "unique"):
            self.result()

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
