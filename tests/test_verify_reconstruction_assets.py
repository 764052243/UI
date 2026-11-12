"""Synthetic SVG/PNG evidence only; does not include any user image."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from PIL import Image

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "verify_reconstruction_assets.py"
spec = importlib.util.spec_from_file_location("verify_reconstruction_assets", MODULE)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path d="M4 4L28 4L16 28Z" fill="#00ccff"/></svg>'


class NoPsdReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "sources/vector").mkdir(parents=True)
        (self.root / "sources/procedural").mkdir(parents=True)
        (self.root / "assets/icons").mkdir(parents=True)
        (self.root / "assets/components").mkdir(parents=True)
        (self.root / "sources/vector/truck.svg").write_text(SVG, encoding="utf-8")
        self.icon_path = self.root / "assets/icons/truck@2x.png"
        self.icon = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        for y in range(6, 58):
            for x in range(6, 58):
                self.icon.putpixel((x, y), (0, 220, 255, 255))
        self.icon.save(self.icon_path)
        self.item = {
            "id": "truck", "method": "vector_redraw",
            "source_path": "sources/vector/truck.svg",
            "export_png": "assets/icons/truck@2x.png",
            "target_css_px": [32, 32], "target_dpr": 2,
            "visual_unit": "nav-logistics",
            "source_kind": "reconstructed"
        }
        self.plan = {"schema_version": "1.0", "reference_id": "approved", "assets": [self.item]}

    def audit(self):
        return verify.check(self.root, self.plan)

    def test_real_svg_and_png_pass_structure_only(self):
        r = self.audit()
        self.assertEqual(r["status"], "PASS", r["errors"])
        self.assertFalse(r["visual_fidelity_verified"])
        self.assertFalse(r["browser_verified"])
        self.assertGreater(r["assets"][0]["vector_elements"], 0)

    def test_svg_wrapping_bitmap_rejected(self):
        f = self.root / "sources/vector/truck.svg"
        f.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/png;base64,AAAA"/></svg>')
        r = self.audit()
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(any("fake/unsafe SVG" in x for x in r["errors"]))

    def test_svg_with_external_raster_href_rejected(self):
        (self.root / "sources/vector/truck.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><use href="https://site.example/map.png"/></svg>'
        )
        self.assertEqual(self.audit()["status"], "FAIL")

    def test_svg_without_vector_geometry_rejected(self):
        (self.root / "sources/vector/truck.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><defs/></svg>'
        )
        self.assertTrue(any("no vector geometry" in e for e in self.audit()["errors"]))

    def test_png_export_dpr_insufficient_rejected(self):
        self.icon.resize((32, 32)).save(self.icon_path)
        self.assertTrue(any("smaller than target CSS" in e for e in self.audit()["errors"]))

    def test_opaque_png_when_icon_requires_alpha_rejected(self):
        Image.new("RGB", (64, 64), (8, 13, 27)).save(self.icon_path)
        self.assertTrue(any("real transparent pixels" in e for e in self.audit()["errors"]))

    def test_svg_missing_no_fake_pass(self):
        (self.root / "sources/vector/truck.svg").unlink()
        self.assertTrue(any("source_path missing" in e for e in self.audit()["errors"]))

    def test_method_requires_declared_provenance(self):
        self.item["source_kind"] = "layer_export"
        self.assertTrue(any("source_kind=reconstructed" in e for e in self.audit()["errors"]))

    def test_pixel_restoration_low_source_pixels_fail(self):
        src = self.root / "sources/vector/low.png"
        self.icon.resize((20, 20)).save(src)
        self.item.update(method="pixel_restoration", source_path="sources/vector/low.png",
                         native_input_px=[20, 20])
        self.assertTrue(any("cannot become true native HD" in e for e in self.audit()["errors"]))

    def test_procedural_script_supports_high_resolution_png(self):
        (self.root / "sources/procedural/plinth.py").write_text("print('geometry')", encoding="utf-8")
        self.item.update(method="procedural_3d", source_path="sources/procedural/plinth.py")
        self.assertEqual(self.audit()["status"], "PASS", self.audit()["errors"])

    def test_ai_only_bitmap_without_editable_source_rejected(self):
        (self.root / "sources/vector/ai.png").write_bytes(self.icon_path.read_bytes())
        self.item.update(method="ai_assisted", source_path="sources/vector/ai.png",
                         manual_review_status="reviewed")
        self.assertEqual(self.audit()["status"], "FAIL")

    def test_ai_candidate_needs_review_even_if_editable_source_exists(self):
        (self.root / "sources/vector/ai.png").write_bytes(self.icon_path.read_bytes())
        self.item.update(method="ai_assisted", source_path="sources/vector/ai.png",
                         editable_source_path="sources/vector/truck.svg",
                         manual_review_status="pending")
        self.assertTrue(any("not documented as manually reviewed" in e for e in self.audit()["errors"]))

    def test_dangerous_path_rejected(self):
        self.item["source_path"] = "../secret.svg"
        self.assertTrue(any("unsafe path" in e for e in self.audit()["errors"]))

    def test_duplicated_asset_ids_fail(self):
        self.plan["assets"].append(self.item.copy())
        self.assertTrue(any("duplicate id" in e for e in self.audit()["errors"]))

    def test_reference_id_required(self):
        self.plan["reference_id"] = ""
        with self.assertRaisesRegex(ValueError, "reference_id"):
            self.audit()


if __name__ == "__main__":
    unittest.main()
