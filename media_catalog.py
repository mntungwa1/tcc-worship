"""Categorised uploads with a private disk cache and portable service media."""
import copy
import csv
import hashlib
import io
import os
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image

CATEGORIES = ('Praise', 'Worship', 'Offering', 'Communion', 'Sunday School',
              'Prayer', 'Scripture', 'Welcome', 'Baptism', 'Easter and Christmas')
MIMES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
         '.webp': 'image/webp', '.gif': 'image/gif', '.mp4': 'video/mp4', '.webm': 'video/webm'}
MAX_FILE = 20 * 1024 * 1024
MAX_UPLOAD = 512 * 1024 * 1024
MAX_COLLECTION = 768 * 1024 * 1024
MAX_ENTRIES = 2000
REF = re.compile(r'tcc-media:([a-f0-9]{32})/([a-f0-9]{64}\.(?:png|jpg|webp|gif|mp4|webm))\Z')


def category_name(value):
    key = re.sub(r'[^a-z0-9]', '', str(value).casefold())
    aliases = {'sundayschool': 'Sunday School', 'kids': 'Sunday School',
               'children': 'Sunday School', 'easterchristmas': 'Easter and Christmas',
               'christmas': 'Easter and Christmas', 'easter': 'Easter and Christmas',
               'scripturereading': 'Scripture', 'bible': 'Scripture'}
    return next((name for name in CATEGORIES if re.sub(r'[^a-z0-9]', '', name.casefold()) == key), aliases.get(key))


def asset_category(asset):
    return category_name(asset.get('category')) or 'Welcome'


def folder_category(name):
    for part in reversed(PurePosixPath(name.replace('\\', '/')).parts[:-1]):
        found = category_name(part)
        if found:
            return found
    return None


def is_cached_source(src):
    return isinstance(src, str) and REF.fullmatch(src) is not None


def storage_root():
    root = Path(os.environ.get('TCC_MEDIA_DIR', str(Path(tempfile.gettempdir()) / 'tcc-worship-media')))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def source_path(src):
    match = REF.fullmatch(src) if isinstance(src, str) else None
    if not match:
        raise ValueError('Invalid stored media reference.')
    return storage_root() / match[1] / match[2]


def preview_source(src):
    if not is_cached_source(src):
        return src
    path = source_path(src)
    if not path.is_file():
        raise ValueError('Re-upload the original media files or ZIP to restore this file after a server restart.')
    return str(path)


def embed_source(src):
    if not is_cached_source(src):
        return src
    from core import media_data
    path = Path(preview_source(src))
    if path.stat().st_size > MAX_FILE:
        raise ValueError('Stored media exceeds the 20 MB per-file limit.')
    return media_data(path.read_bytes(), MIMES[path.suffix])


def portable_item(asset):
    result = copy.deepcopy(asset)
    if result.get('src'):
        result['src'] = embed_source(result['src'])
    for slide in result.get('slides', []):
        if slide.get('src'):
            slide['src'] = embed_source(slide['src'])
    return result


def portable_workspace(workspace):
    """Carry the prepared service and its media without embedding the entire collection."""
    result = copy.deepcopy(workspace)
    result['service'] = [portable_item(x) for x in result['service']]
    backdrop = result.get('theme', {}).get('background_media')
    if backdrop:
        backdrop['src'] = embed_source(backdrop['src'])
    # Keep text/presentation libraries and media actually selected for this service.
    # The full media collection remains in its separate, category-preserving ZIP.
    selected = {x.get('src') for x in workspace['service'] if x.get('src')}
    if backdrop:
        selected.add(workspace['theme']['background_media']['src'])
    result['library'] = [portable_item(x) for x in workspace['library']
                         if x['kind'] not in ('image', 'video') or x.get('src') in selected]
    result.pop('media_scope', None)
    return result


def _safe_member(info):
    name = info.filename.replace('\\', '/')
    path = PurePosixPath(name)
    if (path.is_absolute() or '..' in path.parts or '\x00' in name or
            re.match(r'^[A-Za-z]:', name) or stat.S_ISLNK(info.external_attr >> 16)):
        raise ValueError('The ZIP contains an unsafe path or symbolic link.')
    if info.flag_bits & 1:
        raise ValueError('Password-protected ZIP files are not supported.')
    return name


