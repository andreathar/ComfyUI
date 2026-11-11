"""Export compiled shots for the installed H3 Context Loop nodes."""
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def export(shots, run_name, output_subfolder=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_name):
        raise ValueError('run_name must be a plain identifier')
    if not shots or len({s['shot_id'] for s in shots}) != len(shots):
        raise ValueError('shots must be nonempty with unique IDs')
    if any(s['recipe'] != shots[0]['recipe'] for s in shots):
        raise ValueError('one loop uses one qualified recipe')
    output_subfolder = output_subfolder or f'The_Message/drafts/{run_name}'
    if not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', output_subfolder):
        raise ValueError('output_subfolder must be a contained relative directory')
    bundle = {'version': 2, 'run_name': run_name, 'shots': shots,
              'output_subfolder': output_subfolder}
    bundle['fingerprint'] = hashlib.sha256(canonical(bundle).encode()).hexdigest()
    return bundle


_READ = '''import json
import hashlib
bundle = json.loads(inputs[0])
expected = bundle.pop('fingerprint')
actual = hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
if expected != actual or bundle['version'] != 2 or not bundle['shots']:
    raise ValueError('Changed or invalid production bundle; re-export it')
'''

# Dynamic Script catches exceptions; nonempty sentinels make downstream JSON fail.
PLAN_CODE = '''outputs[:] = ['INVALID_PRODUCTION_BUNDLE', '', 'INVALID', 0, 0, 'INVALID', 'INVALID', 0]
''' + _READ + '''shots = bundle['shots']
plan = {'prompt_prefix': '', 'shots': [
    {'id': s['shot_id'], 'prompt': s['prompt_text'], 'length': s['frames'],
     'seed': s['seed'], 'steps': s['recipe']['steps']} for s in shots]}
recipe = shots[0]['recipe']
outputs[:] = [json.dumps(plan, ensure_ascii=False), expected, bundle['run_name'],
              recipe['width'], recipe['height'], recipe.get('delivery_audio', 'plan'),
              bundle['output_subfolder'], recipe.get('fps', 24)]
'''

SELECT_CODE = '''outputs[:] = ['INVALID_SHOT_SELECTION', 'INVALID_SHOT_SELECTION']
''' + _READ + '''index = inputs[1]
if not isinstance(index, int) or not 1 <= index <= len(bundle['shots']):
    raise ValueError('Scene index outside compiled production')
shot = bundle['shots'][index - 1]
outputs[:] = [json.dumps(shot['stack_state'], ensure_ascii=False),
              json.dumps(shot['media_state'], ensure_ascii=False)]
'''
