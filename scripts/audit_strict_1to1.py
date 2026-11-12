#!/usr/bin/env python3
"""Strict pixel evidence for approved native UI design vs actual browser screenshot.

No resampling, registration, retouch, masking, average-error forgiveness or
automatic threshold relaxation. Structural checks do not authenticate a claimed
file provenance or prove semantic PNG/HTML interactivity. Requires Pillow.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from PIL import Image, ImageChops, UnidentifiedImageError

ALLOWED_ORIGINS = {"original_export", "user_approved_native"}


def safe_file(root, name, label):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(label + " must be a safe relative path")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(label + " cannot leave delivery root")
    file = (root / name).resolve()
    if not file.is_relative_to(root.resolve()) or not file.is_file():
        raise ValueError(label + " missing/outside root")
    return file


def png(path):
    try:
        with Image.open(path) as im:
            if im.format != "PNG":
                raise ValueError("reference/render must be true PNG")
            im.load()
            return im.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("corrupt or unreadable PNG: " + str(exc)) from exc


def rect(value, size):
    if (not isinstance(value, list) or len(value) != 4 or
            any(type(v) is not int for v in value)):
        raise ValueError("ROI must be [left,top,right,bottom] integer pixels")
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise ValueError("ROI outside actual native canvas")
    return tuple(value)


def compare(a, b):
    if a.size != b.size:
        raise ValueError("reference and rendered image must have same native canvas")
    delta = ImageChops.difference(a, b)
    channels = delta.split()
    maximum = channels[0]
    for channel in channels[1:]:
        maximum = ImageChops.lighter(maximum, channel)
    changed = maximum.point(lambda x: 255 if x > 0 else 0)
    bbox = changed.getbbox()
    count = changed.histogram()[255]
    max_delta = maximum.getextrema()[1]
    return {
        "equal": count == 0, "different_pixels": count, "total_pixels": a.width * a.height,
        "different_fraction": round(count / (a.width * a.height), 6),
        "max_rgba_channel_delta": max_delta,
        "difference_bbox": list(bbox) if bbox is not None else None,
    }


def audit(root, plan):
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    ref_id = plan.get("reference_id")
    if not isinstance(ref_id, str) or not ref_id.strip():
        raise ValueError("reference_id must be nonempty")
    if plan.get("reference_origin") not in ALLOWED_ORIGINS:
        raise ValueError("comparison collage, viewer screenshot or resized thumbnail cannot be the native gold reference")
    if plan.get("reference_overlay_free") is not True:
        raise ValueError("reference_overlay_free must be explicitly affirmed")
    if plan.get("claim") != "strict_pixel_1to1":
        raise ValueError("claim must be strict_pixel_1to1")
    ref_path = safe_file(root, plan.get("reference_png"), "reference_png")
    render_path = safe_file(root, plan.get("actual_browser_png"), "actual_browser_png")
    if ref_path.samefile(render_path):
        raise ValueError("browser render cannot be the same file as reference")
    sha = hashlib.sha256(ref_path.read_bytes()).hexdigest()
    declared_sha = plan.get("reference_sha256")
    if not isinstance(declared_sha, str) or len(declared_sha) != 64 or declared_sha.lower() != sha:
        raise ValueError("approved reference SHA256 missing or changed")
    gold, rendered = png(ref_path), png(render_path)
    native_size = plan.get("reference_native_size")
    if (not isinstance(native_size, list) or len(native_size) != 2 or
            any(type(v) is not int or v <= 0 for v in native_size) or
            tuple(native_size) != gold.size):
        raise ValueError("declared native image dimensions inconsistent with gold reference")
    if gold.size != rendered.size:
        raise ValueError("actual browser screenshot does not match approved native canvas; cannot resize to pass")
    if gold.getchannel("A").getextrema()[0] != 255 or rendered.getchannel("A").getextrema()[0] != 255:
        raise ValueError("gold and browser screenshot must be fully opaque (screen composites)")
    scope = plan.get("fidelity_scope")
    if scope not in ("critical_regions", "full_page"):
        raise ValueError("fidelity_scope must be critical_regions or full_page")
    required = plan.get("required_region_ids")
    if (not isinstance(required, list) or not required or
            any(not isinstance(s, str) or not s.strip() for s in required) or
            len(set(required)) != len(required)):
        raise ValueError("required_region_ids must be a nonempty unique set")
    regions = plan.get("regions")
    if not isinstance(regions, list) or not regions:
        raise ValueError("regions must be a nonempty list")
    seen, report = set(), []
    for region in regions:
        if not isinstance(region, dict) or not isinstance(region.get("id"), str) or not region["id"].strip():
            raise ValueError("ROI requires nonempty id")
        rid = region["id"]
        if rid in seen:
            raise ValueError("duplicate ROI id: " + rid)
        seen.add(rid)
        box = rect(region.get("box"), gold.size)
        result = compare(gold.crop(box), rendered.crop(box))
        if result["difference_bbox"] is not None:
            x0, y0 = box[:2]
            b = result["difference_bbox"]
            result["difference_bbox_on_full_canvas"] = [b[0]+x0, b[1]+y0, b[2]+x0, b[3]+y0]
        report.append({"id": rid, "box": list(box), **result, "status": "PASS" if result["equal"] else "FAIL"})
    if set(required) != seen:
        raise ValueError("critical ROI coverage incomplete/unexpected: " + repr(sorted(set(required) ^ seen)))
    whole = compare(gold, rendered) if scope == "full_page" else None
    failures = [r["id"] for r in report if not r["equal"]]
    if whole and not whole["equal"]:
        failures.append("full_page")
    return {
        "status": "PASS" if not failures else "FAIL",
        "claim": "strict_pixel_1to1", "reference_id": ref_id,
        "reference_sha256_verified": True, "reference_native_size": native_size,
        "reference_origin_declared": plan["reference_origin"],
        "reference_origin_independently_verified": False,
        "reference_overlay_free_declared": True,
        "fidelity_scope": scope, "regions": report,
        "whole_page": whole, "failed_regions": failures,
        "semantic_assets_verified": False, "html_interactivity_verified": False,
        "notes": [
            "Only zero changed RGBA pixels is reported as strict pixel 1:1 for this screenshot and viewport.",
            "Declared gold provenance/overlay-free status must be checked against real uploaded original by 002.",
            "Source screenshot comparison cannot prove icon alpha, layer separability, HTML semantics or runtime interactions."
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        result = audit(args.root, plan)
        code = 0 if result["status"] == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        result, code = {"status": "FAIL", "error": str(exc), "strict_pixel_1to1_verified": False}, 2
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
