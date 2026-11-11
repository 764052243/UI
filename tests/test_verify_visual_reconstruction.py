"""Synthetic visual reconstruction comparisons; no customer design images."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_visual_reconstruction.py'
spec = importlib.util.spec_from_file_location('verify_visual_reconstruction', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VisualReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.ref = self.dir / 'approved.png'
        self.actual = self.dir / 'rendered.png'
        self.plan = self.dir / 'plan.json'
        Image.new('RGB', (40, 30), (10, 20, 30)).save(self.ref)
        Image.new('RGB', (40, 30), (10, 20, 30)).save(self.actual)
        self.spec = {
            'schema_version': '1.0', 'reference_id': 'approved-v1',
            'whole_canvas': {'max_changed_fraction': .10, 'max_mean_rgb_difference': 8, 'pixel_tolerance': 0},
            'regions': [
                {'id': 'nav', 'box': [0, 0, 40, 10], 'thresholds': {'max_changed_fraction': .01, 'max_mean_rgb_difference': 2}},
                {'id': 'map', 'box': [0, 10, 40, 30], 'thresholds': {'max_changed_fraction': .20, 'max_mean_rgb_difference': 12}}
            ],
        }
        self.write_plan()

    def write_plan(self):
        self.plan.write_text(json.dumps(self.spec), encoding='utf-8')

    def alter(self, box, color=(255, 220, 0)):
        with Image.open(self.actual) as current:
            rendered = current.convert('RGB')
        for y in range(box[1], box[3]):
            for x in range(box[0], box[2]):
                rendered.putpixel((x, y), color)
        rendered.save(self.actual)

    def run_case(self):
        return module.run(self.ref, self.actual, self.plan)

    def test_identical_reference_passes(self):
        r = self.run_case()
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['full_canvas']['changed_fraction'], 0)
        self.assertTrue(r['all_regions_pass'])
        self.assertTrue(r['manual_visual_review_required'])

    def test_critical_navigation_failure_not_hidden_by_small_global_fraction(self):
        self.alter((0, 0, 10, 5))
        r = self.run_case()
        self.assertTrue(r['full_canvas']['pass'])
        self.assertFalse(r['regions'][0]['pass'])
        self.assertEqual(r['status'], 'FAIL')

    def test_map_change_allowed_under_threshold(self):
        self.alter((10, 11, 12, 13), (20, 25, 32))
        r = self.run_case()
        self.assertEqual(r['status'], 'PASS')
        self.assertGreater(r['regions'][1]['changed_fraction'], 0)

    def test_large_composition_drift_fails(self):
        self.alter((0, 10, 40, 25))
        self.assertEqual(self.run_case()['status'], 'FAIL')

    def test_canvas_mismatch_fails_without_resizing(self):
        Image.new('RGB', (41, 30)).save(self.actual)
        r = self.run_case()
        self.assertEqual(r['status'], 'FAIL')
        self.assertIn('Canvas dimensions differ', r['error'])

    def test_roi_overflow_rejected(self):
        self.spec['regions'][0]['box'] = [0, 0, 99, 30]
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'out of bounds'):
            self.run_case()

    def test_duplicate_id_rejected(self):
        self.spec['regions'][1]['id'] = 'nav'
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.run_case()

    def test_missing_thresholds_rejected(self):
        del self.spec['regions'][0]['thresholds']
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'must be an object'):
            self.run_case()

    def test_excessively_permissive_fraction_rejected(self):
        self.spec['whole_canvas']['max_changed_fraction'] = 1.0
        self.write_plan()
        with self.assertRaisesRegex(ValueError, r'\[0,1\)'):
            self.run_case()

    def test_missing_reference_id_rejected(self):
        del self.spec['reference_id']
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'reference_id'):
            self.run_case()

    def test_bad_png_rejected(self):
        self.actual.write_bytes(b'NOT PNG')
        with self.assertRaisesRegex(ValueError, 'unreadable image'):
            self.run_case()

    def test_corrupted_plan_rejected(self):
        self.plan.write_text('this is not json')
        with self.assertRaises(json.JSONDecodeError):
            self.run_case()


if __name__ == '__main__':
    unittest.main()
