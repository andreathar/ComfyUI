import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3_recipe as h3
import production_validate as pv
import h3_graph
import film


class RecipeTests(unittest.TestCase):
    def test_partial_lighting_override_inherits_the_scene_key(self):
        self.doc['shots'][0]['lighting'] = {'quality': 'soft'}
        out = self.compile()
        self.assertIn('Lighting: neon sign, side, soft.', out['builder_state']['ref']['styleLine'])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.doc = json.loads((pv.SPEC / 'example.production.json').read_text())
        self.doc['shots'][0].pop('target')
        self.doc['shots'][0]['duration_s'] = 2
        self.doc['characters'][0]['voice'] = 'DEMO-VOX-MAIN'
        self.doc['voices'] = [{'id': 'DEMO-VOX-MAIN', 'name': 'Main voice', 'description': 'Test voice reference'}]
        self.doc['shots'][0]['dialogue'] = [{'character': 'DEMO-CHR-MAIN', 'line': 'Not again.'}]
        self.assets = {}
        for key, kind, role, owner in [('actor', 'video', 'identity', 'DEMO-CHR-MAIN'), ('room', 'picture', 'location', 'DEMO-LOC-STREET'), ('voice', 'audio', 'voice', 'DEMO-VOX-MAIN')]:
            relative = f'input/{key}.png' if kind == 'picture' else f'models/refmods/{key}.safetensors'
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(key.encode())
            filename = f'{key}.png [input]' if kind == 'picture' else key
            self.assets[key] = dict(path=relative, sha256=h3.file_hash(path), approved=True, role=role, owner=owner, version=1, kind=kind, source='test fixture', selection={'file': filename, 'kind': kind})
        self.binding = {'assets': ['room', 'actor', 'voice'], 'audio_mode': 'generated_voiceover', 'seed': 0}
        self.recipe = copy.deepcopy(h3.DIAGNOSTIC)

    def compile(self):
        return h3.compile_shot(self.doc, self.doc['shots'][0]['id'], self.binding, self.assets, self.recipe, self.root)

    def silent(self):
        self.recipe={**h3.FOUR_VIEW_CANDIDATE, 'id':'h3-ref-silent-medium-v1',
                     'width':832,'height':480,'delivery_audio':'none'}
        self.doc['shots'][0]['dialogue']=[]
        self.doc['shots'][0]['duration_s']=3
        self.binding.update(audio_mode='silent',assets=['room','actor'])

    def test_medium_silent_recipe_and_frame_alignment(self):
        self.silent()
        out=self.compile()
        self.assertEqual(out['frames'],73)
        self.assertEqual(out['recipe']['delivery_audio'],'none')
        self.assertNotIn('<Audio',out['prompt_text'])

    def test_silent_recipe_cannot_use_legacy_audio_graph(self):
        self.silent()
        with self.assertRaisesRegex(ValueError, 'loop canvas'):
            h3_graph.compile_graph(self.compile(), 'test/video')

    def test_external_refmod_path_and_precedence(self):
        original = self.root / self.assets['actor']['path']
        external = self.root / 'external/refmods/actor.safetensors'
        external.parent.mkdir(parents=True)
        external.write_bytes(original.read_bytes())
        (self.root / 'extra_model_paths.yaml').write_text('external:\n  base_path: external\n  refmods: refmods\n  is_default: true\n')
        original.write_bytes(b'stale local copy')
        self.assertEqual(h3.asset_path(self.root, self.assets['actor']), external)
        self.compile()
        external.write_bytes(b'changed preferred copy')
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.compile()

    def test_empty_cast_has_environment_without_identity_or_voice(self):
        self.silent()
        self.doc['shots'][0]['characters'] = []
        self.binding['assets'] = ['room']
        out = self.compile()
        self.assertEqual(out['subjects']['environment'], '<Subject 1>')
        self.assertEqual(out['stack_state']['picks'], [])
        self.assertNotIn('<Video', out['prompt_text'])
        self.assertNotIn('<Audio', out['prompt_text'])

    def test_picture_reordering_updates_labels_and_prompt(self):
        path = self.root / 'input/wardrobe.png'
        path.write_bytes(b'clothes')
        self.assets['clothes'] = dict(path='input/wardrobe.png', sha256=h3.file_hash(path), approved=True,
            role='wardrobe', owner='DEMO-CHR-MAIN', wardrobe_id='W1', kind='picture',
            selection={'file': 'wardrobe.png [input]', 'kind': 'picture'})
        self.binding['assets'].insert(0, 'clothes')
        out = self.compile()
        self.assertEqual(out['labels']['room'], '<Picture 2>')
        self.assertIn('primary camera layout from <Picture 2>', out['prompt_text'])
        self.assertIn('as shown in <Picture 1>', out['prompt_text'])

    def test_silent_contract_rejects_voice_and_unused_identity(self):
        self.silent()
        self.binding['assets'].append('voice')
        with self.assertRaisesRegex(ValueError,'silent.*voice'):
            self.compile()
        self.binding['assets'].remove('voice')
        self.doc['shots'][0]['characters']=[]
        with self.assertRaisesRegex(ValueError,'identity.*cast'):
            self.compile()

    def test_prop_picture_is_bound_to_declared_shot_prop(self):
        self.silent()
        prop_id='DEMO-PRP-NOTE'
        self.doc['props']=[{'id':prop_id,'name':'Note','description':'Folded cream paper'}]
        self.doc['shots'][0]['props']=[prop_id]
        path=self.root/'input/note.png';path.write_bytes(b'note')
        self.assets['note']=dict(path='input/note.png',sha256=h3.file_hash(path),approved=True,
            role='prop',owner=prop_id,kind='picture',selection={'file':'note.png [input]','kind':'picture'})
        self.binding['shot_controls']={'props':[prop_id]}
        self.binding['assets'].append('note')
        out=self.compile()
        self.assertIn('prop reference <Picture 2>',out['prompt_text'])
        self.assets['note']['owner']='WRONG'
        with self.assertRaisesRegex(ValueError,'prop'):
            self.compile()

    def test_compilation_is_deterministic_and_editor_matches_prompt(self):
        out = self.compile()
        self.assertEqual(out, self.compile())
        self.assertEqual(out['frames'], 56)
        self.assertEqual(out['labels'], {'room': '<Picture 1>', 'actor': '<Video 1>', 'voice': '<Audio 1>'})
        self.assertEqual(out['prompt_text'], h3.render_prompt(out['builder_state']))
        self.assertIn('<d>[en] Not again.</d>', out['prompt_text'])

    def test_changed_asset_blocks(self):
        (self.root / self.assets['actor']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.compile()

    def test_environment_is_defined_and_used_as_a_subject(self):
        out = self.compile()
        ref = out['builder_state']['ref']
        environment = out['subjects']['environment']
        definition = next(d['text'] for d in ref['subjectDefs'] if d['text'].startswith(environment))
        self.assertIn('<Picture 1>', definition)
        self.assertIn(self.doc['locations'][0]['description'], definition)
        self.assertIn(environment, ref['detail'])
        self.assertIn(environment, ref['summaryText'])
        markers = {'fully_preserved', 'partially_preserved', 'attribute_transfer', 'weak_reference'}
        self.assertTrue(all(r['marker'] in markers for r in ref['retention'] if not r['label'].startswith('<Audio')))
        self.assertIn('[reference generation + audio reference]', out['prompt_text'])

    def test_named_subjects_and_retention_context_survive_editor_serialization(self):
        out = self.compile()
        ref = out['builder_state']['ref']
        name = self.doc['characters'][0]['name']
        self.assertIn(f'Their name is {name}.', out['prompt_text'])
        self.assertIn('<Subject 1> (appears in [Shot 1]): partially_preserved', out['prompt_text'])
        self.assertIn('<Subject 1> (S1)', ref['detail'])
        self.assertIn(f"It is {name}'s voice.", out['prompt_text'])
        self.assertTrue(all(line == line.rstrip() for line in out['prompt_text'].splitlines()))

    def test_cut_time_warning_uses_actual_render_duration_without_changing_text(self):
        out = self.compile()
        state = out['builder_state']
        state['ref']['detail'] += '\n[Shot 2] At 00:09.000, Zoom in.\n[Shot 3] At 00:17.000, Zoom out.'
        original = copy.deepcopy(state)
        warnings = h3.prompt_timing_warnings(state, out['duration_actual_s'])
        self.assertEqual(len(warnings), 2)
        self.assertIn('Shot 2', warnings[0])
        self.assertIn('Shot 3', warnings[1])
        self.assertEqual(h3.prompt_timing_warnings(state, 18), [])
        self.assertEqual(state, original)

    def test_reusable_shot_controls_drive_prompt_and_keep_source_unchanged(self):
        original = copy.deepcopy(self.doc)
        self.binding['shot_controls'] = {'framing': 'environment_reaction',
            'must_show': ['espresso counter', 'round table'], 'gaze_target': 'the counter, off camera',
            'expression': 'neutral, lips relaxed and closed', 'screen_position': 'left third'}
        out = self.compile()
        self.assertEqual(out['shot']['lens'], '35mm')
        self.assertEqual(out['shot']['shot_size'], 'medium-wide')
        self.assertIn('Keep visible in the same frame: espresso counter; round table.', out['prompt_text'])
        self.assertIn('Gaze target: the counter, off camera.', out['prompt_text'])
        self.assertEqual(self.doc, original)
        self.assertEqual(out['prompt_text'], h3.render_prompt(out['builder_state']))

    def test_unknown_shot_control_is_not_silently_ignored(self):
        self.binding['shot_controls'] = {'framng': 'environment_reaction'}
        with self.assertRaisesRegex(ValueError, 'shot control'):
            self.compile()

    def test_setting_reference_does_not_override_requested_camera(self):
        self.silent()
        self.binding['shot_controls'] = {'reference_layout': 'setting'}
        self.doc['shots'][0].update(shot_size='close-up', angle='overhead', lens='50mm',
            camera_move={'type': 'dolly-in', 'speed': 'slow'})
        self.doc['style_bible']['camera_rules'] = ['One continuous shot.']
        out = self.compile()
        self.assertIn('close-up shot, overhead, 50mm lens', out['prompt_text'])
        self.assertIn('Camera: slow dolly-in', out['prompt_text'])
        self.assertNotIn('primary camera layout from', out['prompt_text'])
        self.assertNotIn('use the primary picture for camera layout', out['prompt_text'])
        self.assertIn('setting appearance only', out['prompt_text'])
        self.assertIn('camera instructions below', out['prompt_text'])

    def test_invalid_reference_layout_is_rejected(self):
        self.binding['shot_controls'] = {'reference_layout': 'seting'}
        with self.assertRaisesRegex(ValueError, 'reference layout'):
            self.compile()

    def test_setting_reference_preserves_authored_content_instructions(self):
        self.silent()
        self.binding['shot_controls'] = {'reference_layout': 'setting'}
        self.assets['room']['instruction'] = 'Preserve the angular folded-paper outline and its visible flap.'
        self.assertIn(self.assets['room']['instruction'], self.compile()['prompt_text'])

    def test_first_frame_layout_declares_picture_anchor_and_keeps_camera_motion(self):
        self.silent()
        self.binding['shot_controls'] = {'reference_layout': 'first_frame'}
        self.doc['shots'][0]['camera_move'] = {'type':'dolly-in','speed':'slow'}
        self.doc['style_bible']['camera_rules'] = ['One continuous shot.']
        out = self.compile()
        defs = out['builder_state']['ref']['subjectDefs']
        self.assertTrue(any(d['text'].startswith('<Picture 1>') and 'first frame of [Shot 1]' in d['text'] for d in defs))
        self.assertIn('keyframe completion', out['builder_state']['ref']['summaryTypes'])
        self.assertIn('Camera: slow dolly-in', out['prompt_text'])
        self.assertIn('Opening composition from <Picture 1>', out['prompt_text'])

    def test_wardrobe_reference_belongs_to_character_not_a_frame_anchor(self):
        self.silent()
        path = self.root / 'input/wardrobe.png'
        path.write_bytes(b'gray shirt')
        self.assets['clothes'] = dict(path='input/wardrobe.png', sha256=h3.file_hash(path), approved=True,
            role='wardrobe', owner='DEMO-CHR-MAIN', wardrobe_id='W1', kind='picture',
            instruction='Preserve the embroidered blue cuff; ignore cropped framing.',
            selection={'file':'wardrobe.png [input]', 'kind':'picture'})
        self.binding['assets'].insert(0, 'clothes')
        out = self.compile()
        defs = out['builder_state']['ref']['subjectDefs']
        self.assertFalse(any(d['text'].startswith('<Picture 1>') for d in defs))
        person = next(d['text'] for d in defs if d['text'].startswith('<Subject 1>'))
        self.assertIn('<Picture 1>', person)
        self.assertIn('Preserve the embroidered blue cuff; ignore cropped framing.', person)
        self.assertNotIn('DEMO-CHR-MAIN', out['prompt_text'])
        identity = next(r for r in out['builder_state']['ref']['retention'] if r['label']=='<Subject 1>')
        self.assertIn('Facial identity only', identity['note'])
        self.assertIn('wardrobe', identity['note'])

    def test_prop_reference_becomes_reusable_subject_not_a_frame_anchor(self):
        self.silent()
        prop_id = 'DEMO-PRP-NOTE'
        self.doc['props'] = [{'id':prop_id,'name':'Envelope','description':'One white angular envelope'}]
        self.doc['shots'][0]['props'] = [prop_id]
        path = self.root / 'input/note.png'
        path.write_bytes(b'envelope')
        self.assets['note'] = dict(path='input/note.png',sha256=h3.file_hash(path),approved=True,
            role='prop',owner=prop_id,kind='picture',selection={'file':'note.png [input]','kind':'picture'})
        self.binding['assets'].append('note')
        out = self.compile()
        defs = out['builder_state']['ref']['subjectDefs']
        self.assertFalse(any(d['text'].startswith('<Picture 2>') for d in defs))
        self.assertIn('One white angular envelope', out['prompt_text'])
        self.assertIn('<Subject 3>', out['prompt_text'])
        self.assertNotIn('DEMO-PRP-NOTE', out['prompt_text'])

    def test_project_selection_uses_named_inputs_and_rejects_unknown_shot(self):
        film.write_json(self.root / 'selected-script.json', self.doc)
        film.write_json(self.root / 'assets.json', self.assets)
        shot_id = self.doc['shots'][0]['id']
        film.write_json(self.root / 'selected-bindings.json', {shot_id: self.binding})
        film.write_json(self.root / 'selected-recipe.json', self.recipe)
        selected = film.compile_project(self.root, self.root, 'selected-script.json',
                                        'selected-bindings.json', 'selected-recipe.json', [shot_id])
        self.assertEqual([x['shot_id'] for x in selected], [shot_id])
        with self.assertRaisesRegex(ValueError, 'unknown shot selection'):
            film.compile_project(self.root, self.root, 'selected-script.json',
                                 'selected-bindings.json', 'selected-recipe.json', ['missing'])

    def test_ambience_bundle_keeps_identity_and_primary_angle_separate(self):
        path = self.root / 'models/refmods/cafe.safetensors'
        path.write_bytes(b'cafe')
        self.assets['cafe'] = dict(path='models/refmods/cafe.safetensors', sha256=h3.file_hash(path), approved=True,
                                  role='ambience', owner='DEMO-LOC-STREET', kind='video',
                                  instruction='Use the room design, not the camera angle.', selection={'file': 'cafe', 'kind': 'video'})
        self.binding['assets'].append('cafe')
        out = self.compile()
        self.assertEqual(out['labels']['actor'], '<Video 1>')
        self.assertEqual(out['labels']['cafe'], '<Video 2>')
        env = out['subjects']['environment']
        definition = next(d['text'] for d in out['builder_state']['ref']['subjectDefs'] if d['text'].startswith(env))
        self.assertIn('<Picture 1>', definition)
        self.assertIn('<Video 2>', definition)
        self.assertIn('Use the room design, not the camera angle.', out['prompt_text'])
        self.assertNotIn('<Video 2>: reference', out['prompt_text'])
        self.assertEqual(len(out['media_state']), 1)
        self.assertEqual(out['stack_state']['picks'][-1]['visual']['w'], 1)
        self.assets['cafe']['owner'] = 'OTHER-LOCATION'
        with self.assertRaisesRegex(ValueError, 'ambience.*location'):
            self.compile()

    def test_background_bundle_is_a_visual_environment_subject(self):
        path = self.root / 'models/refmods/cafe.safetensors'
        path.write_bytes(b'cafe')
        self.assets['cafe'] = dict(path='models/refmods/cafe.safetensors', sha256=h3.file_hash(path), approved=True,
                                  role='background', owner='DEMO-LOC-STREET', kind='video',
                                  instruction='Preserve the black window frames.', selection={'file': 'cafe', 'kind': 'video'})
        self.binding['assets'].append('cafe')
        out = self.compile()
        environment = out['subjects']['environment']
        definition = next(d['text'] for d in out['builder_state']['ref']['subjectDefs'] if d['text'].startswith(environment))
        self.assertIn('<Video 2>', definition)
        self.assertIn('Preserve the black window frames.', out['prompt_text'])
        self.assertEqual(out['stack_state']['picks'][-1]['visual']['file'], 'cafe')
        self.assets['cafe']['owner'] = 'OTHER-LOCATION'
        with self.assertRaisesRegex(ValueError, 'background.*location'):
            self.compile()

    def test_unapproved_asset_blocks(self):
        self.assets['voice']['approved'] = False
        with self.assertRaisesRegex(ValueError, 'approved'):
            self.compile()

    def test_missing_speaker_binding_blocks(self):
        self.binding['assets'].remove('voice')
        with self.assertRaisesRegex(ValueError, 'voice'):
            self.compile()

    def test_asset_role_cannot_bind_wrong_character(self):
        self.assets['actor']['owner'] = 'DEMO-CHR-OTHER'
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.compile()

    def test_resize_and_script_change_fingerprint(self):
        first = self.compile()['fingerprint']
        self.assets['room']['selection']['resize'] = 256
        self.assertNotEqual(first, self.compile()['fingerprint'])
        second = self.compile()['fingerprint']
        self.doc['project']['source_text'] += ' New ending.'
        self.assertNotEqual(second, self.compile()['fingerprint'])

    def test_unknown_recipe_and_paid_target_block(self):
        self.doc['shots'][0]['target'] = 'kling-v4-omni'
        with self.assertRaisesRegex(ValueError, 'target'):
            self.compile()

    def test_long_dialogue_warns_without_truncating(self):
        line = ' '.join(['word'] * 30)
        self.doc['shots'][0]['dialogue'][0]['line'] = line
        out = self.compile()
        self.assertTrue(out['warnings'])
        self.assertIn(line, out['prompt_text'])

    def test_selection_must_reference_the_hashed_asset(self):
        self.assets['actor']['selection']['file'] = 'different-person'
        with self.assertRaisesRegex(ValueError, 'selection'):
            self.compile()

    def test_four_view_candidate_reaches_canvas_and_rejects_stale_encoder(self):
        baseline = self.compile()
        self.recipe.update(id='h3-ref-four-view-candidate-v1', stack_pictures='up to N', stack_pictures_n=4)
        out = self.compile()
        self.assertNotEqual(out['fingerprint'], baseline['fingerprint'])
        self.assertEqual(out['stack_state'], baseline['stack_state'])
        self.assertEqual(out['prompt_text'], baseline['prompt_text'])
        self.assertTrue(any('candidate' in warning for warning in out['warnings']))
        take = film.prepare(self.root / 'takes', out, 'tk004')
        edits = film.read_json(take / 'panel-edits.json')
        encoder_edits = {e['widget']: e['value'] for e in edits if e['node_id'] == 9}
        self.assertEqual(encoder_edits, {'stack_pictures': 'up to N', 'stack_pictures_n': 4})
        graph = h3_graph.compile_graph(out, 'test/video')
        self.assertEqual(graph['9']['inputs']['stack_pictures'], 'up to N')
        self.assertEqual(graph['9']['inputs']['stack_pictures_n'], 4)
        graph['9']['inputs']['stack_pictures'] = 'every 4th'
        with self.assertRaisesRegex(ValueError, 'nodes: 9'):
            h3_graph.verify(graph, out, 'test/video')

    def test_candidate_does_not_allow_untracked_recipe_changes(self):
        self.recipe.update(id='h3-ref-four-view-candidate-v1', stack_pictures='up to N', stack_pictures_n=4, steps=30)
        with self.assertRaisesRegex(ValueError, 'recipe'):
            self.compile()

    def test_submission_only_null_editor_buttons_do_not_break_receipt(self):
        out = self.compile()
        graph = h3_graph.compile_graph(out, 'test/video')
        graph['8']['inputs'].update({'Edit prompt…': None, '+ RefMods': None, '+ Media loader': None})
        graph['21']['inputs'].update({'Open loader…': None, '+ Native-output splitter': None})
        h3_graph.verify(graph, out, 'test/video')
        graph['8']['inputs']['Edit prompt…'] = 'unexpected value'
        with self.assertRaisesRegex(ValueError, 'nodes: 8'):
            h3_graph.verify(graph, out, 'test/video')
        graph['8']['inputs']['Edit prompt…'] = None
        graph['8']['inputs']['unknown_control'] = None
        with self.assertRaisesRegex(ValueError, 'nodes: 8'):
            h3_graph.verify(graph, out, 'test/video')

    def test_panel_parsed_names_preserve_receipt_but_content_changes_do_not(self):
        out = self.compile()
        graph = h3_graph.compile_graph(out, 'test/video')
        state = copy.deepcopy(out['builder_state'])
        lines = out['prompt_text'].split('\n\n', 1)[0].splitlines()[1:]
        state['ref']['subjectDefs'] = [{'text': line} for line in lines]
        state['off'] = {'subject_definitions': False, 'retention_analysis': False}
        graph['8']['inputs']['builder_state'] = json.dumps(state)
        h3_graph.verify(graph, out, 'test/video')
        state['ref']['detail'] += ' Different action.'
        graph['8']['inputs']['builder_state'] = json.dumps(state)
        with self.assertRaisesRegex(ValueError, 'nodes: 8'):
            h3_graph.verify(graph, out, 'test/video')


if __name__ == '__main__':
    unittest.main()
