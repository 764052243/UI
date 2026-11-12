#!/usr/bin/env python3
"""Read-only guard for approved localized UI image edits.

Checks same-size PNGs, narrowly allowed ROIs, explicit protected regions,
nonzero change and optional darken/brighten direction. This does not edit pixels,
guarantee visual aesthetics or independently prove browser/PSD provenance.
Requires Pillow. Prefer verify_ui_artifact.py for general image health checks.
"""
import argparse
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageChops, UnidentifiedImageError


def read_png(path):
    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                raise ValueError("only actual PNG files can be compared")
            image.load()
            return image.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("invalid PNG " + str(path) + ": " + str(exc)) from exc


def rectangle(value, size, label):
    if (not isinstance(value, list) or len(value) != 4 or
            any(type(v) is not int for v in value)):
        raise ValueError(label + " must be [x,y,width,height] integers")
    x, y, w, h = value
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > size[0] or y + h > size[1]:
        raise ValueError(label + " exceeds canvas or has invalid size")
    return x, y, x+w, y+h


def inside(x, y, boxes):
    return any(a <= x < c and b <= y < d for a, b, c, d in boxes)


def luminance(rgba):
    r, g, b, a = rgba
    return (0.2126*r + 0.7152*g + 0.0722*b) * a / 255.0


def check(before, after, plan):
    if before.size != after.size:
        raise ValueError("approved baseline and candidate image dimensions must match")
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    reference = plan.get("baseline_reference_id")
    target = plan.get("target_id")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("baseline_reference_id must identify approved source")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("target_id must name actual edited element")
    allowed = plan.get("allowed_regions")
    if not isinstance(allowed, list) or not allowed:
        raise ValueError("allowed_regions must contain narrow target regions")
    allowed = [rectangle(b, before.size, "allowed region") for b in allowed]
    protected = plan.get("protected_regions", [])
    if not isinstance(protected, list):
        raise ValueError("protected_regions must be a list")
    protected = [rectangle(b, before.size, "protected region") for b in protected]
    direction = plan.get("color_direction", "any")
    if direction not in ("any", "darken", "brighten"):
        raise ValueError("color_direction must be any/darken/brighten")
    tolerance = plan.get("pixel_tolerance", 0)
    min_changed = plan.get("min_changed_pixels", 1)
    max_changed = plan.get("max_changed_pixels")
    direction_slack = plan.get("direction_slack", 0.5)
    if type(tolerance) is not int or not 0 <= tolerance <= 255:
        raise ValueError("pixel_tolerance must be integer 0..255")
    if type(min_changed) is not int or min_changed < 1:
        raise ValueError("min_changed_pixels must be positive integer")
    if max_changed is not None and (type(max_changed) is not int or max_changed < min_changed):
        raise ValueError("max_changed_pixels must be >= min_changed_pixels")
    if type(direction_slack) not in (float, int) or not math.isfinite(direction_slack) or not 0 <= direction_slack <= 8:
        raise ValueError("direction_slack must be finite numeric 0..8")
    max_delta = plan.get("max_channel_delta")
    if max_delta is not None and (type(max_delta) is not int or not 1 <= max_delta <= 255):
        raise ValueError("max_channel_delta must be integer 1..255")

    a, b = before.load(), after.load()
    x0 = min(r[0] for r in allowed)
    y0 = min(r[1] for r in allowed)
    x1 = max(r[2] for r in allowed)
    y1 = max(r[3] for r in allowed)

    # Fast, fail-safe scan outside the target bounding box for ANY drift.
    differences = ImageChops.difference(before, after)
    parts = differences.split()
    changed = parts[0]
    for band in parts[1:]:
        changed = ImageChops.lighter(changed, band)
    significant = changed.point(lambda v: 255 if v > tolerance else 0)
    histogram = significant.histogram()
    total = histogram[255]
    on_target = 0
    outside = 0
    protected_changes = 0
    wrong_direction = 0
    too_large_changes = 0
    target_lum_delta = 0.0
    outside_bbox = None
    out_l, out_t, out_r, out_b = before.width, before.height, -1, -1
    for y in range(before.height):
        for x in range(before.width):
            if significant.getpixel((x, y)) == 0:
                continue
            in_protected = inside(x, y, protected)
            if not (x0 <= x < x1 and y0 <= y < y1 and inside(x, y, allowed)) or in_protected:
                outside += 1
                if in_protected:
                    protected_changes += 1
                out_l, out_t = min(out_l, x), min(out_t, y)
                out_r, out_b = max(out_r, x + 1), max(out_b, y + 1)
                continue
            on_target += 1
            p, q = a[x, y], b[x, y]
            delta = luminance(q) - luminance(p)
            target_lum_delta += delta
            if ((direction == "darken" and delta >= -direction_slack) or
                    (direction == "brighten" and delta <= direction_slack)):
                wrong_direction += 1
            if max_delta is not None and max(abs(p[i]-q[i]) for i in range(4)) > max_delta:
                too_large_changes += 1
    if out_r >= 0:
        outside_bbox = [out_l, out_t, out_r, out_b]
    errors = []
    if outside:
        errors.append("modified pixels outside authorized target or inside protected regions")
    if on_target < min_changed:
        errors.append("target unchanged or changed fewer pixels than required")
    if max_changed is not None and on_target > max_changed:
        errors.append("modified too many target pixels (line thickness/size may have changed)")
    if wrong_direction:
        errors.append("target changed in wrong luminance direction or remained too close to original")
    if too_large_changes:
        errors.append("individual RGBA change exceeds authorized maximum")
    return {
        "status": "FAIL" if errors else "PASS",
        "baseline_reference_id": reference, "target_id": target,
        "canvas": list(before.size), "color_direction": direction,
        "changed_pixels": total, "target_changed_pixels": on_target,
        "changed_pixels_outside_target": outside,
        "changed_pixels_in_protected_regions": protected_changes,
        "changed_outside_bbox": outside_bbox,
        "wrong_direction_pixels": wrong_direction,
        "too_large_delta_pixels": too_large_changes,
        "mean_target_luminance_delta": round(target_lum_delta / on_target, 4) if on_target else None,
        "errors": errors, "preservation_verified": outside == 0,
        "target_effect_verified": on_target >= min_changed and
                                  (max_changed is None or on_target <= max_changed) and
                                  wrong_direction == 0 and too_large_changes == 0,
        "manual_visual_review_required": True,
        "notes": [
            "This verifies only image pixel effects; CSS/source edits and true user reference identity require separate evidence.",
            "For screenshot comparison, viewport, fonts, content and dynamic state must be identical; do not loosen tolerance after failure.",
            "The target ROI must be set BEFORE comparing. It cannot be expanded to excuse unauthorized changes."
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        result = check(read_png(args.before), read_png(args.after), plan)
        code = 0 if result["status"] == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        result = {"status": "FAIL", "errors": [str(exc)], "preservation_verified": False,
                  "target_effect_verified": False}
        code = 2
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
