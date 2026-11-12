"""Synthetic full-screen gold ROI + clean browser underlay for composite quality gates."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_visual_unit_composite.py"
spec = importlib.util.spec_from_file_location("audit_visual_unit_composite", PATH)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class VisualUnitCompositeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "assets/components").mkdir(parents=True)
        (self.root / "assets/icons").mkdir(parents=True)
        (self.root / "reference").mkdir()
        (self.root / "preview").mkdir()
        self.base = Image.new("RGBA", (30, 26), (0, 0, 0, 0))
        for y in range(4, 22):
            for x in range(3, 27):
                self.base.putpixel((x, y), (4, 15, 24, 255))
        for x in range(8, 23):
            self.base.putpixel((x, 5), (8, 240, 255, 192))
        self.glyph = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        for y in range(3, 17):
            for x in range(4, 16):
                self.glyph.putpixel((x, y), (0, 211, 245, 235))
        self.base_path = self.root / "assets/components/plinth.png"
        self.glyph_path = self.root / "assets/icons/box.png"
        self.base.save(self.base_path)
        self.glyph.save(self.glyph_path)
        self.underlay = Image.new("RGBA", (80, 64), (8, 15, 25, 255))
        self.underlay.save(self.root / "preview/underlay.png")
        self.gold = self.underlay.copy()
        self.gold.alpha_composite(self.base, (10, 25))
        self.gold.alpha_composite(self.glyph, (16, 14))
        self.gold.save(self.root / "reference/gold.png")
        self.plan = {
            "schema_version": "1.0", "reference_id": "approved-screen",
            "gold_reference": "reference/gold.png",
            "underlay_without_units": "preview/underlay.png",
            "visual_units": [{
                "id": "business-warehouse", "roi": [5, 2, 70, 58],
                "pixel_tolerance": 0,
                "max_changed_fraction": 0.0,
                "max_mean_rgb_difference": 0.0,
                "layers": [
                    {"path": "assets/components/plinth.png", "at_xy": [10, 25]},
                    {"path": "assets/icons/box.png", "at_xy": [16, 14]}
                ]
            }]
        }

    def run_audit(self, output=None):
        return qa.examine(self.root, self.plan, output)

    def test_gold_and_true_alpha_composite_equal(self):
        r = self.run_audit()
        self.assertEqual(r["status"], "PASS", r["errors"])
        self.assertEqual(r["regions"][0]["changed_fraction"], 0)
        self.assertFalse(r["fidelity_verified"])
        self.assertTrue(r["manual_edge_and_gold_review_required"])

    def test_relocating_icon_causes_pixel_mismatch(self):
        self.plan["visual_units"][0]["layers"][1]["at_xy"][0] += 3
        r = self.run_audit()
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(any("changed fraction" in x for x in r["errors"]))

    def test_missing_glowing_icon_fails_even_if_plinth_exists(self):
        self.plan["visual_units"][0]["layers"].pop()
        r = self.run_audit()
        self.assertEqual(r["status"], "FAIL")
        self.assertGreater(r["regions"][0]["mean_rgb_difference"], 0)

    def test_faint_glow_touching_canvas_is_rejected(self):
        self.base.putpixel((0, 0), (0, 140, 255, 1))
        self.base.save(self.base_path)
        r = self.run_audit()
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(any("glow clipped" in x for x in r["errors"]))

    def test_masked_black_rectangle_pollution_mismatches_reference(self):
        for y in range(2, 25):
            for x in range(1, 29):
                if self.base.getpixel((x, y))[3] == 0:
                    self.base.putpixel((x, y), (0, 0, 0, 255))
        self.base.save(self.base_path)
        r = self.run_audit()
        self.assertEqual(r["status"], "FAIL")
        self.assertGreater(r["regions"][0]["changed_fraction"], 0)

    def test_roi_missing_part_of_glow_fails(self):
        self.plan["visual_units"][0]["roi"] = [20, 18, 40, 40]
        r = self.run_audit()
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(any("visible layer exceeds reference ROI" in x for x in r["errors"]))

    def test_screenshot_viewports_must_match(self):
        Image.new("RGB", (40, 64), "#091018").save(self.root / "preview/underlay.png")
        with self.assertRaisesRegex(ValueError, "identical viewport"):
            self.run_audit()

    def test_screenshot_underlay_must_be_opaque(self):
        Image.new("RGBA", (80, 64), (2, 3, 6, 0)).save(self.root / "preview/underlay.png")
        with self.assertRaisesRegex(ValueError, "must be opaque"):
            self.run_audit()

    def test_proof_sheet_is_created_outside_assets(self):
        output = self.root / "reports/composite-qa.png"
        r = self.run_audit(output)
        self.assertEqual(r["status"], "PASS")
        with Image.open(output) as im:
            self.assertEqual(im.size, (65 * 3 + 32, 56 + 16))

    def test_proof_sheet_cannot_overwrite_gold(self):
        with self.assertRaisesRegex(ValueError, "cannot overwrite"):
            self.run_audit(self.root / "reference/gold.png")

    def test_proof_sheet_cannot_enter_assets_dir(self):
        with self.assertRaisesRegex(ValueError, "must not contaminate"):
            self.run_audit(self.root / "assets/components/audit.png")

    def test_layer_path_traversal_rejected(self):
        self.plan["visual_units"][0]["layers"][0]["path"] = "../secret.png"
        with self.assertRaisesRegex(ValueError, "cannot escape"):
            self.run_audit()

    def test_bleed_exception_requires_specific_approval(self):
        self.base.putpixel((0, 0), (0, 140, 255, 1))
        self.base.save(self.base_path)
        layer = self.plan["visual_units"][0]["layers"][0]
        layer["intentional_bleed"] = True
        self.assertEqual(self.run_audit()["status"], "FAIL")
        layer["bleed_approval_reference"] = "approved-ROI-leaks-left"
        self.assertFalse(any("glow clipped" in x for x in self.run_audit()["errors"]))

    def test_invalid_thresholds_rejected(self):
        self.plan["visual_units"][0]["max_changed_fraction"] = 1.0
        with self.assertRaisesRegex(ValueError, "thresholds required"):
            self.run_audit()

    def test_stable_underlay_required_to_compare_gold(self):
        self.plan["underlay_without_units"] = "preview/missing.png"
        with self.assertRaisesRegex(ValueError, "missing"):
            self.run_audit()


if __name__ == "__main__":
    unittest.main()
