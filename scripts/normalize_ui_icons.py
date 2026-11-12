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
from PIL import Image, ImageDraw, UnidentifiedImageError


def read_icon(path):
    try:
        with Image.open(path) as item:
            if item.format != 'PNG':
                raise ValueError('not PNG')
            item.load()
            return item.convert('RGBA')
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError('unreadable PNG: ' + str(exc)) from exc


def detect_rectangular_matte(image):
    """Conservative warning for opaque near-black/white rectangular backing.

    Uses the solid-alpha core rather than the overall alpha bbox so a faint
    glow outside a rectangular matte cannot conceal it. This is a gate for
    manual layer extraction, never an automatic background eraser.
    """
    alpha = image.getchannel('A')
    core = alpha.point(lambda a: 255 if a >= 245 else 0).getbbox()
    if core is None:
        return {'suspected': False, 'reason': 'no opaque core'}
    x0, y0, x1, y1 = core
    if x1 - x0 < 12 or y1 - y0 < 12:
        return {'suspected': False, 'reason': 'core too small'}
    rgb = image.convert('RGB')
    coords = [
        [(x, y0) for x in range(x0, x1)],
        [(x, y1 - 1) for x in range(x0, x1)],
        [(x0, y) for y in range(y0, y1)],
        [(x1 - 1, y) for y in range(y0, y1)],
    ]
    ratios = {'dark': [], 'light': []}
    for edge in coords:
        count = {'dark': 0, 'light': 0}
        for xy in edge:
            a = alpha.getpixel(xy)
            r, g, b = rgb.getpixel(xy)
            neutral = max(r, g, b) - min(r, g, b) <= 24
            if a >= 245 and neutral:
                if max(r, g, b) <= 65:
                    count['dark'] += 1
                if min(r, g, b) >= 218:
                    count['light'] += 1
        for key in ratios:
            ratios[key].append(round(count[key] / len(edge), 3))
    kind = next((key for key, scores in ratios.items()
                 if sum(value >= .82 for value in scores) >= 3), None)
    return {'suspected': kind is not None, 'matte_kind': kind,
            'opaque_core_bbox': list(core), 'border_ratios': ratios,
            'reason': ('opaque rectangular neutral border; needs source-layer or '
                       'manual semantic separation' if kind else 'no rectangular neutral border detected')}


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
    matte = detect_rectangular_matte(image)
    return {
        'canvas': [width, height], 'alpha_bbox': [x0, y0, x1, y1],
        'transparent_margins_ltrb': margins, 'max_margin_px': max_pad,
        'max_center_skew_px': max_center_skew,
        'geometrically_centered': centered, 'tightly_trimmed': tight,
        'pass': centered and tight and not matte['suspected'],
        'suspected_baked_background': matte,
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
    if info['suspected_baked_background']['suspected']:
        raise ValueError('suspected opaque rectangular background; cannot trim it away: use original layer or manual mask')
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
        raise ValueError('normalized icon failed matte/trim/center quality gate')
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
                    record['error'] = ('suspected baked background / excessive transparency / off-center icon; manual review required')
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


def render_review_sheet(source, output_path, use_normalized=False, normalized_dir=None):
    """Create a contact sheet for visual QA; never repairs icon content.

    Three identical PNG previews on checkerboard/light/dark show black/white
    matte, alpha fringing and visual imbalance that file metadata misses.
    """
    root = normalized_dir if use_normalized else source
    if root is None:
        raise ValueError('normalized directory not available')
    files = [root] if root.is_file() else sorted(root.rglob('*.png'))
    if not files:
        raise ValueError('no icons to preview')
    if output_path.resolve() in [p.resolve() for p in files]:
        raise ValueError('contact sheet cannot overwrite an input icon')
    width, row_h = 540, 160
    sheet = Image.new('RGB', (width, 30 + len(files) * row_h), (239, 243, 246))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), 'ICON REVIEW - checker / light / dark (not final QA)', fill=(20, 35, 45))
    for i, path in enumerate(files):
        ybase = 30 + i * row_h
        draw.text((12, ybase + 4), path.name.encode('ascii', 'replace').decode('ascii')[:65], fill=(25, 33, 42))
        try:
            original = read_icon(path)
            status = analyze(original)
            flags = []
            if status['suspected_baked_background']['suspected']:
                flags.append('RECTANGULAR MATTE')
            if not status['tightly_trimmed']:
                flags.append('EXTRA MARGIN')
            if not status['geometrically_centered']:
                flags.append('OFF-CENTER')
            if not flags:
                flags.append('GEOMETRY PASS / VERIFY GOLDEN MASTER')
            draw.text((12, ybase + 22), ', '.join(flags), fill=(170, 40, 20) if not status['pass'] else (30, 90, 70))
            icon = original.copy()
            icon.thumbnail((112, 96), Image.Resampling.LANCZOS)
            for index, kind in enumerate(('checker', 'light', 'dark')):
                left, top = 12 + index * 176, ybase + 47
                tile = Image.new('RGBA', (160, 102), (255, 255, 255, 255))
                if kind == 'checker':
                    td = ImageDraw.Draw(tile)
                    for yy in range(0, 102, 12):
                        for xx in range(0, 160, 12):
                            td.rectangle((xx, yy, xx + 11, yy + 11),
                                         fill=(200, 200, 200, 255) if ((xx // 12 + yy // 12) % 2) else (245, 245, 245, 255))
                elif kind == 'dark':
                    tile.paste((6, 20, 31, 255), (0, 0, 160, 102))
                tile.alpha_composite(icon, ((160 - icon.width) // 2, (102 - icon.height) // 2))
                sheet.paste(tile.convert('RGB'), (left, top))
                draw.rectangle((left, top, left + 159, top + 101), outline=(146, 151, 155))
        except ValueError as exc:
            draw.text((12, ybase + 50), 'INVALID ICON: ' + str(exc)[:55], fill=(180, 20, 20))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format='PNG')
    return str(output_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output-dir', type=Path, help='write separate trimmed files, never overwrite source')
    parser.add_argument('--padding', type=int, default=2, help='safe halo margin after alpha cropping (default 2 px)')
    parser.add_argument('--report', type=Path, help='optional JSON report path')
    parser.add_argument('--contact-sheet', type=Path, help='visual review PNG on checkerboard, light and dark')
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.padding <= 64:
            parser.error('--padding must be in 0..64')
        result = run(args.source, args.output_dir, args.padding)
        if args.contact_sheet:
            result['contact_sheet'] = render_review_sheet(
                args.source, args.contact_sheet,
                use_normalized=args.output_dir is not None,
                normalized_dir=args.output_dir
            )
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
