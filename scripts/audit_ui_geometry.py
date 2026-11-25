#!/usr/bin/env python3
"""Read-only, opt-in raster geometry assertions for approved UI micro-edits.

Use the *same* plan JSON with verify_micro_edit.py. This tool verifies measured
component geometry only; the companion verifies change and frozen regions.
It cannot authenticate user approval or infer semantics from arbitrary colors.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def _rect(value, size, name):
    if not isinstance(value, list) or len(value) != 4 or any(type(v) is not int for v in value):
        raise ValueError(f"{name} must be [x,y,width,height] integers")
    x, y, w, h = value
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > size[0] or y+h > size[1]:
        raise ValueError(f"{name} outside canvas or invalid")
    return (x, y, x+w, y+h)


def _color(value, name):
    if not isinstance(value, list) or len(value) != 4 or any(type(v) is not int or not 0 <= v <= 255 for v in value):
        raise ValueError(f"{name} must be four RGBA integers (0..255)")
    return tuple(value)


def _number(value, name, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be a finite number >= {minimum}")
    return value


def _matches(pixel, color, tolerance):
    return all(abs(pixel[i]-color[i]) <= tolerance for i in range(4))


def read_png(path):
    try:
        with Image.open(path) as im:
            if im.format != "PNG":
                raise ValueError(f"not a PNG: {path}")
            im.load()
            return im.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"invalid PNG: {path}: {exc}") from exc


def measure(image, plan):
    geometry = plan.get("geometry")
    if not isinstance(geometry, dict):
        raise ValueError("geometry object is required; run verify_micro_edit.py separately for freeze checks")
    definitions = geometry.get("entities")
    constraints = geometry.get("constraints")
    if not isinstance(definitions, dict) or not definitions:
        raise ValueError("geometry.entities must be a nonempty object")
    if not isinstance(constraints, list) or not constraints:
        raise ValueError("geometry.constraints must be a nonempty list")

    pixels = image.load()
    entities, errors, results = {}, [], []
    for key, config in definitions.items():
        if not isinstance(key, str) or not key or not isinstance(config, dict):
            raise ValueError("entity IDs must be nonempty strings and values objects")
        roi = _rect(config.get("roi"), image.size, key+".roi")
        color = _color(config.get("color_rgba"), key+".color_rgba")
        tol = config.get("tolerance", 0)
        if type(tol) is not int or not 0 <= tol <= 255:
            raise ValueError(key+".tolerance must be integer 0..255")
        count_min = config.get("min_pixels", 2)
        if type(count_min) is not int or count_min < 1:
            raise ValueError(key+".min_pixels must be positive integer")
        coords = [(x,y) for y in range(roi[1],roi[3]) for x in range(roi[0],roi[2])
                  if _matches(pixels[x,y], color, tol)]
        if len(coords) < count_min:
            errors.append(f"entity {key}: only {len(coords)} matching pixels, need {count_min}")
            continue
        a,b,c,d = min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords)+1,max(y for x,y in coords)+1
        entities[key] = {"bbox": (a,b,c,d), "color": color, "tolerance": tol, "matched_pixels": len(coords)}

    ids = set()
    for spec in constraints:
        if not isinstance(spec,dict):
            raise ValueError("geometry constraint must be object")
        cid, kind = spec.get("id"), spec.get("type")
        if not isinstance(cid,str) or not cid or cid in ids:
            raise ValueError("geometry constraint IDs must be unique nonempty strings")
        ids.add(cid)
        issues, observed = [], {}
        name = spec.get("entity")
        if kind in ("rect_border", "vertical_center", "height_fraction", "color_samples"):
            if name not in definitions:
                raise ValueError(f"{cid}: unknown entity")
            item = entities.get(name)
            if not item:
                issues.append("entity could not be measured")
        elif kind == "horizontal_gap":
            if spec.get("left") not in definitions or spec.get("right") not in definitions:
                raise ValueError(f"{cid}: unknown entity")
            item = None
            if spec["left"] not in entities or spec["right"] not in entities:
                issues.append("reference entity could not be measured")
        else:
            raise ValueError(f"{cid}: unsupported geometry constraint type {kind}")

        if not issues and kind == "horizontal_gap":
            l, r = entities[spec["left"]]["bbox"], entities[spec["right"]]["bbox"]
            target = _number(spec.get("expected_px"), cid+".expected_px")
            tolerance = _number(spec.get("tolerance_px",0), cid+".tolerance_px")
            gap = r[0] - l[2] # exclusive right edge -> first pixel of right entity
            observed = {"gap_px": gap, "expected_px": target, "tolerance_px": tolerance}
            if abs(gap-target)>tolerance:
                issues.append("horizontal clear gap does not match reference")
        elif not issues and kind == "vertical_center":
            box = item["bbox"]
            container = _rect(spec.get("container_rect"),image.size,cid+".container_rect")
            tolerance = _number(spec.get("tolerance_px",0),cid+".tolerance_px")
            offset = ((box[1]+box[3])-(container[1]+container[3]))/2.0
            observed = {"center_offset_px":offset,"tolerance_px":tolerance}
            if abs(offset)>tolerance:
                issues.append("vertical center offset exceeds tolerance")
        elif not issues and kind == "height_fraction":
            box=item["bbox"]
            container=_rect(spec.get("container_rect"),image.size,cid+".container_rect")
            target=_number(spec.get("expected"),cid+".expected")
            tolerance=_number(spec.get("tolerance",0),cid+".tolerance")
            ratio=(box[3]-box[1])/(container[3]-container[1])
            observed={"height_fraction":ratio,"expected":target,"tolerance":tolerance}
            if abs(ratio-target)>tolerance:
                issues.append("height fraction does not match")
        elif not issues and kind == "rect_border":
            box=item["bbox"]
            width,height=box[2]-box[0],box[3]-box[1]
            thickness=spec.get("thickness_px")
            if type(thickness) is not int or thickness < 1:
                raise ValueError(f"{cid}.thickness_px must be positive integer")
            if width <= 2*thickness or height <= 2*thickness:
                issues.append("frame too small for requested border thickness")
            else:
                col,tol=item["color"],item["tolerance"]
                wrong=0
                for y in range(box[1],box[3]):
                    for x in range(box[0],box[2]):
                        edge=min(x-box[0],box[2]-1-x,y-box[1],box[3]-1-y)<thickness
                        if edge and not _matches(pixels[x,y],col,tol):
                            wrong+=1
                # At each side midpoint the immediately adjacent *inner* pixel
                # must not be border-colored: detects thick borders and solid boxes.
                midx=(box[0]+box[2]-1)//2
                midy=(box[1]+box[3]-1)//2
                inner=[(midx,box[1]+thickness),(midx,box[3]-thickness-1),
                       (box[0]+thickness,midy),(box[2]-thickness-1,midy)]
                thick=sum(_matches(pixels[x,y],col,tol) for x,y in inner)
                observed={"bbox_xyxy":list(box),"thickness_px":thickness,
                          "missing_border_pixels":wrong,"unexpected_inner_border_samples":thick}
                if wrong: issues.append("border not a complete square-corner rectangle")
                if thick: issues.append("border thicker than requested (inner midpoint samples)")
        elif not issues and kind == "color_samples":
            box=item["bbox"]
            color=_color(spec.get("color_rgba"),cid+".color_rgba")
            tol=spec.get("tolerance",0)
            if type(tol) is not int or not 0 <= tol <= 255:
                raise ValueError(cid+".tolerance must be integer 0..255")
            samples=spec.get("offsets")
            if not isinstance(samples,list) or not samples:
                raise ValueError(cid+".offsets must be nonempty list")
            incorrect=[]
            for pt in samples:
                if not isinstance(pt,list) or len(pt)!=2 or any(type(v) is not int for v in pt):
                    raise ValueError(cid+".offsets points must be [x,y] integers")
                x,y=box[0]+pt[0],box[1]+pt[1]
                if not (box[0]<=x<box[2] and box[1]<=y<box[3]):
                    raise ValueError(cid+".offsets point outside entity bbox")
                if not _matches(pixels[x,y],color,tol): incorrect.append(pt)
            observed={"sample_count":len(samples),"failed_offsets":incorrect}
            if incorrect: issues.append("specified colors not found at target offsets")

        results.append({"id":cid,"type":kind,"status":"FAIL" if issues else "PASS",
                        "observed":observed,"errors":issues})
        errors.extend(f"{cid}: {e}" for e in issues)

    return {"status":"FAIL" if errors else "PASS", "canvas":list(image.size),
            "entities":{k:{"bbox_xyxy":list(v["bbox"]),"matched_pixels":v["matched_pixels"]} for k,v in entities.items()},
            "geometry_constraints":results,"errors":errors,
            "freeze_and_old_position_verified":False,
            "notes":["Only measured candidate raster geometry; run verify_micro_edit.py separately to verify frozen regions and old-position removal.",
                     "Reference ROI/color, baseline SHA and semantic meaning must be validated against the user's actual approved source."]}


def audit(before_path, after_path, plan):
    if plan.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    expected=plan.get("approved_baseline_sha256")
    if not isinstance(expected,str) or len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError("approved_baseline_sha256 must be an exact lowercase SHA256 from approved original PNG")
    actual=hashlib.sha256(before_path.read_bytes()).hexdigest()
    if actual!=expected:
        raise ValueError("baseline SHA256 mismatch (wrong source/old rejected candidate)")
    before,after=read_png(before_path),read_png(after_path)
    if before.size!=after.size:
        raise ValueError("candidate dimensions differ from approved baseline")
    result=measure(after,plan)
    result["baseline_sha256_verified"]=True
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before",type=Path,required=True)
    parser.add_argument("--after",type=Path,required=True)
    parser.add_argument("--plan",type=Path,required=True)
    parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    try:
        result=audit(args.before,args.after,json.loads(args.plan.read_text(encoding='utf-8')))
        exitcode=0 if result["status"]=="PASS" else 1
    except (ValueError,OSError,json.JSONDecodeError) as e:
        result={"status":"FAIL","errors":[str(e)],"baseline_sha256_verified":False}
        exitcode=2
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return exitcode

if __name__=='__main__':
    sys.exit(main())
