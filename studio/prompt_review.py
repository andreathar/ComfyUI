"""Advisory review of resolved H3 prompt inputs; never rewrites or loads models."""

import hashlib
import json
import re

GUIDE = 'https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md'
RULES_VERSION = 'h3-prompt-review-v1'


def review_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def review_prompt(text, state, *, expected_text=None, expected_mode='REF', reference_labels=None, duration=None, package_revision=None, seed=None):
    findings = []
    def note(code, message):
        findings.append({'code': code, 'message': message})

    state_sha256 = review_digest(state)
    if not isinstance(state, dict):
        state, expected_text = {}, None
        note('invalid_state', 'Editor state is not an object; the committed prompt remains unchanged and state parity is unverified.')
    off = state.get('off') if isinstance(state.get('off'), dict) else {}
    mode = state.get('mode', 'REF')
    if mode != expected_mode:
        note('mode_mismatch', 'Builder mode differs from the configured workflow profile.')
    if expected_text is not None and text.strip() != expected_text.strip():
        note('state_text_mismatch', 'Saved prompt text differs from the supported state renderer; review the committed text and state together.')
    expected_sections = (['subject_definitions', 'summary', 'retention_analysis', 'detailed_description', 'overall_soundscape', 'non_diegetic_music']
                         if mode == 'REF' else ['integrated_multimodal_description', 'overall_soundscape', 'non_diegetic_music'])
    sections = re.findall(r'(?m)^([a-z_]+):', text)
    enabled = [name for name in expected_sections if not off.get(name)]
    if sections != enabled:
        note('section_structure', 'Prompt sections differ from the enabled sections for this mode.')
    cited = sorted(set(re.findall(r'<(?:Picture|Video|Audio) \d+>', text)))
    if reference_labels is None:
        note('reference_map_unverified', 'Final encoder reference labels are unavailable; no missing reference is inferred.')
    else:
        missing = sorted(set(cited) - set(reference_labels))
        if missing:
            note('missing_reference', 'Cited references absent from the provided map: ' + ', '.join(missing))
    if re.search(r'\(S\d+\)', text) and not re.search(r'<d>', text) and re.search(r'no (?:speech|dialogue)', text, re.I):
        note('silent_speaker', 'A silent prompt contains a vocal-source ID; remove it only after reviewing the intended audio.')
    body = text.split('detailed_description:', 1)[-1].split('overall_soundscape:', 1)[0] if mode == 'REF' else text
    if not re.search(r'\[Shot 1\]', body):
        note('shot_opening', 'The description has no [Shot 1] opening.')
    locked = re.search(r'(?:camera\s*:\s*static|locked tripod|camera holds a static shot)', body, re.I)
    moving = re.search(r'(?:camera (?:slowly )?(?:pushes|pulls|pans|trucks|arcs|tracks)|(?:push-in|pull-back|dolly|tracking) (?:movement|shot))', body, re.I)
    if locked and moving:
        note('camera_conflict', 'The shot contains both a locked camera instruction and a camera movement; check whether the change is intentional.')
    for minutes, seconds in re.findall(r'\[Shot \d+\]\s+At (\d+):(\d+(?:\.\d+)?)', body):
        if isinstance(duration, (int, float)) and int(minutes) * 60 + float(seconds) >= duration:
            note('shot_timing', 'A shot cut is at or beyond the requested duration.')
    if mode == 'REF':
        defs = text.split('subject_definitions:', 1)[-1].split('summary:', 1)[0]
        retention = text.split('retention_analysis:', 1)[-1].split('detailed_description:', 1)[0]
        for label in sorted(set(re.findall(r'<Subject \d+>', text))):
            if label not in defs or label not in retention:
                note('subject_role', label + ' needs a consistent definition and retention role.')
        for label in cited:
            anchor = any(label in sentence and re.search(r'camera layout|composition|first frame|keyframe', sentence, re.I)
                         for sentence in re.split(r'[.\n]', body))
            if label.startswith('<Picture') and anchor and label not in retention:
                note('picture_role', label + ' has a composition/frame role but no explicit retention entry.')
    result = {'rules_version': RULES_VERSION, 'guide': GUIDE, 'profile': 'h3-ref2va' if expected_mode == 'REF' else 'h3-base-' + expected_mode.lower(),
              'profile_basis': 'configured workflow profile; loaded model identity unverified',
              'prompt_sha256': hashlib.sha256(text.encode()).hexdigest(), 'state_sha256': state_sha256,
              'package_revision': package_revision, 'resolved_seed': seed, 'state_parity': 'unverified' if expected_text is None else 'matched' if text.strip() == expected_text.strip() else 'mismatch',
              'reference_coverage': 'unverified' if reference_labels is None else 'provided map',
              'reference_labels': reference_labels, 'cited_labels': cited, 'findings': findings[:64], 'blocks_generation': False}
    result['review_sha256'] = review_digest(result)
    return result
