#!/usr/bin/env python3
"""Inspect or losslessly trim transparent margins around PNG UI icons.

Never changes a source file, never resizes or redraws visible icon pixels.
Requires Pillow. Visual/semantic fidelity still requires human and golden-master review.
"""
import argparse
import json
import math
import sys
from pathlib import Path
from PIL import Image, UnidentifiedImageError


def read_icon(path):
    try:
        with Image.open(path) as item:
            if item.format != 'PNG':
                raise ValueError('not PNG')
            item.load()
            return item.convert('RGBA')
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError('unreadable PNG: ' + str(exc)) from exc


def analyze(image):
    width, height = image.size
    alpha = image.getchannel('A')
    minimum, maximum = alpha.getextrema()
    if maximum == 0:
        raise ValueError('all pixels transparent; no icon content')
    if minimum == 255:
        raise ValueError('fully opaque image; cannot infer isolated icon or clean margin')
    bbox = alpha.getbbox()  # preserve even very faint halo pixels, no arbitrary alpha threshold
    if bbox is None:
        raise ValueError('no nontransparent pixels')
    x0, y0, x1, y1 = bbox
    margins = [x0, y0, width - x1, height - y1]
    max_pad = max(2, math.ceil(min(width, height) * 0.04))
    max_center_skew = max(2, math.ceil(min(width, height) * 0.02))
    centered = abs(margins[0] - margins[2]) <= max_center_skew and abs(margins[1] - margins[3]) <= max_center_skew
    tight = max(margins) <= max_pad
    return {
        'canvas': [width, height], 'alpha_bbox': [x0, y0, x1, y1],
        'transparent_margins_ltrb': margins, 'max_margin_px': max_pad,
        'max_center_skew_px': max_center_skew,
        'geometrically_centered': centered, 'tightly_trimmed': tight,
        'pass': centered and tight,
        'manual_fidelity_review_required': True,
        'warnings': [
            'Alpha-based checks cannot detect black/white backgrounds baked into an icon.',
            'Shape balance, halo, baseline alignment and correspondence with the approved design require visual review.'
        ],
    }


def normalize(image, padding=2):
    if type(padding) is not int or not 0 <= padding <= 64:
        raise ValueError('padding must be integer in 0..64')
    info = analyze(image)  # refuse opaque, blank, or corrupted file
    x0, y0, x1, y1 = info['alpha_bbox']
    cut = image.crop((x0, y0, x1, y1))
    out = Image.new('RGBA', (cut.width + 2 * padding, cut.height + 2 * padding), (0, 0, 0, 0))
    out.paste(cut, (padding, padding))
    # Transparent trimming and translation must not stretch or redraw any visible pixels.
    new_box = out.getchannel('A').getbbox()
    if cut.tobytes() != out.crop(new_box).tobytes():
        raise ValueError('post-trim visible pixels do not match source')
    after = analyze(out)
    if not after['pass']:
        raise ValueError('normalized icon still has excessive margin or off-center alpha bounds')
    return out, info, after


def run(source, output_dir=None, padding=2):
    if not source.exists():
        raise ValueError('source path not found')
    if not source.is_file() and not source.is_dir():
        raise ValueError('source must be a PNG file or directory')
    if output_dir is not None:
        source_abs, dest_abs = source.resolve(), output_dir.resolve()
        if (source.is_dir() and (dest_abs == source_abs or source_abs in dest_abs.parents)) or (source.is_file() and dest_abs == source_abs.parent):
            raise ValueError('output directory must be separate from source; refusing in-place operations')
    files = [source] if source.is_file() else sorted(source.rglob('*.png'))
    if not files:
        raise ValueError('no PNG files to inspect')
    items = []
    for path in files:
        record = {'file': str(path), 'status': 'FAIL'}
        try:
            icon = read_icon(path)
            if output_dir is None:
                info = analyze(icon)
                record.update(info)
                record['status'] = 'PASS' if info['pass'] else 'FAIL'
                if not info['pass']:
                    record['error'] = 'excessive transparent whitespace or off-center visible bounds'
            else:
                normalized, before, after = normalize(icon, padding)
                rel = path.relative_to(source) if source.is_dir() else Path(path.name)
                target = output_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                normalized.save(target, format='PNG')
                record.update({'before': before, 'after': after, 'output': str(target), 'status': 'PASS'})
        except (ValueError, OSError) as exc:
            record['error'] = str(exc)
        items.append(record)
    return {'status': 'PASS' if all(x['status'] == 'PASS' for x in items) else 'FAIL',
            'mode': 'normalize' if output_dir is not None else 'inspect', 'icons': items,
            'manual_visual_review_required': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output-dir', type=Path, help='write separate trimmed files, never overwrite source')
    parser.add_argument('--padding', type=int, default=2, help='safe halo margin after alpha cropping (default 2 px)')
    parser.add_argument('--report', type=Path, help='optional JSON report path')
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.padding <= 64:
            parser.error('--padding must be in 0..64')
        result = run(args.source, args.output_dir, args.padding)
        code = 0 if result['status'] == 'PASS' else 1
    except ValueError as exc:
        result, code = {'status': 'FAIL', 'error': str(exc), 'manual_visual_review_required': True}, 2
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + '\n', encoding='utf-8')
    return code


if __name__ == '__main__':
    sys.exit(main())
