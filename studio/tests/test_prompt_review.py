import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prompt_review import review_prompt


def fixture():
    state = {'mode': 'REF', 'duration': 3, 'off': {}, 'ref': {
        'subjectDefs': [{'text': '<Subject 1> is the person in <Picture 1>.'}],
        'summaryTypes': ['reference generation'], 'summaryText': '<Subject 1> sits.',
        'retention': [{'label': '<Subject 1>', 'marker': 'fully_preserved', 'note': 'Keep appearance.'}],
        'styleLine': 'Natural daylight.', 'detail': '[Shot 1] <Subject 1> sits. The camera holds a static shot.',
        'soundscape': 'No speech.', 'music': 'N/A'}}
    from h3_recipe import render_prompt
    return render_prompt(state), state


class PromptReviewTests(unittest.TestCase):
    def review(self, text, state, **kw):
        from h3_recipe import render_prompt
        return review_prompt(text, state, expected_text=render_prompt(state), **kw)

    def test_review_identifies_the_exact_inputs_and_never_changes_them(self):
        text, state = fixture(); before = copy.deepcopy(state)
        result = self.review(text, state, reference_labels=['<Picture 1>'])
        self.assertEqual(result['state_parity'], 'matched')
        self.assertEqual(result['reference_coverage'], 'provided map')
        self.assertEqual(state, before)
        changed = self.review(text + '\nChanged', state)
        self.assertNotEqual(result['prompt_sha256'], changed['prompt_sha256'])
        self.assertNotEqual(result['review_sha256'], changed['review_sha256'])
        self.assertIn('state_text_mismatch', [f['code'] for f in changed['findings']])

    def test_silent_speaker_and_camera_conflict_are_advisory(self):
        text, state = fixture()
        state['ref']['detail'] += ' <Subject 1> (S1) sits. The camera pushes in slowly.'
        from h3_recipe import render_prompt
        result = self.review(render_prompt(state), state)
        codes = [f['code'] for f in result['findings']]
        self.assertIn('silent_speaker', codes)
        self.assertIn('camera_conflict', codes)
        self.assertFalse(result['blocks_generation'])

    def test_unknown_map_does_not_invent_missing_refmod_labels(self):
        text, state = fixture()
        self.assertNotIn('missing_reference', [f['code'] for f in self.review(text, state)['findings']])
        known = self.review(text, state, reference_labels=[])
        self.assertIn('missing_reference', [f['code'] for f in known['findings']])

    def test_profile_and_timing_mismatches_are_reported(self):
        text, state = fixture(); state['mode'] = 'I2VA'
        result = review_prompt(text + '\n[Shot 2] At 00:05.000, cut.', state, duration=3)
        codes = [f['code'] for f in result['findings']]
        self.assertIn('mode_mismatch', codes)
        self.assertIn('shot_timing', codes)

    def test_unreadable_editor_state_keeps_the_prompt_executable(self):
        text, _ = fixture()
        result = review_prompt(text, 'old state')
        self.assertFalse(result['blocks_generation'])
        self.assertEqual(result['state_parity'], 'unverified')
        self.assertIn('invalid_state', [f['code'] for f in result['findings']])

    def test_loader_overflow_and_disabled_media_are_not_claimed_as_references(self):
        from master_studio_package import package_review
        text, state = fixture()
        package = {'prompt_text': text, 'builder_state': state, 'stack_state': {'picks': []},
                   'media_state': [{'kind': 'picture'}] * 10, 'seed': 4}
        self.assertEqual(package_review(package, 'a' * 64)['reference_coverage'], 'unverified')
        package['media_state'] = [{'kind': 'picture', 'enabled': False}]
        result = package_review(package, 'a' * 64)
        self.assertEqual(result['reference_labels'], [])
        self.assertIn('missing_reference', [f['code'] for f in result['findings']])

    def test_composition_role_before_picture_label_is_reviewed(self):
        text, state = fixture()
        state['ref']['detail'] += ' Camera layout from <Picture 1>.'
        from h3_recipe import render_prompt
        result = review_prompt(render_prompt(state), state)
        self.assertIn('picture_role', [f['code'] for f in result['findings']])
