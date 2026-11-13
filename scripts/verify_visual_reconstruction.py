#!/usr/bin/env python3
"""Read-only visual regression diagnostic for rendered UI screenshots.

Pillow required. Tests pixel/color/edge differences by critical regions against
one accepted reference of the *same canvas*. Does NOT prove visual fidelity or
allow replacing human icon/glow/typography review.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat, UnidentifiedImageError


def open_image(path):
    try:
        with Image.open(path) as im:
            im.load()
            return im.convert('RGBA')
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise ValueError(f'unreadable image: {path}: {exc}') from exc


def valid_thresholds(node, tag):
    if not isinstance(node, dict):
        raise ValueError(f'{tag} must be an object')
    fraction = node.get('max_changed_fraction')
    mean = node.get('max_mean_rgb_difference')
    tolerance = node.get('pixel_tolerance', 0)
    if isinstance(fraction, bool) or not isinstance(fraction, (float, int)) or not 0 <= fraction < 1:
        raise ValueError(f'{tag}: max_changed_fraction must be in [0,1)')
    if isinstance(mean, bool) or not isinstance(mean, (float, int)) or not 0 <= mean <= 255:
        raise ValueError(f'{tag}: max_mean_rgb_difference must be in [0,255]')
    if type(tolerance) is not int or not 0 <= tolerance <= 255:
        raise ValueError(f'{tag}: pixel_tolerance must be integer in [0,255]')
    return float(fraction), float(mean), tolerance



def validate_light_preservation(cfg):
    """Optional focused ROI gate: detect highlights/bevel/glow dimmed in HTML.

    RGB pixel diffs remain the primary test. This only checks that pixels
    designated bright in the approved image are not lost or uniformly darkened.
    Regions must be preselected to EXCLUDE text, icons, charts and changing data.
    """
    if not isinstance(cfg, dict):
        raise ValueError('light_preservation must be an object')
    threshold = cfg.get('reference_min_luminance')
    min_count = cfg.get('min_reference_highlight_pixels')
    minimum_ratio = cfg.get('min_preserved_luminance_ratio')
    max_lost = cfg.get('max_lost_highlight_fraction')
    tolerance = cfg.get('drop_tolerance', 4)
    if type(threshold) is not int or not 1 <= threshold <= 254:
        raise ValueError('light_preservation.reference_min_luminance must be integer 1..254')
    if type(min_count) is not int or min_count <= 0:
        raise ValueError('light_preservation.min_reference_highlight_pixels must be positive integer')
    if (type(minimum_ratio) not in (float, int) or
            not 0 <= minimum_ratio <= 1):
        raise ValueError('light_preservation.min_preserved_luminance_ratio must be in [0,1]')
    if (type(max_lost) not in (float, int) or
            not 0 <= max_lost <= 1):
        raise ValueError('light_preservation.max_lost_highlight_fraction must be in [0,1]')
    if type(tolerance) is not int or not 0 <= tolerance <= 255:
        raise ValueError('light_preservation.drop_tolerance must be integer 0..255')
    return threshold, min_count, float(minimum_ratio), float(max_lost), tolerance


def measure_light_preservation(reference, actual, cfg):
    threshold, min_count, min_ratio, max_lost, tol = validate_light_preservation(cfg)
    if reference.size != actual.size:
        raise ValueError('light preservation requires same-size ROI screenshots')
    ref_gray = reference.convert('RGB').convert('L')
    actual_gray = actual.convert('RGB').convert('L')
    count = 0
    ref_brightness = 0
    actual_brightness = 0
    lost_count = 0
    for ref_l, cand_l in zip(ref_gray.getdata(), actual_gray.getdata()):
        if ref_l < threshold:
            continue
        count += 1
        ref_brightness += ref_l
        actual_brightness += cand_l
        if cand_l + tol < ref_l:
            lost_count += 1
    ratio = actual_brightness / ref_brightness if ref_brightness else 0.0
    lost_fraction = lost_count / count if count else 1.0
    passed = count >= min_count and ratio >= min_ratio and lost_fraction <= max_lost
    return {
        'pass': passed,
        'reference_highlight_pixels': count,
        'min_reference_highlight_pixels': min_count,
        'mean_luminance_preservation_ratio': round(ratio, 4),
        'min_preserved_luminance_ratio': min_ratio,
        'lost_highlight_fraction': round(lost_fraction, 6),
        'max_lost_highlight_fraction': max_lost,
        'reference_min_luminance': threshold,
        'drop_tolerance': tol,
        'warning': ('Highlight protection is a localized diagnostic; it cannot identify exact glow '
                    'layers, color shifts, blur radius, opacity or 3D materials by itself.')
    }


def measure(reference, actual, cfg):
    fraction_limit, mean_limit, tol = valid_thresholds(cfg, 'thresholds')
    if reference.size != actual.size:
        raise ValueError(f'canvas mismatch: reference={reference.size}, actual={actual.size}; never stretch to pass')
    pixel_diff = ImageChops.difference(reference.convert('RGB'), actual.convert('RGB'))
    channels = pixel_diff.split()
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    delta_alpha = ImageChops.difference(reference.getchannel('A'), actual.getchannel('A'))
    maximum = ImageChops.lighter(maximum, delta_alpha)
    binary = maximum.point(lambda v: 255 if v > tol else 0)
    fraction = binary.histogram()[255] / (reference.width * reference.height)
    mean = sum(ImageStat.Stat(pixel_diff).mean) / 3
    edge_ref = reference.convert('RGB').convert('L').filter(ImageFilter.FIND_EDGES)
    edge_actual = actual.convert('RGB').convert('L').filter(ImageFilter.FIND_EDGES)
    edge_diff = ImageChops.difference(edge_ref, edge_actual)
    edge_mean = ImageStat.Stat(edge_diff).mean[0]
    result = {
        'changed_fraction': round(fraction, 6),
        'mean_rgb_difference': round(mean, 4),
        'edge_mean_difference_diagnostic_only': round(edge_mean, 4),
        'pixel_tolerance': tol,
        'max_changed_fraction': fraction_limit,
        'max_mean_rgb_difference': mean_limit,
        'pass': fraction <= fraction_limit and mean <= mean_limit,
    }
    # Legacy plans remain valid; focused light verification is opt-in only.
    if 'light_preservation' in cfg:
        result['light_preservation'] = measure_light_preservation(
            reference, actual, cfg['light_preservation'])
        result['pass'] = result['pass'] and result['light_preservation']['pass']
    return result


def run(reference_path, actual_path, plan_path):
    ref, actual = open_image(reference_path), open_image(actual_path)
    result = {
        'status': 'FAIL', 'reference': str(reference_path), 'actual': str(actual_path),
        'canvas_reference': list(ref.size), 'canvas_actual': list(actual.size),
        'all_regions_pass': False, 'manual_visual_review_required': True,
        'browser_interaction_verified': False,
        'warnings': [
            'Pixel metrics cannot certify semantic icon extraction, clean background, text correctness, layered glow, or UX.',
            'Plan thresholds must be fixed against the approved baseline before the candidate is made.',
            'User review of actual rendered PNG/HTML is still required.'
        ], 'regions': [],
    }
    if ref.size != actual.size:
        result['error'] = 'Canvas dimensions differ; compare at original common viewport; no automatic resampling.'
        return result
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    if not isinstance(plan, dict) or plan.get('schema_version') != '1.0':
        raise ValueError('plan schema_version must be 1.0')
    if not isinstance(plan.get('reference_id'), str) or not plan['reference_id'].strip():
        raise ValueError('plan requires nonempty reference_id (approved original version)')
    if not isinstance(plan.get('regions'), list) or not plan['regions']:
        raise ValueError('plan requires at least one critical ROI')
    result['reference_id'] = plan['reference_id']
    result['full_canvas'] = measure(ref, actual, plan.get('whole_canvas'))
    seen = set()
    for i, item in enumerate(plan['regions']):
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].strip() or item['id'] in seen:
            raise ValueError(f'regions[{i}] needs unique nonempty id')
        seen.add(item['id'])
        box = item.get('box')
        if not isinstance(box, list) or len(box) != 4 or any(type(n) is not int for n in box):
            raise ValueError(f'regions[{i}] box must be integer [left,top,right,bottom]')
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= ref.width and 0 <= y0 < y1 <= ref.height):
            raise ValueError(f'regions[{i}] box out of bounds')
        region = measure(ref.crop(box), actual.crop(box), item.get('thresholds'))
        region['id'], region['box'] = item['id'], box
        result['regions'].append(region)
    result['all_regions_pass'] = all(x['pass'] for x in result['regions'])
    result['status'] = 'PASS' if result['full_canvas']['pass'] and result['all_regions_pass'] else 'FAIL'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--actual', required=True, type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--report', type=Path, help='optional JSON report location')
    args = parser.parse_args()
    try:
        report = run(args.reference, args.actual, args.plan)
        code = 0 if report['status'] == 'PASS' else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        report, code = {'status': 'FAIL', 'error': str(exc), 'manual_visual_review_required': True}, 2
    output = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
    print(output)
    if args.report:
        args.report.write_text(output + '\n', encoding='utf-8')
    return code


if __name__ == '__main__':
    sys.exit(main())
