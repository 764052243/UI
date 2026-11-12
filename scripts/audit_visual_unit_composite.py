#!/usr/bin/env python3
"""Audit assembled UI visual units against an approved screen ROI, pixel-for-pixel.

Require a gold reference AND a same-viewport underlay screenshot with the
target unit hidden. Alpha-composite actual independent PNG layers at real HTML
positions; never re-center, resize or recolor images to make a test pass.
Reports sharpness/glow/edge concerns for manual review but cannot repair them.
"""
import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError


def source(root, value, label):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError(label + " must be a safe relative path")
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(label + " cannot escape delivery root")
    path = root.joinpath(*rel.parts)
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(label + " missing or outside delivery: " + value)
    return path


def load(path, png_only=False):
    try:
        with Image.open(path) as raw:
            if png_only and raw.format != "PNG":
                raise ValueError("layer must be PNG: " + str(path))
            raw.load()
            return raw.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("invalid image " + str(path) + ": " + str(exc)) from exc


def roi_box(box, w, h):
    if not isinstance(box, list) or len(box) != 4 or any(type(x) is not int for x in box):
        raise ValueError("roi requires four integer coordinates")
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
        raise ValueError("roi outside approved viewport")
    return tuple(box)


def metrics(gold, actual, tolerance):
    if type(tolerance) is not int or not 0 <= tolerance <= 255:
        raise ValueError("pixel_tolerance must be integer 0..255")
    diff = ImageChops.difference(gold.convert("RGB"), actual.convert("RGB"))
    maximum = ImageChops.lighter(ImageChops.lighter(diff.getchannel("R"), diff.getchannel("G")), diff.getchannel("B"))
    changed = maximum.point(lambda x: 255 if x > tolerance else 0).histogram()[255]
    return {
        "changed_fraction": round(changed / (gold.width * gold.height), 6),
        "mean_rgb_difference": round(sum(ImageStat.Stat(diff).mean) / 3, 4),
        "difference_image": diff,
    }


