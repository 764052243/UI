#!/usr/bin/env python3
"""Check gold-vs-browser icon color fidelity and slot-level visual centering.

Inputs MUST be actual same-viewport screenshots and browser-captured DOM/image
geometry. This is a diagnostic gate, not a retouch tool or proof of art quality.
It never resizes screenshots or shifts/recolors icons to make tests pass.
Requires Pillow.
"""
import argparse
import json
import math
import sys
from pathlib import Path, PurePosixPath
from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError


def rooted(root, relative, field):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError(field + ": unsafe path")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(field + ": unsafe path")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()) or not result.is_file():
        raise ValueError(field + ": file missing or outside delivery")
    return result


def decode(path):
    try:
        with Image.open(path) as picture:
            picture.load()
            return picture.convert("RGB")
    except (OSError, UnidentifiedImageError) as err:
        raise ValueError("unreadable screenshot " + str(path) + ": " + str(err)) from err


def parse_roi(box, size):
    if not isinstance(box, list) or len(box) != 4 or any(type(n) is not int for n in box):
        raise ValueError("roi must be four integer pixel coordinates")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise ValueError("roi outside screenshot viewport")
    return box


def numeric(value, label, lo, hi, exclusive_upper=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(label + " must be finite number")
    if value < lo or (value >= hi if exclusive_upper else value > hi):
        raise ValueError(label + " outside valid range")
    return float(value)


def color_region(gold, actual, region):
    roi = parse_roi(region.get("roi"), gold.size)
    reference = gold.crop(roi)
    candidate = actual.crop(roi)
    gate = region.get("color_gate")
    if not isinstance(gate, dict):
        raise ValueError("color_gate object required")
    kind = gate.get("sample_mode", "saturated")
    if kind not in ("saturated", "bright"):
        raise ValueError("sample_mode must be saturated or bright")
    brightness = numeric(gate.get("brightness_min"), "brightness_min", 0, 255)
    chroma = numeric(gate.get("min_rgb_chroma", 40), "min_rgb_chroma", 0, 255)
    min_pixels = gate.get("min_reference_pixels")
    if type(min_pixels) is not int or min_pixels <= 0:
        raise ValueError("min_reference_pixels must be positive integer")
    max_mean = numeric(gate.get("max_mean_ink_delta"), "max_mean_ink_delta", 0, 255)
    tolerance = numeric(gate.get("per_pixel_tolerance"), "per_pixel_tolerance", 0, 255)
    max_outliers = numeric(gate.get("max_outlier_fraction"), "max_outlier_fraction", 0, 1)
    max_full_fraction = numeric(gate.get("max_full_roi_changed_fraction"), "max_full_roi_changed_fraction", 0, 1)
    full_tol = numeric(gate.get("full_roi_tolerance"), "full_roi_tolerance", 0, 255)
    ref_colors, act_colors = list(reference.getdata()), list(candidate.getdata())
    selected = []
    for index, rgb in enumerate(ref_colors):
        m, n = max(rgb), min(rgb)
        if m >= brightness and (kind == "bright" or m - n >= chroma):
            selected.append(index)
    errors = []
    if len(selected) < min_pixels:
        errors.append("reference contains insufficient qualified foreground pixels; ROI/mask must be reviewed")
    mean_delta = None
    outlier_fraction = None
    if selected:
        differences = [
            (sum((ref_colors[i][k] - act_colors[i][k]) ** 2 for k in range(3)) / 3) ** .5
            for i in selected
        ]
        mean_delta = round(sum(differences) / len(differences), 4)
        outlier_fraction = round(sum(x > tolerance for x in differences) / len(differences), 6)
        if mean_delta > max_mean:
            errors.append("foreground color mean delta exceeds approved ROI tolerance")
        if outlier_fraction > max_outliers:
            errors.append("foreground color outlier fraction exceeds approved ROI tolerance")
    all_changed = 0
    for a, b in zip(ref_colors, act_colors):
        if max(abs(a[j] - b[j]) for j in range(3)) > full_tol:
            all_changed += 1
    full_fraction = round(all_changed / len(ref_colors), 6)
    if full_fraction > max_full_fraction:
        errors.append("full ROI pixel change exceeds threshold (shape, dark fringe or offset)")
    return {
        "id": region["id"], "roi": roi, "selected_reference_pixels": len(selected),
        "foreground_mean_rgb_distance": mean_delta, "foreground_outlier_fraction": outlier_fraction,
        "full_roi_changed_fraction": full_fraction,
        "pass": not errors, "errors": errors,
    }


def box(value, label):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(label + " must be [x,y,width,height]")
    nums = [numeric(v, label, -100000, 100000) for v in value]
    if nums[2] <= 0 or nums[3] <= 0:
        raise ValueError(label + " must have positive width and height")
    return nums


def layout_check(spec, actual):
    name = spec.get("id")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("layout id required")
    row = actual.get(name)
    if not isinstance(row, dict) or row.get("error"):
        return {"id": name, "pass": False, "errors": [name + ": browser geometry unavailable: " +
                str(row.get("error") if isinstance(row, dict) else "not captured")]}
    slot = box(row.get("slot_rect"), name + " slot")
    foreground = box(row.get("visible_rect"), name + " visible")
    target = spec.get("expected_center_delta_px")
    tolerances = spec.get("max_center_error_px")
    if (not isinstance(target, list) or not isinstance(tolerances, list) or
            len(target) != 2 or len(tolerances) != 2):
        raise ValueError(name + ": expected_center_delta_px and max_center_error_px must be [dx,dy]")
    target = [numeric(v, name + " desired delta", -10000, 10000) for v in target]
    tolerances = [numeric(v, name + " tolerance", 0, 1000) for v in tolerances]
    dx = foreground[0] + foreground[2] / 2 - (slot[0] + slot[2] / 2)
    dy = foreground[1] + foreground[3] / 2 - (slot[1] + slot[3] / 2)
    deviation = [abs(dx - target[0]), abs(dy - target[1])]
    errors = []
    if deviation[0] > tolerances[0]:
        errors.append(name + ": visible PNG foreground not horizontally centered in its designated slot")
    if deviation[1] > tolerances[1]:
        errors.append(name + ": visible PNG foreground not vertically aligned to approved slot offset")
    return {
        "id": name, "actual_center_delta_px": [round(dx, 3), round(dy, 3)],
        "desired_center_delta_px": target, "absolute_error_px": [round(v, 3) for v in deviation],
        "pass": not errors, "errors": errors,
    }


def check(root, plan):
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    if not isinstance(plan.get("reference_id"), str) or not plan["reference_id"].strip():
        raise ValueError("approved reference_id is required")
    gold = decode(rooted(root, plan.get("gold_reference"), "gold_reference"))
    rendered = decode(rooted(root, plan.get("browser_render"), "browser_render"))
    if gold.size != rendered.size:
        raise ValueError("gold/browser canvas mismatch; do not rescale to pass")
    regions = plan.get("color_regions")
    layout = plan.get("layout_checks")
    if not isinstance(regions, list) or not regions or not isinstance(layout, list) or not layout:
        raise ValueError("color_regions and layout_checks must be nonempty lists")
    seen = set()
    colors = []
    for region in regions:
        if not isinstance(region, dict) or not isinstance(region.get("id"), str) or not region["id"].strip() or region["id"] in seen:
            raise ValueError("color_region id must be unique and nonempty")
        seen.add(region["id"])
        colors.append(color_region(gold, rendered, region))
    with rooted(root, plan.get("browser_layout_report"), "browser_layout_report").open(encoding="utf-8") as file:
        measurements = json.load(file)
    if not isinstance(measurements, dict) or not isinstance(measurements.get("items"), list):
        raise ValueError("browser layout report must contain items[]")
    if measurements.get("capture_type") != "browser_dom_image_alpha":
        raise ValueError("browser layout report missing real DOM+alpha capture type")
    if measurements.get("viewport") != list(gold.size):
        raise ValueError("browser DOM viewport differs from screenshot; capture screenshot at CSS-pixel scale")
    if type(measurements.get("device_pixel_ratio")) not in (int, float):
        raise ValueError("browser layout report requires real device_pixel_ratio")
    captured = {}
    for item in measurements["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in captured:
            raise ValueError("browser layout report has missing or duplicate item id")
        captured[item["id"]] = item
    layout_out, ids = [], set()
    for item in layout:
        if not isinstance(item, dict) or item.get("id") in ids:
            raise ValueError("layout check missing/duplicate id")
        ids.add(item["id"])
        layout_out.append(layout_check(item, captured))
    errors = [e for row in colors + layout_out for e in row["errors"]]
    return {
        "status": "PASS" if not errors else "FAIL",
        "reference_id": plan["reference_id"], "viewport": list(gold.size),
        "color_regions": colors, "layout_checks": layout_out, "errors": errors,
        "manual_color_and_edge_review_required": True, "visual_fidelity_verified": False,
        "browser_execution_independently_verified": False,
        "warnings": [
            "A declaration of browser geometry cannot independently prove actual DOM execution; retain real screenshot and capture log.",
            "Dark outline, antialiasing and material aging require gold-relative manual review; never blanket-remove valid 3D dark sidewalls.",
            "Approved color/center thresholds must be fixed before comparing the candidate and may not be widened to force PASS."
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = check(args.root, json.loads(args.plan.read_text(encoding="utf-8")))
        code = 0 if report["status"] == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        report, code = {"status": "FAIL", "error": str(exc), "visual_fidelity_verified": False}, 2
    output = json.dumps(report, indent=2, ensure_ascii=False)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
