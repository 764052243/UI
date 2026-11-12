"""Synthetic native UI gold and browser-render screenshots only."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_strict_1to1.py"
spec = importlib.util.spec_from_file_location("audit_strict_1to1", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class StrictGoldRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "reference").mkdir()
        (self.root / "preview").mkdir()
        self.gold = Image.new("RGBA", (72, 45), (7, 18, 26, 255))
        for x in range(9, 24):
            for y in range(10, 25):
                self.gold.putpixel((x, y), (15, 221, 250, 255))
        for x in range(39, 60):
            for y in range(13, 29):
                self.gold.putpixel((x, y), (238, 142, 30, 255))
        self.gold_path = self.root / "reference/approved.png"
        self.gold.save(self.gold_path)
        self.candidate = self.gold.copy()
        self.render_path = self.root / "preview/render.png"
        self.save_render()
        self.plan = {
            "schema_version": "1.0", "reference_id": "approved-screen-1",
            "reference_origin": "original_export",
            "reference_overlay_free": True,
            "reference_png": "reference/approved.png",
            "reference_sha256": hashlib.sha256(self.gold_path.read_bytes()).hexdigest(),
            "reference_native_size": [72, 45],
            "actual_browser_png": "preview/render.png",
            "claim": "strict_pixel_1to1",
            "fidelity_scope": "critical_regions",
            "required_region_ids": ["status-blue", "kpi-orange"],
            "regions": [
                {"id": "status-blue", "box": [5, 5, 31, 32]},
                {"id": "kpi-orange", "box": [35, 8, 65, 35]},
            ],
        }

    def save_render(self):
        self.candidate.save(self.render_path)

    def scan(self):
        return m.audit(self.root, self.plan)

    def test_identical_native_regions_pass_but_not_claim_semantic_html(self):
        r = self.scan()
        self.assertEqual(r["status"], "PASS")
        self.assertFalse(r["html_interactivity_verified"])
        self.assertFalse(r["reference_origin_independently_verified"])
        self.assertFalse(r["semantic_assets_verified"])

    def test_cyan_icon_hue_change_fails_its_roi(self):
        self.candidate.putpixel((12, 12), (35, 154, 191, 255))
        self.save_render()
        r = self.scan()
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["failed_regions"], ["status-blue"])

    def test_orange_stack_shape_shift_fails_roi(self):
        self.candidate.putpixel((44, 16), (7, 18, 26, 255))
        self.save_render()
        self.assertEqual(self.scan()["failed_regions"], ["kpi-orange"])

    def test_extra_black_outline_fails(self):
        self.candidate.putpixel((8, 11), (0, 0, 0, 255))
        self.save_render()
        self.assertEqual(self.scan()["status"], "FAIL")

    def test_no_majority_mask_can_hide_one_pixel(self):
        self.candidate.putpixel((11, 13), (14, 221, 250, 255))
        self.save_render()
        row = self.scan()["regions"][0]
        self.assertEqual(row["different_pixels"], 1)
        self.assertEqual(row["max_rgba_channel_delta"], 1)

    def test_full_page_fails_on_outside_change(self):
        self.candidate.putpixel((70, 42), (2, 10, 15, 255))
        self.save_render()
        self.assertEqual(self.scan()["status"], "PASS")  # critical regions are equal
        self.plan["fidelity_scope"] = "full_page"
        r = self.scan()
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("full_page", r["failed_regions"])

    def test_missing_key_region_rejected(self):
        self.plan["regions"].pop()
        with self.assertRaisesRegex(ValueError, "ROI coverage incomplete"):
            self.scan()

    def test_duplicate_required_region_id_rejected(self):
        self.plan["required_region_ids"] = ["status-blue", "status-blue"]
        with self.assertRaisesRegex(ValueError, "unique"):
            self.scan()

    def test_duplicate_region_id_rejected(self):
        self.plan["regions"][1]["id"] = "status-blue"
        with self.assertRaisesRegex(ValueError, "duplicate ROI"):
            self.scan()

    def test_reference_file_hash_tampering_fails(self):
        self.gold.putpixel((4, 3), (200, 100, 80, 255))
        self.gold.save(self.gold_path)
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.scan()

    def test_picture_viewer_screenshot_rejected(self):
        self.plan["reference_origin"] = "viewer_screenshot"
        with self.assertRaisesRegex(ValueError, "collage"):
            self.scan()

    def test_overlay_declaration_missing_rejected(self):
        self.plan["reference_overlay_free"] = False
        with self.assertRaisesRegex(ValueError, "overlay_free"):
            self.scan()

    def test_canvas_mismatch_rejected_not_resized(self):
        self.candidate.resize((144, 90)).save(self.render_path)
        with self.assertRaisesRegex(ValueError, "native canvas"):
            self.scan()

    def test_transparent_browser_composite_rejected(self):
        self.candidate.putpixel((2, 2), (3, 4, 5, 0))
        self.save_render()
        with self.assertRaisesRegex(ValueError, "fully opaque"):
            self.scan()

    def test_crop_box_outside_canvas_rejected(self):
        self.plan["regions"][0]["box"] = [5, 5, 1000, 32]
        with self.assertRaisesRegex(ValueError, "outside actual native canvas"):
            self.scan()

    def test_gold_and_render_cannot_point_to_same_file(self):
        self.plan["actual_browser_png"] = self.plan["reference_png"]
        with self.assertRaisesRegex(ValueError, "same file"):
            self.scan()

    def test_wrong_claim_cannot_fake_strict_mode(self):
        self.plan["claim"] = "perceptual_approximation"
        with self.assertRaisesRegex(ValueError, "strict_pixel_1to1"):
            self.scan()

    def test_reference_size_declaration_must_match_actual(self):
        self.plan["reference_native_size"] = [1672, 941]
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            self.scan()


if __name__ == "__main__":
    unittest.main()