def examine(root, plan, output_sheet=None):
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    if not isinstance(plan.get("reference_id"), str) or not plan["reference_id"].strip():
        raise ValueError("approved reference_id is required")
    gold = load(source(root, plan.get("gold_reference"), "gold_reference"))
    underlay = load(source(root, plan.get("underlay_without_units"), "underlay_without_units"))
    if gold.size != underlay.size:
        raise ValueError("gold and underlay must have identical viewport; cannot resize them")
    if min(gold.getchannel("A").getextrema()) != 255 or min(underlay.getchannel("A").getextrema()) != 255:
        raise ValueError("gold and underlay screenshots must be opaque")
    units = plan.get("visual_units")
    if not isinstance(units, list) or not units:
        raise ValueError("visual_units must be a nonempty list")
    result = {
        "status": "FAIL", "reference_id": plan["reference_id"],
        "viewport": list(gold.size), "regions": [], "errors": [],
        "manual_edge_and_gold_review_required": True,
        "fidelity_verified": False,
        "notes": [
            "Hard ROI checks reject layer displacement/glow clipping; only a verified clean underlay permits meaningful numeric scores.",
            "RGB metrics do not prove artistic fidelity or correct anti-aliasing; review proof sheet at 100% and 400%.",
            "Dark 3D sidewalls are valid design content; do not blanket-remove black pixels."
        ],
    }
    proofs, ids = [], set()
    for index, item in enumerate(units):
        if not isinstance(item, dict):
            raise ValueError("visual unit must be object")
        uid = item.get("id")
        if not isinstance(uid, str) or not uid.strip() or uid in ids:
            raise ValueError("visual unit id missing/duplicate")
        ids.add(uid)
        box = roi_box(item.get("roi"), *gold.size)
        x0, y0, x1, y1 = box
        dims = (x1 - x0, y1 - y0)
        reference = gold.crop(box)
        actual = underlay.crop(box)
        errors, layer_reports = [], []
        layers = item.get("layers")
        if not isinstance(layers, list) or not layers:
            raise ValueError(uid + ": required ordered PNG layers missing")
        for layer in layers:
            if not isinstance(layer, dict) or not isinstance(layer.get("path"), str):
                raise ValueError(uid + ": layer path missing")
            path = source(root, layer["path"], "layer")
            image = load(path, png_only=True)
            at = layer.get("at_xy")
            if not isinstance(at, list) or len(at) != 2 or any(type(n) is not int for n in at):
                raise ValueError(uid + ": at_xy must be [int, int] in full screenshot coordinates")
            b = image.getchannel("A").getbbox()
            if b is None:
                errors.append(layer["path"] + ": fully transparent PNG")
                continue
            bx0, by0, bx1, by1 = [v + at[i % 2] for i, v in enumerate(b)]
            pad = min(b[0], b[1], image.width - b[2], image.height - b[3])
            # For a complete free-standing sprite, the original faint glow
            # must not be cut at a PNG edge. Intentional bleed is exceptional.
            bleed = layer.get("intentional_bleed", False)
            proof = layer.get("bleed_approval_reference")
            if type(bleed) is not bool:
                raise ValueError(uid + ": intentional_bleed must be boolean")
            if pad < 2 and not (bleed and isinstance(proof, str) and proof.strip()):
                errors.append(layer["path"] + ": PNG alpha touches/approaches canvas edge; glow clipped or halo unsafe")
            if bx0 < x0 or by0 < y0 or bx1 > x1 or by1 > y1:
                errors.append(layer["path"] + ": visible layer exceeds reference ROI; redraw/correct ROI, do not crop")
            actual.alpha_composite(image, (at[0] - x0, at[1] - y0))
            layer_reports.append({
                "path": layer["path"], "placed_xy": at,
                "alpha_bbox_native": list(b), "visible_bbox_global": [bx0, by0, bx1, by1],
                "min_transparent_safety_px": pad,
                "intentional_bleed": bleed,
            })
        tol = item.get("pixel_tolerance", 16)
        score = metrics(reference, actual, tol)
        max_fraction = item.get("max_changed_fraction")
        max_mean = item.get("max_mean_rgb_difference")
        if (type(max_fraction) not in (float, int) or not 0 <= max_fraction < 1 or
                type(max_mean) not in (float, int) or not 0 <= max_mean <= 255):
            raise ValueError(uid + ": both numeric thresholds required, fixed before comparing candidate")
        if score["changed_fraction"] > max_fraction:
            errors.append(uid + ": changed fraction exceeds approved ROI threshold")
        if score["mean_rgb_difference"] > max_mean:
            errors.append(uid + ": mean RGB delta exceeds approved ROI threshold")
        proofs.append((reference.convert("RGB"), actual.convert("RGB"), score["difference_image"]))
        row = {
            "id": uid, "roi": list(box), "layers": layer_reports,
            "pixel_tolerance": tol,
            "max_changed_fraction": max_fraction,
            "max_mean_rgb_difference": max_mean,
            "changed_fraction": score["changed_fraction"],
            "mean_rgb_difference": score["mean_rgb_difference"],
            "errors": errors, "status": "FAIL" if errors else "PASS",
        }
        result["regions"].append(row)
        result["errors"].extend(errors)
    result["status"] = "FAIL" if result["errors"] else "PASS"
    if output_sheet:
        if output_sheet.resolve() in [source(root, plan["gold_reference"], "gold_reference").resolve(),
                                       source(root, plan["underlay_without_units"], "underlay_without_units").resolve()]:
            raise ValueError("proof sheet cannot overwrite reference")
        if output_sheet.resolve().is_relative_to((root / "assets").resolve()):
            raise ValueError("proof sheet must not contaminate assets directory")
        max_w = max(x[0].width for x in proofs)
        total_h = sum(x[0].height + 16 for x in proofs)
        sheet = Image.new("RGB", (max_w * 3 + 32, total_h), (28, 36, 44))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(sheet)
        offset = 0
        for i, trio in enumerate(proofs):
            draw.text((5, offset + 2), result["regions"][i]["id"] + ": GOLD | COMPOSED | DIFF", fill="white")
            for col, img in enumerate(trio):
                sheet.paste(img, (8 + col * max_w, offset + 16))
            offset += trio[0].height + 16
        output_sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output_sheet, "PNG")
        result["proof_sheet"] = str(output_sheet)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--proof-sheet", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = examine(args.root, json.loads(args.plan.read_text(encoding="utf-8")), args.proof_sheet)
        status = 0 if report["status"] == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        report, status = {"status": "FAIL", "errors": [str(exc)], "fidelity_verified": False}, 2
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + "\n", encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main())
