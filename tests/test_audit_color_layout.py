"""Synthetic regression for screenshot color drift and real DOM-visible centering."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "audit_color_layout.py"
spec = importlib.util.spec_from_file_location("audit_color_layout", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ColorLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "reference").mkdir()
        (self.root / "preview").mkdir()
        (self.root / "reports").mkdir()
        self.gold = Image.new("RGB", (100, 80), (6, 18, 28))
        for y in range(20, 50):
            for x in range(30, 60):
                self.gold.putpixel((x, y), (15, 208, 250))
        self.gold.save(self.root / "reference/gold.png")
        self.actual = self.gold.copy()
        self.output = self.root / "preview/html.png"
        self.actual.save(self.output)
        self.layout_report = {
            "capture_type": "browser_dom_image_alpha",
            "viewport": [100, 80],
            "device_pixel_ratio": 1,
            "items": [{
                "id": "bottom-production", "slot_rect": [25, 15, 40, 40],
                "image_rect": [25, 15, 40, 40],
                "visible_rect": [30, 20, 30, 30],
            }]
        }
        self.write_report()
        self.plan = {
            "schema_version": "1.0",
            "reference_id": "user-approved-last-image",
            "gold_reference": "reference/gold.png",
            "browser_render": "preview/html.png",
            "browser_layout_report": "reports/browser-layout.json",
            "color_regions": [{
                "id": "bottom-production-color", "roi": [25, 15, 65, 55],
                "color_gate": {
                    "sample_mode": "saturated", "brightness_min": 90,
                    "min_rgb_chroma": 40, "min_reference_pixels": 50,
                    "max_mean_ink_delta": 5,
                    "per_pixel_tolerance": 12, "max_outlier_fraction": 0.01,
                    "full_roi_tolerance": 12, "max_full_roi_changed_fraction": 0.01,
                }
            }],
            "layout_checks": [{
                "id": "bottom-production",
                "expected_center_delta_px": [0, 0], "max_center_error_px": [1.5, 1.5],
            }],
        }

    def write_report(self):
        (self.root / "reports/browser-layout.json").write_text(
            json.dumps(self.layout_report), encoding="utf-8"
        )

    def scan(self):
        return audit.check(self.root, self.plan)

    def test_exact_reference_and_center_pass_diagnostic(self):
        output = self.scan()
        self.assertEqual(output["status"], "PASS", output["errors"])
        self.assertEqual(output["color_regions"][0]["foreground_mean_rgb_distance"], 0)
        self.assertFalse(output["visual_fidelity_verified"])
        self.assertFalse(output["browser_execution_independently_verified"])

    def test_bright_cyan_to_aged_gray_blue_fails(self):
        for y in range(20, 50):
            for x in range(30, 60):
                self.actual.putpixel((x, y), (61, 116, 139))
        self.actual.save(self.output)
        self.assertTrue(any("foreground color" in e for e in self.scan()["errors"]))

    def test_wrong_hue_same_brightness_fails(self):
        for y in range(20, 50):
            for x in range(30, 60):
                self.actual.putpixel((x, y), (230, 170, 10))
        self.actual.save(self.output)
        self.assertEqual(self.scan()["status"], "FAIL")

    def test_extra_dark_fringe_outside_icon_fails_full_roi(self):
        for y in range(18, 52):
            for x in range(28, 62):
                if not (30 <= x < 60 and 20 <= y < 50):
                    self.actual.putpixel((x, y), (0, 0, 0))
        self.actual.save(self.output)
        result = self.scan()
        self.assertTrue(any("full ROI pixel change" in e for e in result["errors"]))

    def test_html_visible_icon_offset_fails(self):
        self.layout_report["items"][0]["visible_rect"][0] += 5
        self.write_report()
        self.assertTrue(any("horizontally centered" in e for e in self.scan()["errors"]))

    def test_html_visible_icon_vertical_offset_fails(self):
        self.layout_report["items"][0]["visible_rect"][1] -= 4
        self.write_report()
        self.assertTrue(any("vertically aligned" in e for e in self.scan()["errors"]))

    def test_center_image_box_but_alpha_offcenter_fails(self):
        # Image element itself is centered, yet foreground alpha is not.
        self.layout_report["items"][0]["image_rect"] = [25, 15, 40, 40]
        self.layout_report["items"][0]["visible_rect"] = [37, 20, 30, 30]
        self.write_report()
        self.assertEqual(self.scan()["layout_checks"][0]["pass"], False)

    def test_known_gold_offset_can_be_allowed(self):
        self.layout_report["items"][0]["visible_rect"][0] += 4
        self.write_report()
        self.plan["layout_checks"][0]["expected_center_delta_px"] = [4, 0]
        self.assertEqual(self.scan()["status"], "PASS", self.scan()["errors"])

    def test_missing_browser_measurement_fails(self):
        self.layout_report["items"] = []
        self.write_report()
        self.assertEqual(self.scan()["status"], "FAIL")

    def test_capture_error_from_tainted_canvas_fails(self):
        self.layout_report["items"][0]["error"] = "Canvas is tainted by cross-origin image"
        self.write_report()
        self.assertEqual(self.scan()["status"], "FAIL")

    def test_duplicate_measurements_rejected(self):
        self.layout_report["items"].append(self.layout_report["items"][0].copy())
        self.write_report()
        with self.assertRaisesRegex(ValueError, "duplicate item"):
            self.scan()

    def test_layout_viewport_must_match_css_screenshot(self):
        self.layout_report["viewport"] = [200, 160]
        self.write_report()
        with self.assertRaisesRegex(ValueError, "viewport differs"):
            self.scan()

    def test_geometry_must_come_from_dom_capture(self):
        self.layout_report["capture_type"] = "manually_entered"
        self.write_report()
        with self.assertRaisesRegex(ValueError, "DOM\\+alpha capture type"):
            self.scan()

    def test_reference_and_actual_viewport_mismatch_rejected(self):
        self.actual.resize((90, 80)).save(self.output)
        with self.assertRaisesRegex(ValueError, "canvas mismatch"):
            self.scan()

    def test_roi_must_contain_enough_reference_ink(self):
        self.plan["color_regions"][0]["roi"] = [0, 0, 15, 15]
        self.assertTrue(any("insufficient qualified" in e for e in self.scan()["errors"]))

    def test_white_pictogram_uses_bright_color_mode(self):
        for y in range(20, 50):
            for x in range(30, 60):
                self.gold.putpixel((x, y), (230, 235, 243))
        self.gold.save(self.root / "reference/gold.png")
        self.actual = self.gold.copy()
        self.actual.save(self.output)
        self.plan["color_regions"][0]["color_gate"]["sample_mode"] = "bright"
        self.plan["color_regions"][0]["color_gate"]["brightness_min"] = 200
        self.assertEqual(self.scan()["status"], "PASS", self.scan()["errors"])

    def test_thresholds_cannot_be_nonsense(self):
        self.plan["color_regions"][0]["color_gate"]["max_outlier_fraction"] = 5
        with self.assertRaisesRegex(ValueError, "outside valid range"):
            self.scan()

    def test_traversal_image_rejected(self):
        self.plan["gold_reference"] = "../external.png"
        with self.assertRaisesRegex(ValueError, "unsafe path"):
            self.scan()


if __name__ == "__main__":
    unittest.main()
