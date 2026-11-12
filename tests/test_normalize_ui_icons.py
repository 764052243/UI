"""Icon trim/centering checks with synthetic RGBA data only."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'normalize_ui_icons.py'
spec = importlib.util.spec_from_file_location('normalize_ui_icons', SOURCE)
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)


class IconTrimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.out = self.root / 'export'
        self.path = self.source / 'nav.png'
        self.icon = Image.new('RGBA', (60, 50), (0, 0, 0, 0))
        for y in range(3, 13):
            for x in range(35, 47):
                self.icon.putpixel((x, y), (10, 220, 255, 255))
        self.icon.putpixel((34, 2), (10, 220, 255, 1))  # faint glow fringe
        self.icon.save(self.path)

    def test_offcenter_source_fails_inspection(self):
        value = lib.run(self.source)
        self.assertEqual(value['status'], 'FAIL')
        self.assertFalse(value['icons'][0]['geometrically_centered'])
        self.assertFalse(value['icons'][0]['tightly_trimmed'])

    def test_normalize_crops_and_centers_without_resampling(self):
        output, before, after = lib.normalize(self.icon, padding=2)
        self.assertEqual(output.size, (17, 15))
        self.assertEqual(after['transparent_margins_ltrb'], [2, 2, 2, 2])
        self.assertTrue(after['pass'])
        self.assertEqual(output.getpixel((2, 2))[3], 1)
        self.assertEqual(output.getpixel((3, 3)), (10, 220, 255, 255))
        self.assertEqual(self.icon.getpixel((34, 2))[3], 1)

    def test_batch_writes_new_dir_without_overwriting_original(self):
        raw = self.path.read_bytes()
        result = lib.run(self.source, self.out, padding=2)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertTrue((self.out / 'nav.png').is_file())
        self.assertTrue(lib.run(self.out)['icons'][0]['pass'])

    def test_already_tight_icon_passes_inspection(self):
        out, _, _ = lib.normalize(self.icon, 2)
        self.assertTrue(lib.analyze(out)['pass'])

    def test_fully_opaque_background_rejected(self):
        opaque = Image.new('RGB', (24, 24), '#ffffff').convert('RGBA')
        with self.assertRaisesRegex(ValueError, 'fully opaque'):
            lib.normalize(opaque)

    def test_all_transparent_rejected(self):
        with self.assertRaisesRegex(ValueError, 'all pixels transparent'):
            lib.analyze(Image.new('RGBA', (12, 12)))

    def test_large_symmetric_whitespace_rejected_even_if_centered(self):
        img = Image.new('RGBA', (128, 128))
        for y in range(45, 55):
            for x in range(60, 68):
                img.putpixel((x, y), (255, 200, 0, 255))
        result = lib.analyze(img)
        self.assertFalse(result['pass'])
        self.assertFalse(result['tightly_trimmed'])

    def test_tight_crop_does_not_change_glow_shape_or_alpha(self):
        output, before, after = lib.normalize(self.icon, 1)
        self.assertEqual(self.icon.crop(before['alpha_bbox']).tobytes(), output.crop(after['alpha_bbox']).tobytes())

    def test_bad_png_rejected(self):
        self.path.write_bytes(b'fake PNG')
        result = lib.run(self.source)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('unreadable PNG', result['icons'][0]['error'])

    def test_inplace_normalization_rejected(self):
        with self.assertRaisesRegex(ValueError, 'separate from source'):
            lib.run(self.source, self.source)

    def test_no_png_directory_rejected(self):
        empty = self.root / 'empty'
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, 'no PNG'):
            lib.run(empty)

    def test_transparent_png_with_baked_black_rectangle_is_rejected(self):
        icon = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
        for y in range(2, 46):
            for x in range(2, 46):
                icon.putpixel((x, y), (4, 12, 17, 255))
        for y in range(18, 28):
            for x in range(18, 30):
                icon.putpixel((x, y), (0, 225, 255, 255))
        diagnosis = lib.analyze(icon)
        self.assertTrue(diagnosis['geometrically_centered'])
        self.assertTrue(diagnosis['tightly_trimmed'])
        self.assertFalse(diagnosis['pass'])
        self.assertEqual(diagnosis['suspected_baked_background']['matte_kind'], 'dark')
        with self.assertRaisesRegex(ValueError, 'suspected opaque rectangular background'):
            lib.normalize(icon)

    def test_navy_panel_mat_background_is_detected(self):
        icon = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
        for y in range(2, 46):
            for x in range(2, 46):
                icon.putpixel((x, y), (8, 27, 45, 255))
        for y in range(18, 28):
            for x in range(18, 30):
                icon.putpixel((x, y), (0, 235, 245, 255))
        result = lib.analyze(icon)
        self.assertTrue(result['suspected_baked_background']['suspected'])
        self.assertEqual(result['suspected_baked_background']['matte_kind'], 'dark')

    def test_transparent_png_with_baked_white_rectangle_is_rejected(self):
        icon = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
        for y in range(2, 46):
            for x in range(2, 46):
                icon.putpixel((x, y), (250, 250, 250, 255))
        for y in range(18, 28):
            for x in range(18, 30):
                icon.putpixel((x, y), (0, 225, 255, 255))
        self.assertEqual(lib.analyze(icon)['suspected_baked_background']['matte_kind'], 'light')

    def test_glow_cannot_hide_baked_black_background(self):
        icon = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
        for y in range(6, 42):
            for x in range(6, 42):
                icon.putpixel((x, y), (5, 11, 17, 255))
        for y in range(2, 46):
            for x in range(2, 46):
                if icon.getpixel((x, y))[3] == 0:
                    icon.putpixel((x, y), (0, 180, 255, 1))
        self.assertTrue(lib.analyze(icon)['suspected_baked_background']['suspected'])

    def test_legitimate_dark_round_pedestal_not_auto_removed(self):
        icon = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
        for y in range(3, 45):
            for x in range(3, 45):
                if (x - 24) ** 2 + (y - 24) ** 2 <= 21 ** 2:
                    icon.putpixel((x, y), (4, 19, 24, 255))
        for y in range(15, 26):
            for x in range(18, 30):
                icon.putpixel((x, y), (0, 240, 250, 255))
        self.assertFalse(lib.analyze(icon)['suspected_baked_background']['suspected'])

    def test_contact_sheet_shows_three_backgrounds_and_preserves_source(self):
        raw = self.path.read_bytes()
        sheet_path = self.root / 'contact-sheet.png'
        path = lib.render_review_sheet(self.source, sheet_path)
        self.assertEqual(path, str(sheet_path))
        with Image.open(sheet_path) as image:
            self.assertEqual(image.size, (540, 190))
        self.assertEqual(self.path.read_bytes(), raw)

    def test_contact_sheet_does_not_overwrite_original_icon(self):
        with self.assertRaisesRegex(ValueError, 'cannot overwrite'):
            lib.render_review_sheet(self.path, self.path)

    def test_invalid_padding_rejected(self):
        with self.assertRaisesRegex(ValueError, 'padding'):
            lib.normalize(self.icon, -1)


if __name__ == '__main__':
    unittest.main()
