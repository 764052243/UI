#!/usr/bin/env python3
"""Read-only PNG export and frozen-region verifier for UI design revisions.

This is an automated file/pixel check, NOT a perceptual sharpness, text,
business correctness, or user acceptance test.

Requires: Pillow
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, UnidentifiedImageError


def read_png(path):
    """Fully verify PNG structure, then decode to RGBA for comparison."""
    if not os.path.isfile(path):
        raise ValueError("file does not exist: " + path)
    if os.path.getsize(path) <= 0:
        raise ValueError("file is empty: " + path)
    try:
        with Image.open(path) as probe:
            if probe.format != "PNG":
                raise ValueError("file is not a PNG: " + path)
            probe.verify()
        with Image.open(path) as actual:
            if actual.format != "PNG":
                raise ValueError("file is not a PNG: " + path)
            actual.load()
            return actual.convert("RGBA")
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError("PNG decode failed: " + str(exc)) from exc


def parse_region(region_text, size):
    try:
        parts = [int(part.strip()) for part in region_text.split(",")]
    except ValueError as exc:
        raise ValueError("region must contain integer x,y,width,height") from exc
    if len(parts) != 4:
        raise ValueError("region must contain x,y,width,height")
    x, y, width, height = parts
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("region has invalid origin or dimensions")
    if x + width > size[0] or y + height > size[1]:
        raise ValueError("region exceeds image bounds")
    return x, y, width, height


def compare_frozen_pixels(before, after, region, tolerance):
    """Count changed pixels inside/outside the only authorized edit region."""
    if before.size != after.size:
        raise ValueError("baseline and output dimensions differ")
    x, y, width, height = region
    delta = ImageChops.difference(before, after)
    bands = delta.split()
    maximum = bands[0]
    for band in bands[1:]:
        maximum = ImageChops.lighter(maximum, band)
    binary = maximum.point(lambda value: 255 if value > tolerance else 0)
    inside = Image.new("L", before.size, 0)
    ImageDraw.Draw(inside).rectangle(
        (x, y, x + width - 1, y + height - 1), fill=255
    )
    changed_inside = ImageChops.multiply(binary, inside).histogram()[255]
    outside = ImageChops.subtract(binary, inside)
    changed_outside = outside.histogram()[255]
    return changed_inside, changed_outside, outside.getbbox()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="final PNG file")
    parser.add_argument("--width", type=int, help="expected final width")
    parser.add_argument("--height", type=int, help="expected final height")
    parser.add_argument("--before", help="approved source PNG to preserve")
    parser.add_argument(
        "--region", help="only permitted changed rectangle: x,y,width,height"
    )
    parser.add_argument(
        "--tolerance", type=int, default=0,
        help="per-channel difference tolerated (0 = exact, default)"
    )
    parser.add_argument(
        "--require-change", action="store_true",
        help="fail if the permitted rectangle has no changed pixels"
    )
    args = parser.parse_args(argv)

    if (args.width is None) != (args.height is None):
        parser.error("--width and --height must be supplied together")
    if args.width is not None and (args.width <= 0 or args.height <= 0):
        parser.error("expected image dimensions must be positive")
    if (args.before is None) != (args.region is None):
        parser.error("--before and --region must be supplied together")
    if args.require_change and args.before is None:
        parser.error("--require-change needs --before and --region")
    if not (0 <= args.tolerance <= 255):
        parser.error("--tolerance must be in 0..255")

    result = {
        "status": "FAIL",
        "image": args.image,
        "image_ok": False,
        "preservation_verified": False,
        "manual_visual_review_required": True,
        "errors": [],
        "warnings": [
            "Dimensions and pixels cannot prove text sharpness or visual quality.",
            "User approval, business correctness and download are not tested."
        ]
    }
    try:
        after = read_png(args.image)
        result["image_ok"] = True
        result["width"], result["height"] = after.size
        result["bytes"] = os.path.getsize(args.image)
        if args.width is not None and after.size != (args.width, args.height):
            result["errors"].append(
                "expected dimensions %dx%d, got %dx%d"
                % (args.width, args.height, *after.size)
            )
        if args.before is not None:
            before = read_png(args.before)
            region = parse_region(args.region, after.size)
            inside, outside, bbox = compare_frozen_pixels(
                before, after, region, args.tolerance
            )
            result["preservation_verified"] = outside == 0
            result["changed_pixels_inside"] = inside
            result["changed_pixels_outside"] = outside
            result["changed_outside_bbox"] = bbox
            result["allowed_region"] = region
            result["pixel_tolerance"] = args.tolerance
            if args.tolerance > 0:
                result["warnings"].append(
                    "Nonzero tolerance is not an exact frozen-pixel proof."
                )
            if outside:
                result["errors"].append(
                    "changed pixels detected outside authorized region"
                )
            if args.require_change and inside == 0:
                result["errors"].append("authorized region did not change")
        else:
            result["warnings"].append(
                "No baseline/region supplied; preservation is unverified."
            )
    except ValueError as exc:
        result["errors"].append(str(exc))

    result["status"] = "PASS" if not result["errors"] else "FAIL"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
