#!/usr/bin/env python3
"""Synthetic regression tests for verify_ui_delivery.py; no user assets."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image


SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "verify_ui_delivery.py"
spec = importlib.util.spec_from_file_location("verify_ui_delivery", SOURCE)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class SemanticDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "delivery"
        for part in ["assets/backgrounds", "assets/icons", "preview", "css", "js"]:
            (self.root / part).mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (32, 24), (10, 15, 20, 255)).save(self.root / "assets/backgrounds/bg.png")
        Image.new("RGBA", (32, 24), (10, 15, 20, 255)).save(self.root / "preview/full-page.png")
        icon = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(2, 6):
            for x in range(2, 6):
                icon.putpixel((x, y), (0, 210, 255, 255))
        icon.save(self.root / "assets/icons/nav.png")
        (self.root / "index.html").write_text(
            '<!doctype html><html><head><link rel="stylesheet" href="css/style.css"></head>'
            '<body><h1>业务运营可视化平台</h1><nav><button type="button">'
            '<img src="assets/icons/nav.png" alt="">综合概览</button></nav>'
            '<script src="js/app.js"></script></body></html>', encoding="utf-8"
        )
        (self.root / "css/style.css").write_text(
            'body {background-image: url("../assets/backgrounds/bg.png");}'
            'nav button {cursor:pointer}', encoding="utf-8"
        )
        (self.root / "js/app.js").write_text(
            'document.querySelector("button").addEventListener("click",()=>{});',
            encoding="utf-8"
        )
        self.manifest = {
            "schema_version": "1.0",
            "canvas": {"width": 32, "height": 24},
            "entry_html": "index.html",
            "css": ["css/style.css"],
            "js": ["js/app.js"],
            "preview": "preview/full-page.png",
            "assets": [
                {"id": "bg", "role": "background", "path": "assets/backgrounds/bg.png"},
                {"id": "nav", "role": "icon", "path": "assets/icons/nav.png"}
            ],
            "required_text": ["业务运营可视化平台", "综合概览"],
            "required_interactions": ["navigation"]
        }
        self.write_manifest()

    def write_manifest(self):
        (self.root / "asset-manifest.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8"
        )

    def scan(self, zip_file=None):
        return checker.scan(self.root, zip_file)

    def test_valid_semantic_package_passes_static_checks(self):
        result = self.scan()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["assets_checked"], 2)
        self.assertFalse(result["visual_verified"])
        self.assertFalse(result["interaction_runtime_verified"])

    def test_missing_html_fails(self):
        (self.root / "index.html").unlink()
        self.assertEqual(self.scan()["status"], "FAIL")

    def test_opaque_icon_fails(self):
        Image.new("RGB", (8, 8), (11, 30, 50)).save(self.root / "assets/icons/nav.png")
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("icon lacks transparent" in x for x in result["errors"]))

    def test_background_wrong_dimensions_fails(self):
        Image.new("RGB", (31, 24), (0, 0, 0)).save(self.root / "assets/backgrounds/bg.png")
        self.assertTrue(any("background size mismatch" in e for e in self.scan()["errors"]))

    def test_missing_reference_fails(self):
        html = self.root / "index.html"
        html.write_text(html.read_text(encoding="utf-8").replace(
            '<img src="assets/icons/nav.png" alt="">', ''
        ), encoding="utf-8")
        self.assertTrue(any("asset not referenced" in e for e in self.scan()["errors"]))

    def test_missing_semantic_html_text_fails(self):
        html = self.root / "index.html"
        html.write_text(html.read_text(encoding="utf-8").replace(
            '业务运营可视化平台', '待填充'
        ), encoding="utf-8")
        self.assertTrue(any("HTML text missing" in e for e in self.scan()["errors"]))

    def test_preview_used_in_html_fails(self):
        html = self.root / "index.html"
        html.write_text(html.read_text(encoding="utf-8").replace(
            '</body>', '<img src="preview/full-page.png"></body>'
        ), encoding="utf-8")
        self.assertTrue(any("preview used as page content" in e for e in self.scan()["errors"]))

    def test_asset_path_traversal_fails(self):
        self.manifest["assets"][1]["path"] = "../secrets.png"
        self.write_manifest()
        self.assertEqual(self.scan()["status"], "FAIL")

    def test_missing_icon_png_fails(self):
        (self.root / "assets/icons/nav.png").unlink()
        self.assertEqual(self.scan()["status"], "FAIL")

    def test_valid_complete_zip_passes(self):
        archive_path = Path(self.tmp.name) / "delivery.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in self.root.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(self.root).as_posix())
        result = self.scan(archive_path)
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["zip_files"], 7)

    def test_zip_missing_html_fails(self):
        archive_path = Path(self.tmp.name) / "bad.zip"
        with zipfile.ZipFile(archive_path, "w") as z:
            for p in self.root.rglob("*"):
                if p.is_file() and p.name != "index.html":
                    z.write(p, p.relative_to(self.root).as_posix())
        self.assertTrue(any("ZIP file list" in e for e in self.scan(archive_path)["errors"]))

    def test_broken_png_fails(self):
        (self.root / "assets/icons/nav.png").write_bytes(b"not png")
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("invalid or unreadable PNG" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
