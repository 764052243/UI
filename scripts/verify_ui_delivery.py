#!/usr/bin/env python3
"""Read-only structure checker for semantic PNG assets + HTML/CSS/JS delivery.

Checks file paths, PNG decode, background dimensions, icon alpha, HTML text,
asset references, and optional ZIP integrity. Does NOT prove visual fidelity,
real interactivity, or user download success. Requires Pillow.
"""
import argparse
import json
import math
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from PIL import Image, UnidentifiedImageError


class HtmlScan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []
        self.words = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("src", "href"):
            if attrs.get(key):
                self.refs.append(attrs[key].split("?")[0].split("#")[0])

    def handle_data(self, data):
        self.words.append(data)


def safe_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(label + " must be a nonempty POSIX relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        raise ValueError(label + " cannot be absolute or contain traversal")
    if ":" in value or value.startswith("/"):
        raise ValueError(label + " must be relative")
    return p


def read_png(file, label):
    try:
        with Image.open(file) as check:
            if check.format != "PNG":
                raise ValueError(label + " is not PNG: " + str(file))
            check.verify()
        with Image.open(file) as img:
            if img.format != "PNG":
                raise ValueError(label + " is not PNG: " + str(file))
            img.load()
            size = img.size
            mode = img.mode
            alpha = img.getchannel("A").getextrema() if "A" in img.getbands() else None
            if mode == "P" and "transparency" in img.info:
                alpha = img.convert("RGBA").getchannel("A").getextrema()
        return size, alpha
    except (OSError, SyntaxError, UnidentifiedImageError) as exc:
        raise ValueError(label + " invalid or unreadable PNG: " + str(exc)) from exc


def resolve_reference(source, ref):
    if not ref or ref.startswith(("http:", "https:", "data:", "#", "javascript:", "//")):
        return None
    from posixpath import normpath, dirname, join
    result = normpath(join(dirname(source), ref))
    if result == ".." or result.startswith("../") or result.startswith("/"):
        return None
    return result


def referenced_assets(source, text):
    refs = []
    if source.endswith(".html"):
        parser = HtmlScan()
        parser.feed(text)
        refs.extend(parser.refs)
    refs.extend(re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", text))
    refs.extend(re.findall(r"['\"]((?:\.\./|\./)?assets/[^'\"]+\.png)['\"]", text))
    return {normalized for ref in refs if (normalized := resolve_reference(source, ref))}


def scan(root, zip_path=None):
    errors = []
    warnings = [
        "PNG metadata cannot detect foreground UI baked into a background.",
        "Transparent alpha cannot prove an icon was cleanly isolated.",
        "HTML structure cannot prove a real click handler or visual equivalence.",
        "Browser run, screenshot comparison, and user download remain unverified."
    ]
    report = {
        "status": "FAIL", "root": str(root), "errors": errors,
        "warnings": warnings, "assets_checked": 0, "html_found": False,
        "interaction_runtime_verified": False, "visual_verified": False
    }
    try:
        manifest_path = root / "asset-manifest.json"
        if not manifest_path.is_file():
            raise ValueError("asset-manifest.json is missing")
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or doc.get("schema_version") != "1.0":
            raise ValueError("unsupported manifest schema_version")
        canvas = doc.get("canvas")
        if not isinstance(canvas, dict):
            raise ValueError("canvas object is missing")
        width, height = canvas.get("width"), canvas.get("height")
        if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
            raise ValueError("canvas width/height must be positive integers")
        report["canvas"] = [width, height]

        def required_file(value, name, extension):
            rel = safe_path(value, name)
            if rel.suffix.lower() != extension:
                raise ValueError(name + " must have extension " + extension)
            actual = root / str(rel)
            if not actual.is_file() or actual.stat().st_size <= 0:
                raise ValueError(name + " missing or empty: " + str(rel))
            return str(rel), actual

        html_path, html_file = required_file(doc.get("entry_html"), "entry_html", ".html")
        report["html_found"] = True
        required_file("README.txt", "README", ".txt")
        css_paths = doc.get("css")
        js_paths = doc.get("js")
        if not isinstance(css_paths, list) or not css_paths:
            raise ValueError("css must have at least one path")
        if not isinstance(js_paths, list) or not js_paths:
            raise ValueError("js must have at least one path")

        sources = {html_path: html_file.read_text(encoding="utf-8")}
        for name, group, ext in (("css", css_paths, ".css"), ("js", js_paths, ".js")):
            for item in group:
                p, full = required_file(item, name, ext)
                sources[p] = full.read_text(encoding="utf-8")
        html_refs = HtmlScan()
        html_refs.feed(sources[html_path])
        for source_file in [*css_paths, *js_paths]:
            if source_file not in html_refs.refs:
                errors.append("CSS/JS file not referenced from HTML: " + source_file)
        preview_path, preview_file = required_file(doc.get("preview"), "preview", ".png")
        preview_size, _ = read_png(preview_file, "preview")
        if preview_size != (width, height):
            errors.append("preview dimensions differ from canvas")
        report["preview_dimensions"] = list(preview_size)

        assets = doc.get("assets")
        if not isinstance(assets, list) or not assets:
            raise ValueError("assets must be a nonempty list")
        roles, asset_paths, asset_ids = [], set(), set()
        declared = []
        for i, asset in enumerate(assets):
            if not isinstance(asset, dict):
                errors.append("assets[%d] must be an object" % i)
                continue
            role, aid = asset.get("role"), asset.get("id")
            if role not in ("background", "icon", "component"):
                errors.append("assets[%d] has unknown role" % i)
                continue
            if not isinstance(aid, str) or not aid.strip() or aid in asset_ids:
                errors.append("assets[%d] has missing/duplicate id" % i)
                continue
            asset_ids.add(aid)
            roles.append(role)
            try:
                p, file = required_file(asset.get("path"), "asset", ".png")
                if p in asset_paths:
                    raise ValueError("duplicate asset file path: " + p)
                if not p.startswith("assets/"):
                    raise ValueError("asset path must be inside assets/: " + p)
                if role == "icon" and not p.startswith("assets/icons/"):
                    raise ValueError("icon must be in assets/icons/: " + p)
                if role == "background" and not p.startswith("assets/backgrounds/"):
                    raise ValueError("background must be in assets/backgrounds/: " + p)
                size, alpha = read_png(file, role)
                if role == "background" and size != (width, height):
                    errors.append("background size mismatch: " + p)
                if role == "icon" and (alpha is None or alpha[0] >= 255 or alpha[1] <= 0):
                    errors.append("icon lacks transparent/visible pixels: " + p)
                elif role == "icon":
                    # Zero-alpha exterior may hide large whitespace or unequal spacing.
                    # This is a geometry gate, not proof of clean cutout or visual fidelity.
                    with Image.open(file) as raw:
                        alpha_box = raw.convert("RGBA").getchannel("A").getbbox()
                    if alpha_box is None:
                        errors.append("icon contains no visible alpha content: " + p)
                    else:
                        x0, y0, x1, y1 = alpha_box
                        margins = [x0, y0, size[0] - x1, size[1] - y1]
                        max_pad = max(2, math.ceil(min(size) * 0.04))
                        center_skew = max(2, math.ceil(min(size) * 0.02))
                        centered = (abs(margins[0] - margins[2]) <= center_skew and
                                    abs(margins[1] - margins[3]) <= center_skew)
                        tight = max(margins) <= max_pad
                        report.setdefault("icon_geometry", {})[p] = {
                            "alpha_bbox": list(alpha_box),
                            "transparent_margins_ltrb": margins,
                            "max_pad_px": max_pad,
                            "centered": centered,
                            "tightly_trimmed": tight
                        }
                        if not tight:
                            errors.append("icon has excessive transparent whitespace: " + p)
                        if not centered:
                            errors.append("icon visible bounds are off-center: " + p)
                asset_paths.add(p)
                declared.append((role, p, list(size)))
                report["assets_checked"] += 1
            except ValueError as exc:
                errors.append(str(exc))
        # A file sitting in assets/icons is still a deliverable: do not skip
        # checks by omitting it from the manifest or relabelling it as component.
        icon_folder = root / "assets" / "icons"
        actual_icons = ({p.relative_to(root).as_posix() for p in icon_folder.rglob("*.png")}
                        if icon_folder.is_dir() else set())
        declared_icons = {path for role, path, _ in declared if role == "icon"}
        for undeclared in sorted(actual_icons - declared_icons):
            errors.append("undeclared icon file skipped by manifest: " + undeclared)
        if "icon" not in roles:
            errors.append("no semantic PNG icon declared")
        if "background" not in roles:
            errors.append("no full-canvas background declared")
        report["assets"] = [{"role": r, "path": p, "dimensions": s} for r, p, s in declared]

        refs = set()
        for source, text in sources.items():
            refs |= referenced_assets(source, text)
        for p in asset_paths:
            if p not in refs:
                errors.append("asset not referenced by HTML/CSS/JS: " + p)
        if preview_path in refs:
            errors.append("preview used as page content/background: " + preview_path)
        if not asset_paths.intersection(refs):
            errors.append("no actual semantic assets referenced")
        report["referenced_assets"] = sorted(asset_paths.intersection(refs))

        parser = HtmlScan()
        parser.feed(sources[html_path])
        visible = " ".join(parser.words)
        visible = " ".join(visible.split())
        must_text = doc.get("required_text", [])
        if not isinstance(must_text, list) or any(not isinstance(x, str) for x in must_text):
            errors.append("required_text must be an array of strings")
        else:
            for phrase in must_text:
                if phrase.strip() and phrase not in visible:
                    errors.append("HTML text missing: " + phrase)
        interactions = doc.get("required_interactions", [])
        if not isinstance(interactions, list) or any(not isinstance(x, str) for x in interactions):
            errors.append("required_interactions must be an array of strings")
        else:
            report["declared_interactions"] = interactions
            if interactions:
                warnings.append("Declared interactions require browser click testing.")
        # A screenshot-only HTML should not be mistaken for a semantic layout.
        if not parser.words or not visible.strip():
            errors.append("HTML has no selectable visible text")

        if zip_path is not None:
            if not zip_path.is_file():
                errors.append("ZIP does not exist: " + str(zip_path))
            else:
                with zipfile.ZipFile(zip_path, "r") as archive:
                    if archive.testzip() is not None:
                        errors.append("ZIP CRC check failed")
                    listed = {i.filename for i in archive.infolist() if not i.is_dir()}
                    if any(name.startswith("/") or ".." in PurePosixPath(name).parts or "\\" in name for name in listed):
                        errors.append("ZIP contains unsafe paths")
                    disk = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
                    if disk != listed:
                        errors.append("ZIP file list does not exactly match delivery directory")
                    report["zip_files"] = len(listed)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        errors.append(str(exc))
    report["status"] = "PASS" if not errors else "FAIL"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delivery", type=Path)
    parser.add_argument("--zip", dest="zip_path", type=Path)
    args = parser.parse_args()
    result = scan(args.delivery, args.zip_path)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
