"""Expand a compact single-scene outline into the existing Studio schema."""

import re

if __package__:
    from . import production_validate as pv
else:
    import production_validate as pv


SYSTEM = '''Draft one short, silent scene of one to four shots from the user's story. Return one compact JSON object, no prose.
Use this shape:
{"place":{"name":"...","kind":"EXT","time":"dusk","description":"..."},"cast":[{"name":"...","appearance":"...","wardrobe":"..."}],"props":[{"name":"...","description":"..."}],"shots":[{"excerpt":"verbatim short part of story","action":"one visible action","cast":[0],"props":[0],"size":"wide"}]}
Use zero-based indexes into cast and props; use [] when none. Keep descriptions short and factual.
Place kind: INT, EXT, INT/EXT. Time: dawn, day, golden-hour, dusk, night.
Shot size: extreme-wide, wide, full, medium-wide, medium, medium-close, close-up, extreme-close-up.
Optional shot fields: move (static, pan, tilt, dolly-in, dolly-out, track, handheld, crane, orbit, zoom, whip-pan), seconds, lens. Omit them unless requested; Studio supplies defaults. Optional place fields: light (short key-light description), quality (soft, hard, mixed).
Use a different verbatim source excerpt for each shot, in story order. Do not echo the whole story or invent characters, actions, appearance, props, paths or IDs. A supplied brief appearance is enough. Keep only the shots requested, or suggest the smallest useful coverage.
If the story needs multiple scenes, dialogue, a wardrobe change, or lacks essential scene facts, return only {"questions":[{"about":"...","ask":"..."}]} rather than flattening it or silently removing content.'''


def fields(value, label, required, optional=()):
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be an object')
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        raise ValueError(f'{label}: missing {sorted(missing)}, unexpected {sorted(extra)}')
    return value


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be nonempty text')
    return value


def rows(value, label, maximum):
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f'{label} must be a list of at most {maximum}')
    return value


def selected(indexes, bank, label):
    indexes = rows(indexes, label, len(bank))
    if any(type(i) is not int or not 0 <= i < len(bank) for i in indexes) or len(set(indexes)) != len(indexes):
        raise ValueError(f'{label} must contain distinct in-range indexes')
    return [bank[i]['id'] for i in indexes]


def expand(outline, source, code, title):
    if not re.fullmatch(r'[A-Z0-9]{2,8}', code):
        raise ValueError('Project code must be 2–8 uppercase letters or digits')
    text(title, 'Project title')
    if isinstance(outline, dict) and 'questions' in outline:
        questions = rows(fields(outline, 'Response', ('questions',))['questions'], 'questions', 4)
        if not questions:
            raise ValueError('Questions list is empty')
        for question in questions:
            for key, value in fields(question, 'Question', ('about', 'ask')).items():
                text(value, key)
        return {'questions': questions}
    fields(outline, 'Outline', ('place', 'cast', 'props', 'shots'))
    place = fields(outline['place'], 'Place', ('name', 'kind', 'time', 'description'), ('light', 'quality'))
    location = {'id': f'{code}-LOC-01', 'name': text(place['name'], 'Place name'),
                'kind': place['kind'], 'description': text(place['description'], 'Place description')}
    cast, props, shots = [], [], []
    for number, item in enumerate(rows(outline['cast'], 'Cast', 8), 1):
        row = fields(item, 'Character', ('name', 'appearance', 'wardrobe'))
        cast.append({'id': f'{code}-CHR-{number:02}', 'name': text(row['name'], 'Character name'),
                     'appearance': text(row['appearance'], 'Appearance'),
                     'persona': dict(summary='Unspecified', demeanor='Unspecified', speech='Unspecified'),
                     'wardrobe': [{'id': 'W1', 'description': text(row['wardrobe'], 'Wardrobe')}]})
    for number, item in enumerate(rows(outline['props'], 'Props', 8), 1):
        row = fields(item, 'Prop', ('name', 'description'))
        props.append({'id': f'{code}-PRP-{number:02}', 'name': text(row['name'], 'Prop name'),
                      'description': text(row['description'], 'Prop description')})
    scene_id = f'{code}_S001'
    end = 0
    for number, item in enumerate(rows(outline['shots'], 'Shots', 4), 1):
        row = fields(item, f'Shot {number}', ('excerpt', 'action', 'cast', 'props', 'size'), ('move', 'seconds', 'lens'))
        excerpt = text(row['excerpt'], 'Shot excerpt')
        start = source.find(excerpt, end)
        if start < 0:
            raise ValueError(f'Shot {number}: excerpt must occur verbatim in source after the previous shot')
        end = start + len(excerpt)
        people = selected(row['cast'], cast, 'Shot cast')
        objects = selected(row['props'], props, 'Shot props')
        size = row['size']
        purpose = 'establishing' if size in ('wide', 'extreme-wide') else 'close-up' if size in ('close-up', 'extreme-close-up') else 'medium'
        subject = ', '.join(person['name'] for person in cast if person['id'] in people) or location['name']
        shots.append(dict(id=f'{scene_id}_SH{number:02}', scene=scene_id, purpose=purpose, shot_size=size,
                          angle='eye-level', camera_move={'type': row.get('move', 'static')}, lens=row.get('lens', '35mm'),
                          subject=subject, action=text(row['action'], 'Shot action'), characters=people, props=objects,
                          location=location['id'], duration_s=row.get('seconds', 3), script_ref={'start': start, 'end': end}))
    if not shots:
        raise ValueError('At least one shot is required')
    people = list(dict.fromkeys(i for shot in shots for i in shot['characters']))
    objects = list(dict.fromkeys(i for shot in shots for i in shot['props']))
    lighting = {'key': place.get('light', 'Unspecified'), 'quality': place.get('quality', 'soft'), 'time_of_day': place['time']}
    doc = dict(schema_version=1, project=dict(code=code, title=title, source_text=source, aspect='16:9', fps=24),
               style_bible=dict(look='Neutral draft', palette=['neutral'], lens_default='35mm', lighting_default=lighting),
               characters=cast, locations=[location], props=props,
               scenes=[dict(id=scene_id, number=1, slug=location['name'], location=location['id'], time=place['time'],
                            summary=' '.join(shot['action'] for shot in shots), characters=people, props=objects,
                            wardrobe={person: 'W1' for person in people}, script_ref={'start': 0, 'end': len(source)})], shots=shots)
    problems = pv.check(doc)
    return {'problems': problems} if problems else {'document': doc}
