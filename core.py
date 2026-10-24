"""TCC Worship's portable service model; no third-party worship code copied."""
import base64
import copy
import json
import re
import uuid
from pathlib import Path

MAX_BACKUP = 45 * 1024 * 1024
KINDS = {'song', 'scripture', 'announcement', 'image', 'video', 'presentation'}

def uid():
    return uuid.uuid4().hex

def slides_from_text(text):
    """Blank lines delimit slides; [Verse 1] is an optional section label."""
    slides = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.strip().splitlines()
        label = ''
        if lines and re.fullmatch(r'\[.+\]', lines[0].strip()):
            label = lines.pop(0).strip()[1:-1]
        body = '\n'.join(lines).strip()
        if body:
            slides.append({'label': label, 'text': body})
    return slides

def item(title, kind, text='', **kwargs):
    return {'id': uid(), 'title': title, 'kind': kind,
            'slides': slides_from_text(text), 'language': '', 'tags': '',
            'credit': '', 'favourite': False, **kwargs}

def new_workspace():
    logo = item('Tabernacle Christian Centre', 'image', src=media_data(Path(__file__).with_name('assets').joinpath('tcc_logo.png').read_bytes(), 'image/png'))
    welcome = item('Welcome to TCC', 'announcement',
        '[Welcome]\nWelcome to TCC\nLet us worship together.\n\n[Gathering]\nPlease take your seats.\nOur service will begin shortly.')
    demo = item('TCC sample song — replace with your lyrics', 'song',
        '[Verse 1]\nTogether we gather in hope\nTogether we lift up our praise\n\n[Chorus]\nLet every heart sing with joy\nLet every voice give thanks',
        language='English', tags='Demo, Thanksgiving', credit='Original demonstration text for TCC Worship')
    return {'schema_version': 1, 'service_title': 'TCC Sunday Worship',
            'theme': {'background': '#101d35', 'accent': '#e8bc73', 'font_size': 54},
            'library': [logo, welcome, demo], 'service': [copy.deepcopy(logo), copy.deepcopy(welcome)]}

def validate_workspace(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('This is not a supported TCC Worship backup (version 1).')
    if not isinstance(data.get('service_title'), str) or len(data['service_title']) > 300:
        raise ValueError('Invalid service title.')
    theme = data.get('theme', {})
    for key in ('background', 'accent'):
        if not isinstance(theme.get(key), str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', theme[key]):
            raise ValueError('Theme colours must be six-digit hex colours.')
    if type(theme.get('font_size')) is not int or not 24 <= theme['font_size'] <= 90:
        raise ValueError('Font size must be between 24 and 90.')
    for name in ('library', 'service'):
        if not isinstance(data.get(name), list) or len(data[name]) > 1000:
            raise ValueError('Invalid library or service list.')
        ids = set()
        for obj in data[name]:
            if not isinstance(obj, dict) or obj.get('kind') not in KINDS:
                raise ValueError('Unsupported content type.')
            if not isinstance(obj.get('id'), str) or obj['id'] in ids:
                raise ValueError('Missing or duplicate item ID.')
            ids.add(obj['id'])
            if not isinstance(obj.get('title'), str) or not obj['title'].strip():
                raise ValueError('Every item needs a title.')
            for key in ('language', 'tags', 'credit'):
                if not isinstance(obj.get(key, ''), str):
                    raise ValueError('Invalid item metadata.')
            if not isinstance(obj.get('slides'), list) or len(obj['slides']) > 500:
                raise ValueError('Invalid slide list.')
            for slide in obj['slides']:
                if not isinstance(slide, dict) or not isinstance(slide.get('text', ''), str) or not isinstance(slide.get('label', ''), str):
                    raise ValueError('Invalid slide text.')
                if slide.get('src'):
                    validate_media(slide['src'], 'image')
            if obj['kind'] in ('image', 'video'):
                validate_media(obj.get('src', ''), obj['kind'])
            elif not obj['slides']:
                raise ValueError('Text and presentation items need at least one slide.')
    return copy.deepcopy(data)

def validate_media(src, kind):
    if not isinstance(src, str):
        raise ValueError('Invalid media.')
    prefix = r'data:image/(png|jpeg|webp|gif);base64,' if kind == 'image' else r'data:video/(mp4|webm);base64,'
    match = re.match(prefix, src)
    if not match:
        raise ValueError('Media must be embedded supported images or videos.')
    try:
        base64.b64decode(src[match.end():], validate=True)
    except Exception as exc:
        raise ValueError('Invalid media encoding.') from exc

def load_backup(raw):
    if len(raw) > MAX_BACKUP:
        raise ValueError('Backup exceeds 45 MB. Split large services.')
    try:
        return validate_workspace(json.loads(raw))
    except (TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid TCC Worship backup.') from exc

def backup_bytes(data):
    return json.dumps(validate_workspace(data), ensure_ascii=False, indent=2).encode('utf-8')

def duplicate(obj):
    result = copy.deepcopy(obj)
    result['id'] = uid()
    return result

def search_items(library, query='', language='All', favourites=False):
    words = query.casefold().split()
    return [x for x in library if (language == 'All' or x.get('language') == language)
            and (not favourites or x.get('favourite'))
            and all(w in ' '.join([x['title'], x.get('tags', ''),
                      *[s.get('text', '') for s in x['slides']]]).casefold() for w in words)]

def media_data(raw, mime):
    return 'data:' + mime + ';base64,' + base64.b64encode(raw).decode()

def export_html(data, bibles=None):
    validate_workspace(data)
    template = Path(__file__).with_name('presenter.html').read_text()
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    from bible import load_bible, validate_bible
    versions = bibles if bibles is not None else [load_bible()]
    for version in versions: validate_bible(version)
    bible_payload = json.dumps(versions, ensure_ascii=False).replace('<', '\\u003c')
    logo = media_data(Path(__file__).with_name('assets').joinpath('tcc_logo.png').read_bytes(), 'image/png')
    return template.replace('/*__TCC_BIBLES__*/', bible_payload).replace('/*__TCC_DATA__*/', payload).replace('__TCC_LOGO__', logo).encode('utf-8')
