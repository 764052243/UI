"""Only synthetic fixtures; actual private user artwork is not committed."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_cutout_source_quality.py"
spec = importlib.util.spec_from_file_location("audit_cutout_source_quality", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class CutoutSourceQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "assets").mkdir()
        (self.root / "preview").mkdir()
        self.plinth = self.root / "assets/plinth.png"
        self.glyph = self.root / "assets/glyph.png"
        self.preview = self.root / "preview/composite.png"
        self.draw(self.plinth, (220, 160), (5, 40, 215, 155))
        self.draw(self.glyph, (220, 160), (55, 15, 165, 110))
        self.draw(self.preview, (220, 160), (5, 15, 215, 155))
        self.payload = {"schema_version": "1.0", "assets": [
            self.asset("assets/plinth.png", "plinth", "layer_anchor"),
            self.asset("assets/glyph.png", "glyph", "layer_anchor")
        ]}

    def draw(self, path, dims, box):
        image = Image.new("RGBA", dims, (0, 0, 0, 0))
        for y in range(box[1], box[3]):
            for x in range(box[0], box[2]):
                image.putpixel((x, y), (0, 208, 255, 255))
        image.save(path)

    def asset(self, path, role, alignment, native=None):
        return {
            "asset_path": path, "visual_unit": "customer",
            "layer_role": role, "alignment_mode": alignment,
            "target_css_px": [100, 70], "target_dpr": 2,
            "source_native_px": native or [220, 160],
            "source_kind": "layer_export",
            "composite_preview": "preview/composite.png"
        }

    def check(self):
        return audit.check(self.root, self.payload)

    def setup_lossless_standalone(self):
        self.source = self.root / "assets/original-icon.png"
        im = Image.new("RGBA", (220, 160), (0, 0, 0, 0))
        # Intentionally asymmetric and multi-part, making half-crops observable.
        for x in range(58, 171):
            for y in range(16, 108):
                if (x + y) % 5 != 0:
                    im.putpixel((x, y), ((3*x)%255, (2*y)%255, 120, 255))
        for y in range(28, 55):
            for x in range(170, 195):
                im.putpixel((x, y), (4, 210, 250, 120))
        im.save(self.source)
        im.crop((52, 10, 200, 115)).save(self.glyph)
        row = self.asset("assets/glyph.png", "standalone", "tight")
        row["integrity_mode"] = "lossless_isolated_layer"
        row["source_layer_path"] = "assets/original-icon.png"
        # Source and export are both raster images, but must not be stretched.
        row["target_css_px"] = [70, 50]
        row["target_dpr"] = 1
        self.payload["assets"] = [row]

    def test_exact_isolated_layer_crop_passes_without_resampling(self):
        self.setup_lossless_standalone()
        result = self.check()
        self.assertEqual(result["status"], "PASS", result["failures"])
        proof = result["assets"][0]["lossless_integrity"]
        self.assertEqual(proof["different_visible_pixels"], 0)
        self.assertTrue(proof["pass"])
        self.assertFalse(result["quality_verified"])

    def test_only_half_icon_cropped_fails_even_if_dims_metadata_look_good(self):
        self.setup_lossless_standalone()
        with Image.open(self.glyph) as im:
            cropped = im.convert("RGBA").crop((0, 0, 105, im.height))
        cropped.save(self.glyph)
        result = self.check()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("lossless isolated icon integrity failed" in
                            item["message"] for item in result["failures"]))

    def test_doubly_resampled_icon_fails_exact_source_integrity(self):
        self.setup_lossless_standalone()
        with Image.open(self.glyph) as im:
            pix = im.convert("RGBA")
        # Simulate thumbnail/resize chain while keeping final pixel dimensions.
        reduced = pix.resize((60, 43), Image.Resampling.BILINEAR)
        reduced.resize(pix.size, Image.Resampling.BILINEAR).save(self.glyph)
        result = self.check()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("lossless isolated icon integrity failed" in
                            item["message"] for item in result["failures"]))

    def test_recolored_icon_fails_exact_integrity(self):
        self.setup_lossless_standalone()
        with Image.open(self.glyph) as im:
            img = im.convert("RGBA")
        img.putpixel((50, 30), (255, 0, 0, 255))
        img.save(self.glyph)
        self.assertEqual(self.check()["status"], "FAIL")

    def test_opaque_screenshot_cannot_claim_isolated_layer(self):
        self.setup_lossless_standalone()
        Image.new("RGB", (220, 160), "white").save(self.source)
        with self.assertRaisesRegex(ValueError, "isolated transparent RGBA layer"):
            self.check()

    def test_source_reference_mandatory_in_lossless_mode(self):
        self.setup_lossless_standalone()
        self.payload["assets"][0].pop("source_layer_path")
        with self.assertRaisesRegex(ValueError, "source_layer_path"):
            self.check()

    def test_lossless_mode_cannot_be_claimed_for_masked_flat_screenshot(self):
        self.setup_lossless_standalone()
        self.payload["assets"][0]["source_kind"] = "masked"
        with self.assertRaisesRegex(ValueError, "requires source_kind layer_export"):
            self.check()

    def test_existing_declared_source_metadata_only_stays_compatible(self):
        result = self.check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["assets"][0]["integrity_mode"], "not_claimed")
        self.assertIsNone(result["assets"][0]["lossless_integrity"])

    def test_complete_group_with_source_pixels_passes_numeric_gates(self):
        result = self.check()
        self.assertEqual(result["status"], "PASS", result["failures"])
        self.assertFalse(result["quality_verified"])
        self.assertFalse(result["photoshop_executed"])

    def test_missing_glyph_flags_half_visual_unit(self):
        self.payload["assets"].pop()
        result = self.check()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("missing glyph or plinth" in item["message"] for item in result["failures"]))

    def test_missing_composite_preview_flags_incomplete_group(self):
        for asset in self.payload["assets"]:
            asset.pop("composite_preview")
        self.assertTrue(any("missing complete composite preview" in x["message"] for x in self.check()["failures"]))

    def test_inconsistent_composite_previews_rejected(self):
        self.draw(self.root / "preview/another.png", (220, 160), (0, 0, 210, 155))
        self.payload["assets"][0]["composite_preview"] = "preview/another.png"
        self.assertTrue(any("inconsistent composite previews" in x["message"] for x in self.check()["failures"]))

    def test_low_source_native_pixels_cannot_pass_by_upscaling(self):
        self.payload["assets"][0]["source_native_px"] = [132, 102]
        r = self.check()
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(any("original native pixels insufficient" in x["message"] for x in r["failures"]))

    def test_low_export_resolution_fails_even_if_native_large(self):
        self.draw(self.plinth, (80, 64), (2, 12, 77, 61))
        r = self.check()
        self.assertTrue(any("exported PNG pixels insufficient" in x["message"] for x in r["failures"]))

    def test_standalone_offcenter_top_gap_fails(self):
        self.payload["assets"] = [self.asset("assets/plinth.png", "standalone", "tight")]
        r = self.check()
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(any("bbox is off-center" in x["message"] for x in r["failures"]))

    def test_standalone_well_centered_passes_geometry(self):
        self.draw(self.plinth, (220, 160), (10, 10, 210, 150))
        self.payload["assets"] = [self.asset("assets/plinth.png", "standalone", "tight")]
        self.assertEqual(self.check()["status"], "PASS", self.check()["failures"])

    def test_layer_anchor_cannot_make_unpaired_map_pass(self):
        self.payload["assets"] = [self.asset("assets/plinth.png", "map", "layer_anchor")]
        self.assertTrue(any("only permitted" in x["message"] for x in self.check()["failures"]))

    def test_missing_preview_is_a_bad_input(self):
        self.preview.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.check()

    def test_traversal_rejected(self):
        self.payload["assets"][0]["asset_path"] = "../secret.png"
        with self.assertRaisesRegex(ValueError, "path traversal"):
            self.check()

    def test_boolean_dpr_rejected(self):
        self.payload["assets"][0]["target_dpr"] = True
        with self.assertRaisesRegex(ValueError, "target_dpr"):
            self.check()

    def test_no_assets_rejected(self):
        self.payload["assets"] = []
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.check()

    def test_missing_source_native_dimensions_rejected(self):
        self.payload["assets"][0].pop("source_native_px")
        with self.assertRaisesRegex(ValueError, "source_native_px"):
            self.check()

    def test_all_transparent_source_rejected(self):
        Image.new("RGBA", (220, 160), (0, 0, 0, 0)).save(self.plinth)
        with self.assertRaisesRegex(ValueError, "fully transparent"):
            self.check()


if __name__ == "__main__":
    unittest.main()
