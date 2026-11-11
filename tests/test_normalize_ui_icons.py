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

    def test_invalid_padding_rejected(self):
        with self.assertRaisesRegex(ValueError, 'padding'):
            lib.normalize(self.icon, -1)


if __name__ == '__main__':
    unittest.main()
