#!/usr/bin/env python3
"""Read-only semantic asset edge-risk diagnostics and three-background QA sheet.

This NEVER removes backgrounds or repairs halos. It reports geometry / clipping
risk and produces previews for manual 100% and zoomed inspection. Pillow needed.
"""
import argparse
import json
import sys
from pathlib import Path, PurePosixPath
from PIL import Image, ImageDraw, UnidentifiedImageError


def safe_asset_path(root, value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("asset path must be a POSIX relative string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value or not path.parts[0] == "assets":
        raise ValueError("unsafe asset path: " + value)
    target = root / value
    if not target.is_file():
        raise ValueError("missing asset: " + value)
    return target


def inspect_png(path, role, policy="closed"):
    try:
        with Image.open(path) as source:
            if source.format != "PNG":
                raise ValueError("not a PNG: " + str(path))
            source.load()
            image = source.convert("RGBA")
    except (UnidentifiedImageError, OSError) as err:
        raise ValueError("cannot decode PNG " + str(path) + ": " + str(err)) from err
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    alpha_min, alpha_max = alpha.getextrema()
    if bbox is None:
        raise ValueError("asset is fully transparent: " + str(path))
    touches = {
        "left": bbox[0] == 0, "top": bbox[1] == 0,
        "right": bbox[2] == image.width, "bottom": bbox[3] == image.height
    }
    # Alpha gradient / matte fringing ratio is diagnostic ONLY: crisp vector edges
    # and soft light glows both may be correct depending on the golden reference.
    partial = alpha.histogram()[1:255]
    semitransparent = sum(partial)
    total = image.width * image.height
    rgba_pixels = image.getdata()
    rgb_when_invisible = sum(
        1 for r, g, b, a in rgba_pixels
        if a == 0 and (r > 0 or g > 0 or b > 0)
    )
    problems = []
    if role in ("icon", "component") and any(touches.values()) and policy != "intentional_bleed":
        problems.append("visible alpha touches canvas boundary; clipped edge or halo risk")
    if role == "background" and alpha_min < 255:
        problems.append("full-canvas background has transparent gaps; use component for overlays")
    # Uniformity is a reason to avoid a redundant PNG, not a pixel-quality proof.
    preview = image.convert("RGB").resize((48, 48), Image.Resampling.BILINEAR)
    colors = preview.getcolors(48 * 48)
    dominant = max((count for count, _ in colors), default=0) / (48 * 48)
    return {
        "dimensions": [image.width, image.height], "role": role,
        "alpha_bbox": list(bbox), "touches_edge": touches,
        "edge_policy": policy, "alpha_range": [alpha_min, alpha_max],
        "semi_alpha_fraction": round(semitransparent / total, 6),
        "invisible_rgb_fraction": round(rgb_when_invisible / total, 6),
        "dominant_color_sample_fraction": round(dominant, 4),
        "problems": problems,
        "warnings": [
            "Edge softness metrics cannot certify anti-aliasing or rule out black/white matte.",
            "Inspect checker/light/dark composition and compare to accepted original at 100% and 400%.",
        ],
        "manual_visual_review_required": True
    }


def build_sheet(files, target):
    """Make an annotated contact sheet. Not an automated proof of edge quality."""
    if target.resolve() in [p.resolve() for _, p in files]:
        raise ValueError("contact sheet cannot overwrite a source PNG")
    if any(target.resolve().is_relative_to(p.parent.resolve()) for _, p in files):
        raise ValueError("contact sheet must be outside input asset directories")
    w, h = 780, 205
    canvas = Image.new("RGB", (w, 40 + h * len(files)), (234, 238, 243))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 12), "ASSET EDGE QA - checker / light / dark | zoomed alpha edges need manual review", fill=(20, 32, 45))
    for idx, (role, path) in enumerate(files):
        y = 40 + h * idx
        image = Image.open(path).convert("RGBA")
        image.thumbnail((180, 138), Image.Resampling.LANCZOS)
        draw.text((15, y + 4), (role + ": " + path.name)[:92], fill=(25, 36, 54))
        for column, name in enumerate(["checker", "light", "dark"]):
            x = 12 + column * 256
            panel = Image.new("RGBA", (242, 160), (255, 255, 255, 255))
            if name == "dark":
                panel.paste((5, 18, 27, 255), (0, 0, 242, 160))
            if name == "checker":
                pd = ImageDraw.Draw(panel)
                for row in range(0, 160, 16):
                    for col in range(0, 242, 16):
                        pd.rectangle((col, row, col + 15, row + 15),
                                     fill=(198, 201, 206, 255) if (row // 16 + col // 16) % 2 else (242, 243, 245, 255))
            panel.alpha_composite(image, ((242 - image.width) // 2, (160 - image.height) // 2))
            canvas.paste(panel.convert("RGB"), (x, y + 31))
            draw.rectangle((x, y + 31, x + 241, y + 190), outline=(125, 135, 145))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, format="PNG")


def audit(root, manifest_path, contact_sheet=None):
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("assets"), list):
        raise ValueError("manifest must contain assets list")
    items, problems, files = [], [], []
    for obj in doc["assets"]:
        if not isinstance(obj, dict) or obj.get("role") not in ("icon", "component", "background"):
            raise ValueError("asset role must be icon/component/background")
        path = safe_asset_path(root, obj.get("path"))
        role = obj["role"]
        report = inspect_png(path, role, obj.get("edge_policy", "closed"))
        report["path"] = str(path.relative_to(root))
        items.append(report)
        files.append((role, path))
        if report["problems"]:
            problems.append({"path": report["path"], "errors": report["problems"]})
    result = {
        "status": "FAIL" if problems else "PASS", "assets": items,
        "problems": problems,
        "quality_verified": False, "manual_visual_review_required": True,
        "warnings": ["The presence/absence of jagged edges or a half-missing 3D layer requires a golden-master visual check."]
    }
    if contact_sheet is not None:
        build_sheet(files, contact_sheet)
        result["contact_sheet"] = str(contact_sheet)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.root, args.manifest, args.contact_sheet)
        status = 0 if result["status"] == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        result = {"status": "FAIL", "error": str(exc), "quality_verified": False}
        status = 2
    summary = json.dumps(result, ensure_ascii=False, indent=2)
    print(summary)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(summary + "\n", encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main())
