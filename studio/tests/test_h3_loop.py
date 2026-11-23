import copy
import json
import unittest
from studio import h3_loop


class LoopTests(unittest.TestCase):
    def rows(self):
        return [dict(shot_id=f'SH{i}', prompt_text=f'prompt {i}', frames=56,
                     seed=i, recipe={'steps':20,'width':608,'height':352},
                     stack_state={'picks':[{'name':f'identity{i}'}]},
                     media_state=[{'file':f'angle{i}.png'}], fingerprint=f'fp{i}')
                for i in (1,2)]

    def execute(self, code, inputs, count):
        env={'inputs':inputs,'outputs':[None]*count}
        try:
            exec(code, env)
        except (ValueError, TypeError, KeyError, IndexError):
            pass  # Dynamic Script exposes exceptions instead of raising.
        return env['outputs']

    def test_plan_and_reference_selection(self):
        bundle=h3_loop.export(self.rows(), 'draft001')
        text=json.dumps(bundle)
        plan, fingerprint, name=self.execute(h3_loop.PLAN_CODE,[text],8)[:3]
        self.assertEqual(json.loads(plan)['shots'][1]['prompt'],'prompt 2')
        self.assertEqual(name,'draft001')
        self.assertEqual(len(fingerprint),64)
        stack,media=self.execute(h3_loop.SELECT_CODE,[text,2],2)
        self.assertEqual(json.loads(stack)['picks'][0]['name'],'identity2')
        self.assertEqual(json.loads(media)[0]['file'],'angle2.png')

    def test_bad_file_or_index_emits_invalid_json_not_empty_fallback(self):
        for text in ('',None,'{}','broken'):
            self.assertEqual(self.execute(h3_loop.PLAN_CODE,[text],3)[0], 'INVALID_PRODUCTION_BUNDLE')
        text=json.dumps(h3_loop.export(self.rows(),'draft001'))
        for i in (0,3,-1):
            self.assertEqual(self.execute(h3_loop.SELECT_CODE,[text,i],2), ['INVALID_SHOT_SELECTION']*2)

    def test_changes_invalidate_and_tampering_fails(self):
        bundle=h3_loop.export(self.rows(),'draft001')
        changed=self.rows()
        changed[1]['media_state'][0]['file']='different.png'
        self.assertNotEqual(bundle['fingerprint'],h3_loop.export(changed,'draft001')['fingerprint'])
        bundle['shots'][0]['prompt_text']='tampered'
        self.assertEqual(self.execute(h3_loop.PLAN_CODE,[json.dumps(bundle)],3)[0],'INVALID_PRODUCTION_BUNDLE')

    def test_empty_duplicate_and_mixed_recipes_rejected(self):
        for rows in ([], [self.rows()[0]]*2):
            with self.assertRaises(ValueError): h3_loop.export(rows,'draft001')
        rows=self.rows(); rows[1]['recipe']['steps']=30
        with self.assertRaises(ValueError): h3_loop.export(rows,'draft001')

    def test_silent_bundle_owns_dimensions_and_destination(self):
        rows=self.rows()
        for row in rows:
            row['recipe'].update(width=832,height=480,fps=24,delivery_audio='none')
            row['frames']=73
        bundle=h3_loop.export(rows,'silent001',output_subfolder='The_Message/silent001')
        self.assertEqual(bundle['version'],2)
        values=self.execute(h3_loop.PLAN_CODE,[json.dumps(bundle)],8)
        self.assertEqual(values[3:],[832,480,'none','The_Message/silent001',24])
        self.assertEqual(json.loads(values[0])['shots'][0]['length'],73)

    def test_destination_cannot_escape_output_directory(self):
        for path in ('../escape','/tmp/escape','safe/../../escape','safe\\escape'):
            with self.assertRaises(ValueError):
                h3_loop.export(self.rows(),'draft001',output_subfolder=path)
