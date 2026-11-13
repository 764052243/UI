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

    def setup_header_glow_roi(self):
        """A deliberately narrow synthetic header light strip, not full UI."""
        with Image.open(self.ref) as im:
            gold = im.convert('RGB')
        for y in range(2, 5):
            for x in range(2, 26):
                gold.putpixel((x, y), (210, 220, 230))
        gold.save(self.ref)
        gold.save(self.actual)
        self.spec['regions'][0]['thresholds'] = {
            'max_changed_fraction': .50,
            'max_mean_rgb_difference': 50,
            'light_preservation': {
                'reference_min_luminance': 130,
                'min_reference_highlight_pixels': 60,
                'min_preserved_luminance_ratio': .90,
                'max_lost_highlight_fraction': .20,
                'drop_tolerance': 8
            }
        }
        self.spec['whole_canvas']['max_changed_fraction'] = .50
        self.write_plan()

    def test_retained_header_glow_passes_opt_in_light_gate(self):
        self.setup_header_glow_roi()
        result = self.run_case()
        self.assertEqual(result['status'], 'PASS')
        light = result['regions'][0]['light_preservation']
        self.assertEqual(light['reference_highlight_pixels'], 72)
        self.assertEqual(light['lost_highlight_fraction'], 0)

    def test_dimmed_header_glow_fails_even_if_rgb_average_passes(self):
        self.setup_header_glow_roi()
        self.alter((2, 2, 26, 5), (150, 160, 170))
        result = self.run_case()
        self.assertTrue(result['full_canvas']['pass'], result)
        roi = result['regions'][0]
        self.assertLess(roi['mean_rgb_difference'], roi['max_mean_rgb_difference'])
        self.assertFalse(roi['light_preservation']['pass'])
        self.assertGreater(roi['light_preservation']['lost_highlight_fraction'], .9)
        self.assertEqual(result['status'], 'FAIL')

    def test_small_local_highlight_change_within_frozen_tolerance_passes(self):
        self.setup_header_glow_roi()
        self.alter((2, 2, 4, 3), (185, 195, 205))
        self.assertEqual(self.run_case()['status'], 'PASS')

    def test_light_gate_rejects_roi_with_no_valid_reference_highlights(self):
        self.setup_header_glow_roi()
        self.spec['regions'][1]['thresholds']['light_preservation'] = {
            'reference_min_luminance': 240,
            'min_reference_highlight_pixels': 1,
            'min_preserved_luminance_ratio': .85,
            'max_lost_highlight_fraction': .20
        }
        self.write_plan()
        result = self.run_case()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['regions'][1]['light_preservation']['reference_highlight_pixels'], 0)

    def test_light_gate_rejects_relaxed_or_invalid_config(self):
        self.setup_header_glow_roi()
        self.spec['regions'][0]['thresholds']['light_preservation']['reference_min_luminance'] = 0
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'reference_min_luminance'):
            self.run_case()
        self.spec['regions'][0]['thresholds']['light_preservation']['reference_min_luminance'] = 130
        self.spec['regions'][0]['thresholds']['light_preservation']['min_preserved_luminance_ratio'] = 1.1
        self.write_plan()
        with self.assertRaisesRegex(ValueError, 'min_preserved_luminance_ratio'):
            self.run_case()

    def test_light_gate_is_optional_for_existing_v1_plan(self):
        self.setup_header_glow_roi()
        self.spec['regions'][0]['thresholds'].pop('light_preservation')
        self.write_plan()
        self.alter((2, 2, 26, 5), (150, 160, 170))
        self.assertEqual(self.run_case()['status'], 'PASS')

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
