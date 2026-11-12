#!/usr/bin/env python3
"""Read-only evidence checks for high-definition UI assets reconstructed without PSD.

Validates real vector/procedural source, exported PNG dimensions, transparency
and provenance. Never claims visual 1:1 fidelity, edge quality or browser QA.
Requires Pillow.
"""
import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from PIL import Image, UnidentifiedImageError

METHODS = {"vector_redraw", "procedural_3d", "pixel_restoration", "ai_assisted"}
SVG_NS = "{http://www.w3.org/2000/svg}"
SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "use"}


def confined_file(root, name, label, prefix=None):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(label + " must be safe relative path")
    rel = PurePosixPath(name)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts or (prefix and rel.parts[0] != prefix):
        raise ValueError(label + " unsafe path")
    f = root.joinpath(*rel.parts)
    if not f.is_file() or f.stat().st_size == 0:
        raise ValueError(label + " missing or empty: " + name)
    if not f.resolve().is_relative_to(root.resolve()):
        raise ValueError(label + " escapes root")
    return f


def validate_vector(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError("invalid SVG source: " + str(exc)) from exc
    if root.tag != SVG_NS + "svg":
        raise ValueError("source SVG must use SVG namespace")
    count = 0
    for item in root.iter():
        tag = item.tag.split("}")[-1] if isinstance(item.tag, str) else ""
        if tag in ("image", "foreignObject", "script"):
            raise ValueError("fake/unsafe SVG source: embedded raster, script or foreignObject")
        for attr, val in item.attrib.items():
            if attr.split("}")[-1] == "href" and (
                val.startswith(("data:", "http:", "https:", "//", "file:")) or ".png" in val.lower()
            ):
                raise ValueError("SVG embeds external/raster content instead of vector geometry")
        if tag in SHAPES:
            count += 1
    if not count:
        raise ValueError("SVG has no vector geometry")
    return count


def positive_pair(value, label):
    if not isinstance(value, list) or len(value) != 2 or any(type(x) is not int or x <= 0 for x in value):
        raise ValueError(label + " must be two positive integers")
    return value


def check(root, plan):
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise ValueError("reconstruction-plan schema_version must be 1.0")
    if not isinstance(plan.get("reference_id"), str) or not plan["reference_id"].strip():
        raise ValueError("approved reference_id is required")
    items = plan.get("assets")
    if not isinstance(items, list) or not items:
        raise ValueError("assets must be a nonempty list")
    report = {
        "status": "FAIL", "reference_id": plan["reference_id"], "assets": [],
        "errors": [], "visual_fidelity_verified": False, "edge_quality_verified": False,
        "browser_verified": False, "original_layer_recovered": False,
        "warnings": ["Source dimensions and declared methods are not independent proof of fidelity.",
                     "SVG/3D source + sufficient PNG pixels do not prove that the shape, lighting or details match the approved image."]
    }
    seen = set()
    for idx, asset in enumerate(items):
        if not isinstance(asset, dict):
            report["errors"].append(f"assets[{idx}] must be object")
            continue
        name = asset.get("id")
        if not isinstance(name, str) or not name.strip() or name in seen:
            report["errors"].append(f"assets[{idx}] missing or duplicate id")
            continue
        seen.add(name)
        row = {"id": name, "errors": []}
        try:
            method = asset.get("method")
            if method not in METHODS:
                raise ValueError("unknown reconstruction method")
            row["method"] = method
            if asset.get("source_kind") != "reconstructed":
                raise ValueError("no-PSD reconstruction must declare source_kind=reconstructed")
            if not isinstance(asset.get("visual_unit"), str) or not asset["visual_unit"].strip():
                raise ValueError("visual_unit is required")
            source = confined_file(root, asset.get("source_path"), "source_path", prefix="sources")
            png = confined_file(root, asset.get("export_png"), "export_png", prefix="assets")
            target = positive_pair(asset.get("target_css_px"), "target_css_px")
            dpr = asset.get("target_dpr")
            if type(dpr) not in (int, float) or not 1 <= dpr <= 4:
                raise ValueError("target_dpr must be 1..4")
            required = [math.ceil(x * dpr) for x in target]
            if method == "vector_redraw":
                if source.suffix.lower() != ".svg":
                    raise ValueError("vector_redraw requires editable .svg source")
                row["vector_elements"] = validate_vector(source)
            elif method == "procedural_3d":
                if source.suffix.lower() not in (".blend", ".py", ".js", ".svg"):
                    raise ValueError("procedural_3d requires .blend/.py/.js/.svg source")
                if source.suffix.lower() == ".svg":
                    row["vector_elements"] = validate_vector(source)
            elif method == "pixel_restoration":
                native = positive_pair(asset.get("native_input_px"), "native_input_px")
                if source.suffix.lower() not in (".png", ".tif", ".tiff", ".webp"):
                    raise ValueError("pixel_restoration requires actual bitmap input source")
                if any(native[i] < required[i] for i in (0, 1)):
                    row["errors"].append("low resolution bitmap cannot become true native HD by interpolation")
            elif method == "ai_assisted":
                edited = confined_file(root, asset.get("editable_source_path"), "editable_source_path", prefix="sources")
                if edited.suffix.lower() not in (".svg", ".blend", ".py", ".js"):
                    raise ValueError("AI result needs editable vector/procedural correction source")
                if edited.suffix.lower() == ".svg":
                    row["vector_elements"] = validate_vector(edited)
                if asset.get("manual_review_status") != "reviewed":
                    row["errors"].append("AI candidate is not documented as manually reviewed")
            try:
                with Image.open(png) as image:
                    if image.format != "PNG":
                        raise ValueError("export is not PNG")
                    image.load()
                    width, height = image.size
                    rgba = image.convert("RGBA")
                    minimum, maximum = rgba.getchannel("A").getextrema()
            except (OSError, UnidentifiedImageError) as exc:
                raise ValueError("invalid output PNG: " + str(exc)) from exc
            row.update({"export_size": [width, height], "required_raster_px": required,
                        "has_transparent_pixels": minimum < 255, "has_visible_pixels": maximum > 0,
                        "source_path": asset["source_path"], "export_png": asset["export_png"]})
            if width < required[0] or height < required[1]:
                row["errors"].append("PNG smaller than target CSS × DPR")
            if maximum <= 0:
                row["errors"].append("PNG has no visible pixels")
            if asset.get("requires_alpha", True) and minimum == 255:
                row["errors"].append("independent PNG needs real transparent pixels")
        except ValueError as exc:
            row["errors"].append(str(exc))
        row["status"] = "FAIL" if row["errors"] else "PASS"
        report["assets"].append(row)
        for err in row["errors"]:
            report["errors"].append(f"{name}: {err}")
    report["status"] = "FAIL" if report["errors"] else "PASS"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        result = check(args.root, data)
        rc = 0 if result["status"] == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        result = {"status": "FAIL", "errors": [str(exc)], "visual_fidelity_verified": False}
        rc = 2
    text_out = json.dumps(result, ensure_ascii=False, indent=2)
    print(text_out)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text_out + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
