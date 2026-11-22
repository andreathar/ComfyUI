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
