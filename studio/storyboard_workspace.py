"""Small, local project operations used by the storyboard creator workspace."""

import re

from . import production_bootstrap as bootstrap
from . import production_outline, production_store, storyboard


def selected(projects_root, slug):
    if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or len(slug) > 64:
        raise ValueError('Choose a valid project name')
    root = production_store.project_path(projects_root)
    return root / slug


def preview(source, title, slug, code, cast, location):
    """An explicit manual starting point, never a substitute for model story analysis."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError('Write your story first')
    paragraphs = [part.strip() for part in re.split(r'\n\s*\n', source) if part.strip()]
    if len(paragraphs) > 4:
        raise ValueError('The manual starting point supports up to four paragraphs; use the local planner for larger stories')
    if not isinstance(cast, list) or any(not isinstance(c, dict) or set(c) != {'name', 'wardrobe'} for c in cast):
        raise ValueError('Characters need a name and outfit')
    outline = {
        'place': {'name': location, 'kind': 'INT', 'time': 'day', 'description': 'Location details need review'},
        'cast': [{'name': c['name'], 'appearance': 'Identity reference needs review', 'wardrobe': c['wardrobe']} for c in cast],
        'props': [],
        'shots': [{'excerpt': paragraph, 'action': paragraph, 'cast': list(range(len(cast))), 'props': [], 'size': 'wide'}
                  for paragraph in paragraphs],
    }
    result = production_outline.expand(outline, source, code, title)
    if 'document' not in result:
        raise ValueError('\n'.join(result.get('problems', ['Review the story details'])))
    document = storyboard.upgrade(result['document'])
    return {'mode': 'story_paragraphs',
            'assumptions': ['Each paragraph is a draft shot in one scene; story interpretation has not run.',
                            'Interior, daytime, wide framing and three-second timing are editable starting choices.',
                            'Characters, outfits, props, geography and endpoint images need review.'],
            'proposal': bootstrap.preview(document, slug)}


def create(projects_root, proposal, approved_digest):
    bootstrap.create(projects_root, proposal, approved_digest)
    return open_project(projects_root, proposal['slug'])


def open_project(projects_root, slug):
    state = production_store.read_project(selected(projects_root, slug))
    return {**state, 'project': slug, 'timeline': storyboard.timeline(state['production']), 'render_ready': False}


def save(projects_root, slug, revision, document):
    state = production_store.commit(selected(projects_root, slug), revision, {'production': document}, 'Edit storyboard plan')
    return {**state, 'project': slug, 'timeline': storyboard.timeline(state['production']), 'render_ready': False}


def projects(projects_root):
    root = production_store.project_path(projects_root)
    result = {'projects': [], 'problems': []}
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_dir() or not (path / 'project.json').exists():
            continue
        try:
            state = open_project(root, path.name)
            project = state['production']['project']
            result['projects'].append({'slug': path.name, 'title': project['title'], 'code': project['code'],
                                       'shots': len(state['timeline'])})
        except (ValueError, KeyError, TypeError, OSError) as error:
            result['problems'].append({'slug': path.name, 'error': str(error)})
    return result
