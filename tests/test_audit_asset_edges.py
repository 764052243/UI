"""Synthetic only: no user PNGs or protected golden master are committed."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_asset_edges.py"
spec = importlib.util.spec_from_file_location("audit_asset_edges", SCRIPT)
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)


class EdgeAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "delivery"
        (self.root / "assets/components").mkdir(parents=True)
        (self.root / "assets/icons").mkdir(parents=True)
        self.art = self.root / "assets/components/map.png"
        image = Image.new("RGBA", (32, 24), (0, 0, 0, 0))
        for y in range(4, 20):
            for x in range(4, 28):
                image.putpixel((x, y), (0, 130, 255, 255))
        image.putpixel((4, 4), (0, 130, 255, 128))
        image.save(self.art)
        self.icon = self.root / "assets/icons/nav.png"
        image.save(self.icon)
        self.manifest = self.root / "asset-manifest.json"
        self.payload = {"assets": [
            {"role": "component", "path": "assets/components/map.png", "edge_policy": "closed"},
            {"role": "icon", "path": "assets/icons/nav.png"}
        ]}
        self.save_manifest()

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.payload), encoding="utf-8")

    def test_closed_component_and_icon_can_pass_geometry(self):
        r = lib.audit(self.root, self.manifest)
        self.assertEqual(r["status"], "PASS", r["problems"])
        self.assertFalse(r["quality_verified"])
        self.assertTrue(r["manual_visual_review_required"])
        self.assertGreater(r["assets"][0]["semi_alpha_fraction"], 0)

    def test_component_truncated_at_edge_fails(self):
        with Image.open(self.art) as im:
            img = im.convert("RGBA")
        img.putpixel((0, 7), (0, 130, 255, 255))
        img.save(self.art)
        r = lib.audit(self.root, self.manifest)
        self.assertEqual(r["status"], "FAIL")
        self.assertTrue(r["assets"][0]["touches_edge"]["left"])

    def test_intentional_bleed_has_documented_exception(self):
        with Image.open(self.art) as im:
            img = im.convert("RGBA")
        img.putpixel((0, 7), (0, 130, 255, 255))
        img.save(self.art)
        self.payload["assets"][0]["edge_policy"] = "intentional_bleed"
        self.save_manifest()
        self.assertEqual(lib.audit(self.root, self.manifest)["status"], "PASS")

    def test_background_with_alpha_hole_fails(self):
        self.payload["assets"] = [{"role": "background", "path": "assets/components/map.png"}]
        self.save_manifest()
        self.assertTrue(any("transparent gaps" in x for x in lib.audit(self.root, self.manifest)["assets"][0]["problems"]))

    def test_no_content_alpha_fails(self):
        Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(self.art)
        with self.assertRaisesRegex(ValueError, "fully transparent"):
            lib.audit(self.root, self.manifest)

    def test_absolute_and_traversal_path_rejected(self):
        for path in ("/tmp/evil.png", "../evil.png", "assets/../../evil.png"):
            with self.assertRaisesRegex(ValueError, "unsafe asset path"):
                lib.safe_asset_path(self.root, path)

    def test_missing_asset_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing asset"):
            lib.safe_asset_path(self.root, "assets/components/nothing.png")

    def test_contact_sheet_is_outside_input_assets(self):
        target = Path(self.tmp.name) / "working" / "asset-review.png"
        result = lib.audit(self.root, self.manifest, target)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(target.is_file())
        with Image.open(target) as im:
            self.assertEqual(im.size, (780, 450))

    def test_contact_sheet_does_not_overwrite_original_png(self):
        with self.assertRaisesRegex(ValueError, "cannot overwrite"):
            lib.build_sheet([("component", self.art)], self.art)

    def test_contact_sheet_cannot_contaminate_asset_dir(self):
        with self.assertRaisesRegex(ValueError, "outside input asset directories"):
            lib.build_sheet([("component", self.art)], self.art.parent / "qa.png")

    def test_png_rgb_invisible_diagnostic_only(self):
        with Image.open(self.art) as im:
            img = im.convert("RGBA")
        img.putpixel((0, 0), (255, 0, 0, 0))
        img.save(self.art)
        r = lib.audit(self.root, self.manifest)
        self.assertEqual(r["status"], "PASS")
        self.assertGreater(r["assets"][0]["invisible_rgb_fraction"], 0)

    def test_half_background_cannot_be_certified_by_alpha_only(self):
        """A solid opaque half-blank scene is visually wrong but needs golden review."""
        path = self.root / "assets/components/halfscreen.png"
        img = Image.new("RGB", (60, 30), (3, 3, 4))
        for y in range(0, 15):
            for x in range(60):
                img.putpixel((x, y), (0, 140, 230))
        img.save(path)
        self.payload["assets"] = [{"role": "component", "path": "assets/components/halfscreen.png", "edge_policy": "intentional_bleed"}]
        self.save_manifest()
        report = lib.audit(self.root, self.manifest)
        self.assertFalse(report["quality_verified"])
        self.assertTrue(report["manual_visual_review_required"])


if __name__ == "__main__":
    unittest.main()