def _credits(archive):
    result = {}
    for info in archive.infolist():
        if PurePosixPath(info.filename).name.casefold() != 'credits.csv' or info.file_size > 2 * 1024 * 1024:
            continue
        try:
            text = archive.read(info).decode('utf-8-sig')
            for row in csv.DictReader(io.StringIO(text)):
                file = row.get('file', '').replace('\\', '/')
                if file:
                    result[file.casefold()] = row
        except (UnicodeDecodeError, csv.Error):
            continue
    return result


def _credit_row(credits, name):
    parts = PurePosixPath(name).parts
    for start in range(len(parts)):
        row = credits.get('/'.join(parts[start:]).casefold())
        if row:
            return row
    return {}


def _credit_text(row):
    if row.get('credit'):
        return str(row['credit'])[:16000]
    return '\n'.join(str(row[key]) for key in
                     ('author', 'license', 'license_url', 'source_page', 'modifications', 'attribution')
                     if row.get(key))[:16000]


def _check_media(raw, suffix):
    if not raw or len(raw) > MAX_FILE:
        raise ValueError('Each image or video must be non-empty and no larger than 20 MB.')
    if suffix in ('.mp4', '.webm'):
        valid = raw[4:8] == b'ftyp' if suffix == '.mp4' else raw[:4] == b'\x1aE\xdf\xa3'
        if not valid:
            raise ValueError('A video does not match its MP4/WebM extension.')
    else:
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 40_000_000:
                    raise ValueError('Images must contain no more than 40 million pixels.')
                expected = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.webp': 'WEBP', '.gif': 'GIF'}[suffix]
                if image.format != expected:
                    raise ValueError('An image does not match its extension.')
                image.verify()
        except (OSError, SyntaxError, Image.DecompressionBombError) as exc:
            raise ValueError('An uploaded image could not be read.') from exc


