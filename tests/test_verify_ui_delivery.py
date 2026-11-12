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
        (self.root / "README.txt").write_text("Open index.html in a browser.", encoding="utf-8")
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

    def test_missing_readme_fails(self):
        (self.root / "README.txt").unlink()
        self.assertTrue(any("README missing" in e for e in self.scan()["errors"]))

    def test_css_not_linked_from_html_fails(self):
        html = self.root / "index.html"
        html.write_text(html.read_text(encoding="utf-8").replace(
            '<link rel="stylesheet" href="css/style.css">', ''
        ), encoding="utf-8")
        self.assertTrue(any("CSS/JS file not referenced" in e for e in self.scan()["errors"]))

    def test_js_not_linked_from_html_fails(self):
        html = self.root / "index.html"
        html.write_text(html.read_text(encoding="utf-8").replace(
            '<script src="js/app.js"></script>', ''
        ), encoding="utf-8")
        self.assertTrue(any("CSS/JS file not referenced" in e for e in self.scan()["errors"]))

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

    def test_icon_with_extra_transparent_space_fails_even_when_centered(self):
        icon = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        for y in range(28, 36):
            for x in range(28, 36):
                icon.putpixel((x, y), (0, 210, 255, 255))
        icon.save(self.root / "assets/icons/nav.png")
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("excessive transparent whitespace" in e for e in result["errors"]))
        self.assertTrue(result["icon_geometry"]["assets/icons/nav.png"]["centered"])

    def test_icon_visible_shape_offcenter_fails(self):
        icon = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
        for y in range(2, 6):
            for x in range(7, 11):
                icon.putpixel((x, y), (0, 210, 255, 255))
        icon.save(self.root / "assets/icons/nav.png")
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("off-center" in e for e in result["errors"]))

    def test_valid_icon_geometry_is_reported(self):
        result = self.scan()
        self.assertEqual(result["status"], "PASS", result["errors"])
        geometry = result["icon_geometry"]["assets/icons/nav.png"]
        self.assertEqual(geometry["alpha_bbox"], [2, 2, 6, 6])
        self.assertTrue(geometry["centered"])
        self.assertTrue(geometry["tightly_trimmed"])

    def test_extra_icon_missing_from_manifest_fails(self):
        (self.root / "assets/icons/extra.png").write_bytes(
            (self.root / "assets/icons/nav.png").read_bytes()
        )
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("undeclared icon file" in e for e in result["errors"]))

    def test_well_trimmed_but_baked_dark_rectangle_fails_delivery(self):
        icon = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
        for y in range(2, 46):
            for x in range(2, 46):
                icon.putpixel((x, y), (6, 16, 21, 255))
        for y in range(18, 30):
            for x in range(18, 30):
                icon.putpixel((x, y), (0, 210, 255, 255))
        icon.save(self.root / "assets/icons/nav.png")
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("baked rectangular" in e for e in result["errors"]))
        self.assertTrue(result["icon_geometry"]["assets/icons/nav.png"]["tightly_trimmed"])

    def test_well_trimmed_but_baked_white_rectangle_fails_delivery(self):
        icon = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
        for y in range(2, 46):
            for x in range(2, 46):
                icon.putpixel((x, y), (250, 250, 250, 255))
        icon.save(self.root / "assets/icons/nav.png")
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("baked rectangular" in e for e in result["errors"]))

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
        self.assertEqual(result["zip_files"], 8)

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


    def enable_v11(self, strategy="image"):
        self.manifest["schema_version"] = "1.1"
        self.manifest["background_strategy"] = strategy
        for item in self.manifest["assets"]:
            item["source_kind"] = "layer_export"
            item["reason_png"] = "original artwork requires independent image alpha"
        if strategy == "css":
            self.manifest["assets"] = [x for x in self.manifest["assets"] if x["role"] != "background"]
            (self.root / "assets/backgrounds/bg.png").unlink()
            (self.root / "css/style.css").write_text(
                'body{background-color:#071821} nav button{cursor:pointer}', encoding="utf-8")
        else:
            self.manifest["required_asset_roles"] = ["background"]
        self.write_manifest()

    def add_component(self, policy="closed", clipped=False, source="layer_export"):
        (self.root / "assets/components").mkdir(exist_ok=True)
        comp = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        box = (0, 0, 24, 24) if clipped else (3, 3, 21, 21)
        for y in range(box[1], box[3]):
            for x in range(box[0], box[2]):
                comp.putpixel((x, y), (10, 170, 240, 255))
        comp.save(self.root / "assets/components/platform.png")
        (self.root / "index.html").write_text(
            (self.root / "index.html").read_text(encoding="utf-8").replace(
                "</body>", '<img src="assets/components/platform.png" alt=""></body>'
            ), encoding="utf-8")
        self.manifest["assets"].append({
            "id": "platform", "role": "component", "path": "assets/components/platform.png",
            "source_kind": source,
            "reason_png": "complex perspective and physically layered lighting",
            "edge_policy": policy
        })
        self.write_manifest()

    def add_ornamental_frame(self):
        self.enable_v11("css")
        (self.root / "assets/components").mkdir(exist_ok=True)
        frame = Image.new("RGBA", (64, 48), (0, 0, 0, 0))
        # Independent four-sided glowing outline, intentionally transparent
        # content area. The actual panel background and text remain CSS/DOM.
        for y in range(3, 45):
            for x in range(3, 61):
                if x <= 5 or x >= 58 or y <= 5 or y >= 42:
                    frame.putpixel((x, y), (20, 160, 220, 210))
        frame.save(self.root / "assets/components/frame.png")
        (self.root / "css/style.css").write_text(
            (self.root / "css/style.css").read_text(encoding="utf-8") +
            ' .panel::before{content:"";pointer-events:none;'
            'position:absolute;inset:0;'
            'background-image:url("../assets/components/frame.png")}',
            encoding="utf-8"
        )
        self.manifest["assets"].append({
            "id": "panel-frame", "role": "component",
            "component_type": "ornamental_frame",
            "path": "assets/components/frame.png",
            "source_kind": "layer_export",
            "reason_png": "nonuniform illuminated segmented panel outline and cut corners",
            "edge_policy": "closed",
            "frame_render_strategy": "fixed_overlay",
            "frame_inner_rect": [8, 9, 56, 39]
        })
        self.manifest["required_frame_asset_ids"] = ["panel-frame"]
        self.write_manifest()

    def test_v11_real_frame_png_with_transparent_interior_passes(self):
        self.add_ornamental_frame()
        result = self.scan()
        self.assertEqual(result["status"], "PASS", result["errors"])
        frame = result["ornamental_frames"]["assets/components/frame.png"]
        self.assertTrue(frame["all_sides_and_corners_present"])
        self.assertTrue(frame["has_transparent_content_area"])
        self.assertEqual(frame["inner_visible_alpha_fraction"], 0)

    def test_v11_required_frame_missing_from_manifest_fails(self):
        self.enable_v11("css")
        self.manifest["required_frame_asset_ids"] = ["left-panel-frame"]
        self.write_manifest()
        self.assertTrue(any("required ornamental_frame PNG not delivered" in e
                            for e in self.scan()["errors"]))

    def test_v11_frame_cannot_be_renamed_generic_component_to_evade_gate(self):
        self.add_ornamental_frame()
        self.manifest["assets"][-1].pop("component_type")
        self.write_manifest()
        self.assertTrue(any("is not an ornamental_frame" in e for e in self.scan()["errors"]))

    def test_v11_opaque_matting_inside_frame_fails(self):
        self.add_ornamental_frame()
        path = self.root / "assets/components/frame.png"
        with Image.open(path) as img:
            frame = img.convert("RGBA")
        for y in range(14, 34):
            for x in range(12, 52):
                frame.putpixel((x, y), (1, 10, 15, 255))
        frame.save(path)
        self.assertTrue(any("opaque content-area matte" in e for e in self.scan()["errors"]))

    def test_v11_frame_missing_right_edge_fails(self):
        self.add_ornamental_frame()
        path = self.root / "assets/components/frame.png"
        with Image.open(path) as img:
            frame = img.convert("RGBA")
        for y in range(9, 39):
            for x in range(56, 64):
                frame.putpixel((x, y), (0, 0, 0, 0))
        frame.save(path)
        self.assertTrue(any("missing frame edge or corner" in e for e in self.scan()["errors"]))

    def test_v11_frame_missing_lower_corner_fails(self):
        self.add_ornamental_frame()
        path = self.root / "assets/components/frame.png"
        with Image.open(path) as img:
            frame = img.convert("RGBA")
        for y in range(39, 48):
            for x in range(56, 64):
                frame.putpixel((x, y), (0, 0, 0, 0))
        frame.save(path)
        self.assertTrue(any("missing frame edge or corner" in e for e in self.scan()["errors"]))

    def test_v11_frame_inner_rect_mandatory(self):
        self.add_ornamental_frame()
        self.manifest["assets"][-1].pop("frame_inner_rect")
        self.write_manifest()
        self.assertTrue(any("requires frame_inner_rect" in e for e in self.scan()["errors"]))

    def test_v11_frame_fake_tiny_hole_cannot_pass(self):
        self.add_ornamental_frame()
        self.manifest["assets"][-1]["frame_inner_rect"] = [30, 22, 34, 26]
        self.write_manifest()
        self.assertTrue(any("inner rect is too small" in e for e in self.scan()["errors"]))

    def test_v11_frame_render_strategy_mandatory(self):
        self.add_ornamental_frame()
        self.manifest["assets"][-1].pop("frame_render_strategy")
        self.write_manifest()
        self.assertTrue(any("requires frame_render_strategy" in e for e in self.scan()["errors"]))

    def test_v11_nine_slice_needs_valid_cut_geometry(self):
        self.add_ornamental_frame()
        self.manifest["assets"][-1]["frame_render_strategy"] = "nine_slice"
        self.manifest["assets"][-1]["frame_slice_px"] = [12, 12, 12, 12]
        self.write_manifest()
        self.assertEqual(self.scan()["status"], "PASS", self.scan()["errors"])
        self.manifest["assets"][-1]["frame_slice_px"] = [30, 33, 30, 33]
        self.write_manifest()
        self.assertTrue(any("nine_slice corners overlap" in e for e in self.scan()["errors"]))

    def test_v11_unreferenced_frame_png_fails(self):
        self.add_ornamental_frame()
        css = self.root / "css/style.css"
        css.write_text("body{background:#081922}", encoding="utf-8")
        self.assertTrue(any("asset not referenced by HTML/CSS/JS" in e
                            for e in self.scan()["errors"]))

    def test_v11_duplicate_required_frame_ids_rejected(self):
        self.add_ornamental_frame()
        self.manifest["required_frame_asset_ids"].append("panel-frame")
        self.write_manifest()
        self.assertTrue(any("required_frame_asset_ids must be unique" in e
                            for e in self.scan()["errors"]))

    def test_v11_css_background_without_png_passes(self):
        self.enable_v11("css")
        result = self.scan()
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertEqual(result["background_strategy"], "css")

    def test_v11_css_strategy_without_css_background_fails(self):
        self.enable_v11("css")
        (self.root / "css/style.css").write_text('nav{display:flex}', encoding="utf-8")
        self.assertTrue(any("no background property" in e for e in self.scan()["errors"]))

    def test_v11_css_strategy_with_extra_background_file_fails(self):
        self.enable_v11("css")
        Image.new("RGB", (32, 24), "#050505").save(self.root / "assets/backgrounds/excess.png")
        self.assertTrue(any("unnecessary or undeclared PNG" in e for e in self.scan()["errors"]))

    def test_v11_explicit_png_background_can_be_solid(self):
        self.enable_v11("image")
        result = self.scan()
        self.assertEqual(result["status"], "PASS", result["errors"])

    def test_v11_unrequested_solid_background_fails(self):
        self.enable_v11("image")
        self.manifest.pop("required_asset_roles")
        self.write_manifest()
        self.assertTrue(any("near-solid background image" in e for e in self.scan()["errors"]))

    def test_v11_background_with_transparency_holes_fails(self):
        self.enable_v11("image")
        with Image.open(self.root / "assets/backgrounds/bg.png") as im:
            img = im.convert("RGBA")
        img.putpixel((4, 5), (0, 0, 0, 0))
        img.save(self.root / "assets/backgrounds/bg.png")
        self.assertTrue(any("transparent holes" in e for e in self.scan()["errors"]))

    def test_v11_masked_background_fails(self):
        self.enable_v11("image")
        self.manifest["assets"][0]["source_kind"] = "masked"
        self.write_manifest()
        self.assertTrue(any("masked foreground screenshot" in e for e in self.scan()["errors"]))

    def test_v11_unclipped_component_passes(self):
        self.enable_v11("css")
        self.add_component()
        self.assertEqual(self.scan()["status"], "PASS", self.scan()["errors"])

    def test_v11_clipped_component_fails_even_if_png_exists(self):
        self.enable_v11("css")
        self.add_component(clipped=True)
        self.assertTrue(any("touches PNG canvas edge" in e for e in self.scan()["errors"]))

    def test_v11_partial_half_component_canvas_fails(self):
        self.enable_v11("css")
        self.add_component()
        img = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        for y in range(3, 9):
            for x in range(3, 21):
                img.putpixel((x, y), (0, 200, 255, 255))
        img.save(self.root / "assets/components/platform.png")
        result = self.scan()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("partial extraction" in e for e in result["errors"]))

    def test_v11_explicit_intentional_bleed_passes_geometry(self):
        self.enable_v11("css")
        self.add_component(policy="intentional_bleed", clipped=True)
        self.assertEqual(self.scan()["status"], "PASS", self.scan()["errors"])

    def test_v11_component_missing_edge_policy_fails(self):
        self.enable_v11("css")
        self.add_component()
        self.manifest["assets"][-1].pop("edge_policy")
        self.write_manifest()
        self.assertTrue(any("needs edge_policy" in e for e in self.scan()["errors"]))

    def test_v11_component_without_reason_fails(self):
        self.enable_v11("css")
        self.add_component()
        self.manifest["assets"][-1]["reason_png"] = "because"
        self.write_manifest()
        self.assertTrue(any("needs specific reason_png" in e for e in self.scan()["errors"]))

    def test_v11_duplicate_picture_assets_are_rejected(self):
        self.enable_v11("css")
        self.add_component()
        clone = self.root / "assets/components/platform-duplicate.png"
        clone.write_bytes((self.root / "assets/components/platform.png").read_bytes())
        (self.root / "index.html").write_text(
            (self.root / "index.html").read_text(encoding="utf-8").replace(
                "</body>", '<img src="assets/components/platform-duplicate.png" alt=""></body>'
            ), encoding="utf-8")
        self.manifest["assets"].append({
            "id": "platform-duplicate", "role": "component",
            "path": "assets/components/platform-duplicate.png",
            "source_kind": "layer_export",
            "reason_png": "duplicated base to test unwanted asset export",
            "edge_policy": "closed"
        })
        self.write_manifest()
        self.assertTrue(any("duplicated PNG content" in e for e in self.scan()["errors"]))

    def test_v11_required_background_role_cannot_be_removed(self):
        self.enable_v11("css")
        self.manifest["required_asset_roles"] = ["background"]
        self.write_manifest()
        self.assertTrue(any("explicitly required role not delivered" in e for e in self.scan()["errors"]))


if __name__ == "__main__":
    unittest.main()
