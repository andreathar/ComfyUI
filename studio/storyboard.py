"""Storyboard preparation and editorial timing over the canonical production document."""

import copy
from decimal import Decimal, ROUND_HALF_UP

from . import production_validate


def validate(document):
    problems = production_validate.check(document)
    if problems:
        raise ValueError('\n'.join(problems))


def upgrade(document):
    """Return a v2 proposal without modifying or renumbering the supplied project."""
    validate(document)
    result = copy.deepcopy(document)
    if result['schema_version'] == 1:
        result.update(schema_version=2, editorial={'version': 1, 'gap_before_frames': {}})
    return result


def legacy(document):
    """Project to v1 only when no IDs or editorial meaning must be discarded."""
    validate(document)
    result = copy.deepcopy(document)
    if result['schema_version'] == 2:
        if any(result['editorial']['gap_before_frames'].values()):
            raise ValueError('The legacy format cannot preserve editorial gaps')
        del result['editorial']
        result['schema_version'] = 1
        if production_validate.check(result):
            raise ValueError('The legacy format cannot preserve these stable IDs')
    return result


def empty(document):
    validate(document)
    return {'version': 1, 'shots': {
        shot['id']: {endpoint: {'description': '', 'candidates': []} for endpoint in ('start', 'end')}
        for shot in document['shots']}}


def targets(document, stored=None):
    result = copy.deepcopy(stored) if stored is not None else {'version': 1, 'shots': {}}
    if not isinstance(result, dict) or set(result) != {'version', 'shots'} or result['version'] != 1 or not isinstance(result['shots'], dict):
        raise ValueError('Unsupported storyboard targets')
    for shot_id, pair in result['shots'].items():
        if not isinstance(shot_id, str) or not isinstance(pair, dict) or set(pair) != {'start', 'end'}:
            raise ValueError('Invalid storyboard target')
        for target in pair.values():
            if (not isinstance(target, dict) or set(target) != {'description', 'candidates'}
                    or not isinstance(target['description'], str) or not isinstance(target['candidates'], list)):
                raise ValueError('Invalid storyboard endpoint')
    for shot_id, pair in empty(document)['shots'].items():
        result['shots'].setdefault(shot_id, pair)
    return result


def validate_target_edit(document, previous, updated):
    old = targets(document, previous)
    new = targets(document, updated)
    if new != updated or not set(old['shots']).issubset(new['shots']):
        raise ValueError('Keep existing storyboard targets')
    current = {shot['id'] for shot in document['shots']}
    if any(shot_id not in current and shot_id not in old['shots'] for shot_id in new['shots']):
        raise ValueError('Storyboard target does not belong to this project')
    for shot_id, pair in old['shots'].items():
        if shot_id not in current and new['shots'][shot_id] != pair:
            raise ValueError('Archived shot targets cannot be edited')
        for endpoint in ('start', 'end'):
            if pair[endpoint]['candidates'] != new['shots'][shot_id][endpoint]['candidates']:
                raise ValueError('Candidate changes require a separate review')
    return new


def timeline(document):
    validate(document)
    fps = document['project']['fps']
    gaps = document.get('editorial', {}).get('gap_before_frames', {})
    rows = []
    end = 0
    for shot in document['shots']:
        frames = int((Decimal(str(shot['duration_s'])) * fps).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        gap = gaps.get(shot['id'], 0)
        start = end + gap
        end = start + frames
        first, last = shot.get('start_frame', ''), shot.get('end_frame', '')
        rows.append({'shot_id': shot['id'], 'scene_id': shot['scene'], 'start': start, 'end': end,
                     'duration_frames': frames, 'gap_before_frames': gap, 'fps': fps,
                     'requested_seconds': shot['duration_s'], 'planned_seconds': frames / fps,
                     'start_image': first, 'end_image': last,
                     'review_status': 'needs_review' if first and last else 'missing_frames'})
    return rows