def import_uploads(workspace, uploads, kind, default_category='Welcome', use_folders=True):
    """Stream each archive entry to staging; publish metadata only after validation."""
    from core import item, validate_workspace, backup_bytes, MAX_BACKUP
    if kind not in ('image', 'video') or default_category not in CATEGORIES:
        raise ValueError('Choose an image/video library and one of the ten categories.')
    candidate = copy.deepcopy(workspace)
    scope = candidate.setdefault('media_scope', uuid.uuid4().hex)
    if not isinstance(scope, str) or not re.fullmatch('[a-f0-9]{32}', scope):
        raise ValueError('Invalid media collection identifier.')
    known = {}
    total = 0
    for obj in candidate['library']:
        if obj['kind'] in ('image', 'video'):
            src = obj.get('src', '')
            digest = obj.get('media_hash')
            if not digest and is_cached_source(src):
                digest = REF.fullmatch(src)[2].split('.')[0]
            if not digest and src.startswith('data:'):
                import base64
                digest = hashlib.sha256(base64.b64decode(src.split(',', 1)[1])).hexdigest()
            if digest:
                known[(obj['kind'], digest)] = obj
            total += obj.get('media_bytes', (len(src) * 3 // 4 if src.startswith('data:') else 0))
    target = storage_root() / scope
    stage = Path(tempfile.mkdtemp(prefix='tcc-import-', dir=storage_root()))
    added = restored = duplicates = ignored = 0
    writes = {}
    counts = {name: 0 for name in CATEGORIES}
    asset_ids = []

    def accept(name, raw, row=None, structured=False):
        nonlocal added, restored, duplicates, ignored, total
        suffix = PurePosixPath(name).suffix.casefold()
        if suffix not in MIMES or (suffix in ('.mp4', '.webm')) != (kind == 'video'):
            ignored += 1
            return
        _check_media(raw, suffix)
        digest = hashlib.sha256(raw).hexdigest()
        previous = known.get((kind, digest))
        if previous:
            if previous['id'] not in asset_ids:
                asset_ids.append(previous['id'])
            src = previous.get('src', '')
            if is_cached_source(src) and not source_path(src).is_file() and src not in writes:
                dest = source_path(src)
                staged = stage / (digest + suffix)
                staged.write_bytes(raw)
                writes[src] = (staged, dest)
                restored += 1
            else:
                duplicates += 1
            return
        total += len(raw)
        if total > MAX_COLLECTION:
            raise ValueError('This media collection would exceed 768 MB. Import a smaller collection.')
        if len(candidate['library']) >= 1000:
            raise ValueError('This workspace supports up to 1,000 library items.')
        row = row or {}
        category = (folder_category(name) or category_name(row.get('category'))) if structured and use_folders else None
        category = category or default_category
        suffix = '.jpg' if suffix == '.jpeg' else suffix
        src = f'tcc-media:{scope}/{digest}{suffix}'
        title = str(row.get('title') or PurePosixPath(name).stem).strip()[:500]
        if title.lower().endswith(tuple(MIMES)):
            title = title.rsplit('.', 1)[0]
        obj = item(title or 'Untitled media', kind, src=src, category=category,
                   credit=_credit_text(row), media_bytes=len(raw), media_hash=digest,
                   import_source=name[:1000])
        staged = stage / (digest + suffix)
        staged.write_bytes(raw)
        writes[src] = (staged, target / (digest + suffix))
        known[(kind, digest)] = obj
        candidate['library'].append(obj)
        asset_ids.append(obj['id'])
        counts[category] += 1
        added += 1

    try:
        expanded = 0
        for upload in uploads:
            upload.seek(0)
            size = getattr(upload, 'size', None)
            if size is None:
                upload.seek(0, 2)
                size = upload.tell()
                upload.seek(0)
            if size > MAX_UPLOAD:
                raise ValueError('Each uploaded ZIP or file must be under 512 MB.')
            name = str(upload.name)
            if Path(name).suffix.casefold() != '.zip':
                if size > MAX_FILE:
                    raise ValueError('Each loose image/video file must be under 20 MB.')
                expanded += size
                if expanded > MAX_COLLECTION:
                    raise ValueError('The upload expands beyond 768 MB.')
                accept(name, upload.read(MAX_FILE + 1))
                continue
            try:
                with zipfile.ZipFile(upload) as archive:
                    infos = archive.infolist()
                    if len(infos) > MAX_ENTRIES:
                        raise ValueError('The ZIP contains too many entries.')
                    for info in infos:
                        _safe_member(info)
                        if not info.is_dir():
                            expanded += info.file_size
                    if expanded > MAX_COLLECTION:
                        raise ValueError('The upload expands beyond 768 MB.')
                    credits = _credits(archive)
                    for info in infos:
                        if info.is_dir():
                            continue
                        name = _safe_member(info)
                        suffix = PurePosixPath(name).suffix.casefold()
                        if suffix not in MIMES or (suffix in ('.mp4', '.webm')) != (kind == 'video'):
                            ignored += 1
                            continue
                        if info.file_size > MAX_FILE:
                            raise ValueError(PurePosixPath(name).name + ' exceeds 20 MB.')
                        with archive.open(info) as member:
                            raw = member.read(MAX_FILE + 1)
                        accept(name, raw, _credit_row(credits, name), structured=True)
            except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError) as exc:
                raise ValueError('The ZIP could not be read. Use an unencrypted ZIP archive.') from exc
        validate_workspace(candidate)
        if len(backup_bytes(candidate)) > MAX_BACKUP:
            raise ValueError('The service and library metadata exceed the workspace limit.')
        for staged, dest in writes.values():
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.replace(staged, dest)
        workspace['library'] = candidate['library']
        workspace['media_scope'] = scope
        return {'added': added, 'restored': restored, 'duplicates': duplicates, 'ignored': ignored, 'categories': counts, 'asset_ids': asset_ids}
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def archive_library(workspace, kind):
    """Keep category folders and credits together for re-import after a restart."""
    import base64
    output = io.BytesIO()
    credits = []
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for obj in workspace['library']:
            if obj['kind'] != kind:
                continue
            src = obj['src']
            if is_cached_source(src):
                path = Path(preview_source(src))
                raw = path.read_bytes()
                suffix = path.suffix
            else:
                prefix, encoded = src.split(',', 1)
                raw = base64.b64decode(encoded)
                suffix = next(ext for ext, mime in MIMES.items() if mime in prefix)
            category = asset_category(obj)
            title = re.sub(r'[^\w .-]', '_', obj['title'])[:100].strip(' .') or 'Media'
            name = f'{category}/{obj["id"]}_{title}{suffix}'
            archive.writestr(name, raw)
            credits.append({'file': name, 'category': category, 'title': obj['title'], 'credit': obj.get('credit', '')})
        csv_file = io.StringIO(newline='')
        writer = csv.DictWriter(csv_file, fieldnames=['file', 'category', 'title', 'credit'])
        writer.writeheader()
        writer.writerows(credits)
        archive.writestr('CREDITS.csv', csv_file.getvalue().encode('utf-8-sig'))
    return output.getvalue()
