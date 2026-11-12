#!/usr/bin/env python3
"""Read-only cutout evidence: native raster quality and complete visual-unit groups.

This does not run Photoshop, unblur a low-res image, remove a background, or
certify artistic edge quality. It checks real PNG dimensions/alpha geometry and
cross-file composition evidence for a separate JSON plan. Requires Pillow.
"""
import argparse
import json
import math
import sys
from pathlib import Path, PurePosixPath
from PIL import Image, UnidentifiedImageError


def safe_file(root, name, label):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(label + ": invalid relative path")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(label + ": path traversal")
    target = root / name
    if not target.is_file():
        raise ValueError(label + ": missing " + name)
    return target


def positive_pair(value, label):
    if not isinstance(value, list) or len(value) != 2 or any(type(x) is not int or x <= 0 for x in value):
        raise ValueError(label + " must be [positive_int, positive_int]")
    return value


def examine_png(path):
    try:
        with Image.open(path) as im:
            if im.format != "PNG":
                raise ValueError("not a PNG: " + str(path))
            im.load()
            rgba = im.convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("cannot read PNG " + str(path) + ": " + str(exc)) from exc
    box = rgba.getchannel("A").getbbox()
    if box is None:
        raise ValueError("fully transparent image: " + str(path))
    width, height = rgba.size
    margins = [box[0], box[1], width - box[2], height - box[3]]
    center_delta = [round((box[0] + box[2] - width) / 2, 2),
                    round((box[1] + box[3] - height) / 2, 2)]
    return {"canvas": [width, height], "alpha_bbox": list(box),
            "margins_ltrb": margins, "visible_size": [box[2]-box[0], box[3]-box[1]],
            "center_delta_xy_px": center_delta,
            "zero_alpha_fraction": round(rgba.getchannel("A").histogram()[0] / (width * height), 5),
            "has_partial_alpha": sum(rgba.getchannel("A").histogram()[1:255]) > 0}


def check(root, plan):
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise ValueError("unsupported cutout plan schema_version")
    assets = plan.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("assets must be nonempty")
    results, failures, groups, seen = [], [], {}, set()
    for i, a in enumerate(assets):
        if not isinstance(a, dict):
            raise ValueError("asset must be object")
        path = a.get("asset_path")
        if path in seen:
            raise ValueError("duplicate asset path")
        seen.add(path)
        fp = safe_file(root, path, "asset_path")
        info = examine_png(fp)
        group = a.get("visual_unit")
        role = a.get("layer_role")
        alignment = a.get("alignment_mode")
        source_kind = a.get("source_kind")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("visual_unit required")
        if role not in ("glyph", "plinth", "composite", "map", "standalone"):
            raise ValueError("unsupported layer_role")
        if alignment not in ("tight", "layer_anchor"):
            raise ValueError("unsupported alignment_mode")
        if source_kind not in ("layer_export", "vector_render", "masked", "reconstructed"):
            raise ValueError("source_kind required")
        target = positive_pair(a.get("target_css_px"), "target_css_px")
        native = positive_pair(a.get("source_native_px"), "source_native_px")
        dpr = a.get("target_dpr")
        if type(dpr) not in (int, float) or isinstance(dpr, bool) or not 1 <= dpr <= 4:
            raise ValueError("target_dpr must be number 1..4")
        required = [math.ceil(x * dpr) for x in target]
        canvas = info["canvas"]
        ratio_native = min(native[k] / required[k] for k in (0, 1))
        ratio_file = min(canvas[k] / required[k] for k in (0, 1))
        errors = []
        if ratio_native < 1:
            errors.append("original native pixels insufficient for CSS size at DPR; upscaling cannot restore detail")
        if ratio_file < 1:
            errors.append("exported PNG pixels insufficient for requested display DPR")
        if alignment == "tight":
            skew_limit = max(2, math.ceil(min(canvas) * 0.04))
            if abs(info["margins_ltrb"][0] - info["margins_ltrb"][2]) > skew_limit or abs(info["margins_ltrb"][1] - info["margins_ltrb"][3]) > skew_limit:
                errors.append("standalone cutout visible bbox is off-center; trim or adjust at source")
        if alignment == "layer_anchor" and role not in ("plinth", "glyph"):
            errors.append("layer_anchor only permitted for real glyph/plinth composition layers")
        preview = a.get("composite_preview")
        if preview:
            safe_file(root, preview, "composite_preview")
            examine_png(root / preview)
        report = {
            **info, "asset_path": path, "visual_unit": group, "layer_role": role,
            "source_kind": source_kind, "alignment_mode": alignment,
            "target_css_px": target, "target_dpr": dpr, "required_raster_px": required,
            "source_native_px_declared": native,
            "min_native_pixel_ratio": round(ratio_native, 3),
            "min_export_pixel_ratio": round(ratio_file, 3),
            "composite_preview": preview,
            "errors": errors, "status": "FAIL" if errors else "PASS",
        }
        results.append(report)
        failures.extend({"asset": path, "message": e} for e in errors)
        groups.setdefault(group, []).append(report)
    for name, members in groups.items():
        anchored = [m for m in members if m["alignment_mode"] == "layer_anchor"]
        if not anchored:
            continue
        roles = {m["layer_role"] for m in members}
        previews = {m["composite_preview"] for m in members if m["composite_preview"]}
        if not {"glyph", "plinth"}.issubset(roles):
            failures.append({"visual_unit": name, "message": "layered visual unit missing glyph or plinth; half-complete composition"})
        if not previews:
            failures.append({"visual_unit": name, "message": "layered visual unit missing complete composite preview"})
        elif len(previews) > 1:
            failures.append({"visual_unit": name, "message": "layered assets point to inconsistent composite previews"})
    return {"status": "PASS" if not failures else "FAIL", "assets": results,
            "failures": failures, "quality_verified": False,
            "photoshop_executed": False, "manual_gold_reference_review_required": True,
            "notes": [
                "source_native_px is a provenance claim, not independently provable from PNG alone; verify source PSD/vector evidence.",
                "PASS checks numeric geometry and membership only; it does not certify complete 3D geometry, alpha fringe or sharpness.",
                "A plinth-only PNG is not a complete business icon unless a companion glyph and composite proof are supplied."
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        result = check(args.root, plan)
        code = 0 if result["status"] == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        result, code = {"status": "FAIL", "error": str(exc),
                        "quality_verified": False, "photoshop_executed": False}, 2
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
