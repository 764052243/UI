#!/usr/bin/env python3
"""Read-only structure checker for semantic PNG assets + HTML/CSS/JS delivery.

Checks file paths, PNG decode, background dimensions, icon alpha, HTML text,
asset references, and optional ZIP integrity. Does NOT prove visual fidelity,
real interactivity, or user download success. Requires Pillow.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from PIL import Image, UnidentifiedImageError

# Keep the packaged delivery checker and the standalone icon inspector on the
# same conservative matte-detection algorithm. Running from scripts/ or from
# unittest's importlib loader must both resolve this sibling module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_ui_icons import detect_rectangular_matte


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



def inspect_ornamental_frame(rgba, asset):
    """Conservative pixel gate for a stand-alone transparent decorative frame.

    The specified inner rectangle is a content-safe area of transparent pixels;
    visual gold fidelity, actual CSS layering, and 9-slice distortion still need
    browser review. A dark panel fill belongs below this transparent overlay.
    """
    width, height = rgba.size
    bounds = asset.get("frame_inner_rect")
    if (not isinstance(bounds, list) or len(bounds) != 4 or
            any(type(v) is not int for v in bounds)):
        raise ValueError("ornamental_frame requires frame_inner_rect [left,top,right,bottom]")
    x0, y0, x1, y1 = bounds
    if not (0 < x0 < x1 < width and 0 < y0 < y1 < height):
        raise ValueError("ornamental_frame inner rect must be strictly inside PNG canvas")
    if ((x1 - x0) / width < 0.4 or (y1 - y0) / height < 0.4):
        raise ValueError("ornamental_frame inner rect is too small to prove content area")
    strategy = asset.get("frame_render_strategy")
    if strategy not in ("fixed_overlay", "nine_slice"):
        raise ValueError("ornamental_frame requires frame_render_strategy fixed_overlay/nine_slice")
    if strategy == "nine_slice":
        cuts = asset.get("frame_slice_px")
        if (not isinstance(cuts, list) or len(cuts) != 4 or
                any(type(v) is not int or v <= 0 for v in cuts)):
            raise ValueError("nine_slice ornamental_frame needs frame_slice_px [top,right,bottom,left]")
        top, right, bottom, left = cuts
        if top + bottom >= height or left + right >= width:
            raise ValueError("nine_slice corners overlap PNG canvas")
    # Independent from the declared inner rect: the whole center outside a
    # narrow perimeter must have exactly zero alpha. This prevents a manifest
    # from hiding baked header fills/icons by shrinking frame_inner_rect.
    band = asset.get("frame_perimeter_px")
    if type(band) is not int or not (1 <= band <= max(1, min(width, height) // 5)):
        raise ValueError("ornamental_frame requires narrow frame_perimeter_px within canvas limits")
    icon_ids = asset.get("frame_icon_asset_ids")
    if (not isinstance(icon_ids, list) or
            any(not isinstance(x, str) or not x.strip() for x in icon_ids) or
            len(icon_ids) != len(set(icon_ids))):
        raise ValueError("ornamental_frame requires unique frame_icon_asset_ids list (empty if no icons)")
    channel = rgba.getchannel("A")
    central = channel.crop((x0, y0, x1, y1))
    hist = central.histogram()
    nontransparent = sum(hist[1:])
    center_fraction = nontransparent / ((x1 - x0) * (y1 - y0))
    safe_rect = (band, band, width - band, height - band)
    if safe_rect[0] >= safe_rect[2] or safe_rect[1] >= safe_rect[3]:
        raise ValueError("ornamental_frame perimeter consumes full canvas")
    interior_alpha = channel.crop(safe_rect)
    interior_pixels = sum(interior_alpha.histogram()[1:])
    regions = {
        "top": (x0, 0, x1, y0),
        "bottom": (x0, y1, x1, height),
        "left": (0, y0, x0, y1),
        "right": (x1, y0, width, y1),
        "top_left": (0, 0, x0, y0),
        "top_right": (x1, 0, width, y0),
        "bottom_left": (0, y1, x0, height),
        "bottom_right": (x1, y1, width, height),
    }
    sides = {}
    for name, rect in regions.items():
        alpha_hist = channel.crop(rect).histogram()
        sides[name] = sum(alpha_hist[1:])
    return {
        "frame_inner_rect": bounds, "frame_perimeter_px": band,
        "frame_icon_asset_ids": icon_ids,
        "frame_render_strategy": strategy,
        "inner_visible_alpha_fraction": round(center_fraction, 6),
        "nonperimeter_visible_alpha_pixels": interior_pixels,
        "edge_and_corner_alpha_pixels": sides,
        "has_transparent_content_area": nontransparent == 0 and interior_pixels == 0,
        "all_sides_and_corners_present": all(v > 0 for v in sides.values())
    }


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
        if not isinstance(doc, dict) or doc.get("schema_version") not in ("1.0", "1.1"):
            raise ValueError("unsupported manifest schema_version")
        strict_roles = doc.get("schema_version") == "1.1"
        background_strategy = doc.get("background_strategy", "image")
        if strict_roles and background_strategy not in ("image", "css"):
            raise ValueError("schema 1.1 requires background_strategy=image or css")
        required_roles = doc.get("required_asset_roles", [])
        if not isinstance(required_roles, list) or any(
            value not in ("background", "icon", "component") for value in required_roles
        ):
            raise ValueError("required_asset_roles must contain only known role names")
        required_frame_ids = doc.get("required_frame_asset_ids", [])
        if (not isinstance(required_frame_ids, list) or
                any(not isinstance(value, str) or not value.strip() for value in required_frame_ids) or
                len(required_frame_ids) != len(set(required_frame_ids))):
            raise ValueError("required_frame_asset_ids must be unique nonempty strings")
        if required_frame_ids and not strict_roles:
            raise ValueError("required_frame_asset_ids needs schema_version 1.1")
        delivered_frame_ids = set()
        report["background_strategy"] = background_strategy
        if not strict_roles:
            warnings.append("Legacy schema 1.0 has no asset decision audit; prefer 1.1 for new deliveries.")
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
        if strict_roles and background_strategy == "css":
            css_text = "\n".join(sources[p] for p in css_paths)
            if not re.search(r"(?<![\w-])background(?:-color|-image)?\s*:", css_text, flags=re.I):
                errors.append("css background strategy has no background property in declared CSS")
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
        seen_pixels = {}
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
            if strict_roles:
                source_kind = asset.get("source_kind")
                reason = asset.get("reason_png")
                if source_kind not in ("layer_export", "masked", "reconstructed"):
                    errors.append("schema 1.1 asset missing source_kind: " + str(aid))
                if not isinstance(reason, str) or len(reason.strip()) < 12:
                    errors.append("schema 1.1 asset needs specific reason_png: " + str(aid))
                if role == "component" and asset.get("edge_policy") not in ("closed", "intentional_bleed"):
                    errors.append("schema 1.1 component needs edge_policy: " + str(aid))
                if role == "background" and source_kind == "masked":
                    errors.append("masked foreground screenshot cannot be valid full-canvas background: " + str(aid))
                if asset.get("component_type") is not None and asset["component_type"] != "ornamental_frame":
                    errors.append("unknown component_type; only ornamental_frame is supported: " + str(aid))
                if asset.get("component_type") == "ornamental_frame" and role != "component":
                    errors.append("ornamental_frame must have component role: " + str(aid))
                if aid in required_frame_ids and (role != "component" or
                                                 asset.get("component_type") != "ornamental_frame"):
                    errors.append("required frame asset id is not an ornamental_frame component: " + str(aid))
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
                if strict_roles and role == "component" and not p.startswith("assets/components/"):
                    raise ValueError("component must be in assets/components/: " + p)
                size, alpha = read_png(file, role)
                if role == "background" and size != (width, height):
                    errors.append("background size mismatch: " + p)
                if strict_roles and role == "background":
                    if alpha is not None and alpha[0] < 255:
                        errors.append("full-canvas background has transparent holes: " + p)
                    with Image.open(file) as backdrop:
                        # Small sample avoids decoding 4K+ images into huge color histograms.
                        sample = backdrop.convert("RGB").resize((48, 48), Image.Resampling.BILINEAR)
                        palette = sample.getcolors(maxcolors=48 * 48)
                        dominant = max((count for count, _ in palette), default=0)
                        ratio = dominant / (48 * 48)
                        report.setdefault("background_samples", {})[p] = {"dominant_exact_fraction": round(ratio, 4)}
                        if ratio > 0.985 and "background" not in required_roles:
                            errors.append("near-solid background image should use CSS unless specifically required: " + p)
                        elif ratio > 0.985:
                            warnings.append("Near-solid background PNG supplied by explicit asset requirement: " + p)
                if strict_roles and role == "component":
                    with Image.open(file) as artwork:
                        rgba = artwork.convert("RGBA")
                        bbox = rgba.getchannel("A").getbbox()
                        touches = (bbox is None or bbox[0] == 0 or bbox[1] == 0
                                   or bbox[2] == rgba.width or bbox[3] == rgba.height)
                        report.setdefault("component_edges", {})[p] = {
                            "alpha_bbox": list(bbox) if bbox else None,
                            "touches_canvas_edge": touches,
                            "edge_policy": asset.get("edge_policy")
                        }
                        if bbox is None:
                            errors.append("component has no visible content: " + p)
                        else:
                            if asset.get("component_type") == "ornamental_frame":
                                try:
                                    frame_report = inspect_ornamental_frame(rgba, asset)
                                    report.setdefault("ornamental_frames", {})[p] = frame_report
                                    if not frame_report["has_transparent_content_area"]:
                                        errors.append("ornamental_frame must be pure border without panel background or embedded interior content: " + p)
                                    if not frame_report["all_sides_and_corners_present"]:
                                        errors.append("ornamental_frame is missing frame edge or corner: " + p)
                                    delivered_frame_ids.add(aid)
                                except ValueError as frame_error:
                                    errors.append(str(frame_error) + ": " + p)
                            coverage = ((bbox[2] - bbox[0]) / rgba.width,
                                        (bbox[3] - bbox[1]) / rgba.height)
                            report["component_edges"][p]["alpha_bbox_coverage_xy"] = [
                                round(coverage[0], 4), round(coverage[1], 4)
                            ]
                            if min(coverage) < 0.65:
                                errors.append("component has oversized blank canvas or partial extraction: " + p)
                            if touches and asset.get("edge_policy") != "intentional_bleed":
                                errors.append("component touches PNG canvas edge; incomplete clip risk: " + p)
                if role == "icon" and (alpha is None or alpha[0] >= 255 or alpha[1] <= 0):
                    errors.append("icon lacks transparent/visible pixels: " + p)
                elif role == "icon":
                    # Zero-alpha exterior may hide large whitespace or unequal spacing.
                    # This is a geometry gate, not proof of clean cutout or visual fidelity.
                    with Image.open(file) as raw:
                        rgba = raw.convert("RGBA")
                        alpha_box = rgba.getchannel("A").getbbox()
                        matte_info = detect_rectangular_matte(rgba)
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
                            "tightly_trimmed": tight,
                            "suspected_baked_background": matte_info
                        }
                        if matte_info["suspected"]:
                            errors.append("icon has suspected baked rectangular black/white background: " + p)
                        if not tight:
                            errors.append("icon has excessive transparent whitespace: " + p)
                        if not centered:
                            errors.append("icon visible bounds are off-center: " + p)
                if strict_roles:
                    with Image.open(file) as raw:
                        rgba = raw.convert("RGBA")
                        fingerprint = (rgba.size, hashlib.sha256(rgba.tobytes()).hexdigest())
                    if fingerprint in seen_pixels:
                        errors.append("duplicated PNG content; reuse one shared asset: " + p +
                                      " (same as " + seen_pixels[fingerprint] + ")")
                    else:
                        seen_pixels[fingerprint] = p
                asset_paths.add(p)
                declared.append((role, p, list(size)))
                report["assets_checked"] += 1
            except ValueError as exc:
                errors.append(str(exc))
        # All linked decorative symbols must be separate PNGs with icon role.
        # This is an asset-identity check, not proof that the frame pixels
        # contain no symbolic motif in the narrow border; visual review stays
        # mandatory for this distinction.
        by_id = {
            asset.get("id"): asset for asset in assets if isinstance(asset, dict)
            and isinstance(asset.get("id"), str)
        }
        if strict_roles:
            for asset in assets:
                if not isinstance(asset, dict) or asset.get("component_type") != "ornamental_frame":
                    continue
                for icon_id in asset.get("frame_icon_asset_ids", []):
                    icon = by_id.get(icon_id)
                    if icon is None or icon.get("role") != "icon":
                        errors.append("frame-linked icon must be independently declared as role=icon: " +
                                      str(asset.get("id")) + " -> " + str(icon_id))
                    elif icon.get("path") == asset.get("path"):
                        errors.append("frame-linked icon PNG must be separate from frame PNG: " + str(icon_id))
        # A file sitting in assets/icons is still a deliverable: do not skip
        # checks by omitting it from the manifest or relabelling it as component.
        icon_folder = root / "assets" / "icons"
        actual_icons = ({p.relative_to(root).as_posix() for p in icon_folder.rglob("*.png")}
                        if icon_folder.is_dir() else set())
        declared_icons = {path for role, path, _ in declared if role == "icon"}
        for undeclared in sorted(actual_icons - declared_icons):
            errors.append("undeclared icon file skipped by manifest: " + undeclared)
        if strict_roles:
            asset_root = root / "assets"
            all_png = {p.relative_to(root).as_posix() for p in asset_root.rglob("*.png")} if asset_root.is_dir() else set()
            for extra in sorted(all_png - asset_paths):
                if extra not in actual_icons:
                    errors.append("unnecessary or undeclared PNG asset: " + extra)
        if "icon" not in roles:
            errors.append("no semantic PNG icon declared")
        if strict_roles:
            for fid in required_frame_ids:
                if fid not in delivered_frame_ids:
                    errors.append("required ornamental_frame PNG not delivered or invalid: " + fid)
            report["required_frame_asset_ids"] = required_frame_ids
            for expected in required_roles:
                if expected not in roles:
                    errors.append("explicitly required role not delivered: " + expected)
            if background_strategy == "image" and "background" not in roles:
                errors.append("image background strategy needs a full-canvas PNG background")
            if background_strategy == "css" and "background" in roles:
                errors.append("unnecessary PNG background declared under css strategy")
        elif "background" not in roles:
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
