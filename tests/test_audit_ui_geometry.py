"""Synthetic-only geometry regression. Never represents 003's private working image."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from PIL import Image

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'audit_ui_geometry.py'
spec=importlib.util.spec_from_file_location('audit_ui_geometry', SCRIPT)
lib=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)

class GeometryAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.original=root/'base.png'; self.candidate=root/'candidate.png'
        self.border=(241,121,34,255);self.divider=(50,60,70,255)
        self.im=Image.new('RGBA',(140,100),(30,30,30,255))
        # component work area: y=10..89 (80px); target 60px tall, y=20..79
        # frame [40,20,60,60], divider at x=108; gap=108-100=8px.
        self.im.paste((255,255,255,255),(40,20,100,80))
        for x in range(40,100):
            self.im.putpixel((x,20),self.border);self.im.putpixel((x,79),self.border)
        for y in range(20,80):
            self.im.putpixel((40,y),self.border);self.im.putpixel((99,y),self.border)
        for y in range(0,100):self.im.putpixel((108,y),self.divider)
        self.im.save(self.candidate)
        Image.new('RGBA',(140,100),(30,30,30,255)).save(self.original)
        self.plan={'schema_version':'1.0','approved_baseline_sha256':hashlib.sha256(self.original.read_bytes()).hexdigest(),
          'geometry':{'entities':{'frame':{'roi':[35,15,67,70],'color_rgba':list(self.border)},
                                  'divider':{'roi':[107,0,3,100],'color_rgba':list(self.divider)}},
           'constraints':[{'id':'outline','type':'rect_border','entity':'frame','thickness_px':1},
                           {'id':'divider-space','type':'horizontal_gap','left':'frame','right':'divider','expected_px':8},
                           {'id':'center','type':'vertical_center','entity':'frame','container_rect':[20,10,85,80],'tolerance_px':0},
                           {'id':'height','type':'height_fraction','entity':'frame','container_rect':[20,10,85,80],'expected':0.75},
                           {'id':'white','type':'color_samples','entity':'frame','color_rgba':[255,255,255,255],
                            'offsets':[[2,2],[30,30],[57,57]]}]}}

    def run_audit(self):
        self.im.save(self.candidate)
        return lib.audit(self.original,self.candidate,self.plan)

    def test_correct_geometry_passes(self):
        result=self.run_audit();self.assertEqual(result['status'],'PASS',result['errors'])
        self.assertEqual(result['entities']['frame']['bbox_xyxy'],[40,20,100,80])
        self.assertFalse(result['freeze_and_old_position_verified'])

    def test_gap_to_divider_not_tab_fails(self):
        self.plan['geometry']['constraints'][1]['expected_px']=7
        self.assertIn('divider-space:',str(self.run_audit()['errors']))

    def test_thicker_border_fails(self):
        for x in range(41,99):
            self.im.putpixel((x,21),self.border)
            self.im.putpixel((x,78),self.border)
        for y in range(21,79):
            self.im.putpixel((41,y),self.border)
            self.im.putpixel((98,y),self.border)
        result=self.run_audit();self.assertEqual(result['status'],'FAIL')
        self.assertTrue(any('outline:' in e for e in result['errors']))

    def test_rounded_corner_fails(self):
        self.im.putpixel((40,20),(255,255,255,255))
        self.assertTrue(any('square-corner' in e for e in self.run_audit()['errors']))

    def test_wrong_height_ratio_fails(self):
        self.plan['geometry']['constraints'][3]['expected']=0.5
        self.assertEqual(self.run_audit()['status'],'FAIL')

    def test_vertical_center_fails(self):
        self.plan['geometry']['constraints'][2]['container_rect']=[20,4,85,80]
        self.assertEqual(self.run_audit()['status'],'FAIL')

    def test_white_fill_fails(self):
        self.im.putpixel((42,22),(200,200,200,255))
        self.assertEqual(self.run_audit()['status'],'FAIL')

    def test_missing_reference_entity_fails(self):
        self.plan['geometry']['entities']['divider']['color_rgba']=[12,13,14,255]
        self.assertEqual(self.run_audit()['status'],'FAIL')

    def test_baseline_wrong_sha_blocks(self):
        self.plan['approved_baseline_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'baseline SHA256 mismatch'):
            self.run_audit()

    def test_canvas_change_blocks(self):
        self.im=self.im.resize((141,100))
        with self.assertRaisesRegex(ValueError,'dimensions differ'):
            self.run_audit()

    def test_invalid_rect_blocks(self):
        self.plan['geometry']['entities']['frame']['roi']=[0,0,500,100]
        with self.assertRaises(ValueError):self.run_audit()

if __name__=='__main__':unittest.main()
