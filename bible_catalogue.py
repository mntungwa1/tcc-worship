"""Free Bible catalogue, bounded downloads and lossless verse-text conversion."""
import base64
import gzip
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from bible import BOOKS, validate_bible

API = 'https://bible.helloao.org'
BOOK_IDS = 'GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'.split()
CANON = dict(zip(BOOK_IDS, BOOKS))


def is_free_translation(entry):
    license_info = entry.get('license', {})
    return (license_info.get('commercialUse') == 'allowed'
            and isinstance(license_info.get('publicDomain'), bool)
            and re.fullmatch(r'[A-Za-z0-9_-]+', entry.get('id', '')) is not None
            and bool(entry.get('simpleCompleteTranslationApiLink')))


def load_catalogue():
    path = Path(__file__).with_name('data') / 'bible_catalogue.json.gz.b64'
    payload = json.loads(gzip.decompress(base64.b64decode(path.read_text())))
    return [x for x in payload['translations'] if is_free_translation(x)]


def download(url, max_bytes=30*1024*1024):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('bible.helloao.org', 'ebible.org') or parsed.username or parsed.password:
        raise ValueError('Bible downloads must use an approved HTTPS source.')
    request = urllib.request.Request(url, headers={'User-Agent':'TCC-Worship/0.2'})
    with urllib.request.urlopen(request, timeout=45) as response:
        final = urllib.parse.urlsplit(response.geturl())
        if final.scheme != 'https' or final.hostname not in ('bible.helloao.org', 'ebible.org'):
            raise ValueError('The Bible source redirected outside approved hosts.')
        raw = response.read(max_bytes+1)
    if len(raw) > max_bytes:
        raise ValueError('The Bible download exceeds the supported size.')
    return raw


class NoticeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0
        self.licenses = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'):
            self.hidden += 1
        if tag in ('p','div','h1','h2','br','li','tr'):
            self.parts.append('\n')
        if tag == 'a':
            href = dict(attrs).get('href','')
            parsed = urllib.parse.urlsplit(href)
            if parsed.scheme in ('http','https') and parsed.hostname in ('creativecommons.org','www.creativecommons.org'):
                self.licenses.append(urllib.parse.urlunsplit(('https',parsed.netloc,parsed.path,parsed.query,'')))

    def handle_endtag(self, tag):
        if tag in ('script','style'):
            self.hidden = max(0,self.hidden-1)
        if tag in ('p','div','h1','h2','li','tr'):
            self.parts.append('\n')

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def source_notice(entry):
    url = entry.get('licenseUrl','')
    if entry['license']['publicDomain']:
        notice = f"{entry['englishName']} ({entry['id']}). Public domain according to source metadata. Source/licensing: {url}"
        if entry['id'] in ('eng_kjv','eng_kja','eng_cpb'):
            notice += ' King James Version printing rights are subject to Crown Letters Patent in the United Kingdom.'
        return notice, notice, url
    if urllib.parse.urlsplit(url).hostname != 'ebible.org':
        raise ValueError('A verified source copyright notice is required for this translation.')
    parser = NoticeParser()
    parser.feed(download(url, 1024*1024).decode('utf-8', errors='replace'))
    notice = '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
    if not parser.licenses or 'creativecommons.org' not in ' '.join(parser.licenses):
        raise ValueError('The source does not provide a supported open licence notice. This version was not added.')
    copyright_lines = []
    seen = set()
    for line in notice.splitlines():
        if re.match(r'^(?:copyright\s*(?:©|\(c\))|©|translation by:)',line,re.I) and len(line)<350 and line.casefold() not in seen:
            copyright_lines.append(line)
            seen.add(line.casefold())
    if not copyright_lines:
        raise ValueError('The source attribution could not be verified. This version was not added.')
    license_url = parser.licenses[0]
    credit = '\n'.join([entry['englishName'],*copyright_lines,license_url,url])
    return credit, notice, license_url


def convert_translation(payload, entry, credit, notice, license_url):
    metadata = payload.get('translation', {})
    if metadata.get('id') != entry['id'] or not is_free_translation(metadata):
        raise ValueError('The downloaded translation identity or permissions do not match the catalogue.')
    books = {}
    labels = {}
    expected_books = payload.get('books', [])
    if len([b for b in expected_books if not b.get('isApocryphal')]) != metadata['numberOfBooks']:
        raise ValueError('The download has an unexpected book count.')
    for book in expected_books:
        name = CANON.get(book['id'],book.get('commonName') or book['name'])
        if name in books:
            raise ValueError('Duplicate book in source download.')
        chapters = {}
        for wrapper in book['chapters']:
            chapter = wrapper['chapter']
            verses = {}
            for verse in chapter['content']:
                if verse['type'] != 'verse':
                    continue
                number = str(verse['number'])
                text = verse.get('text','')
                if not text.strip():
                    # An intentionally omitted verse is not fabricated or renumbered.
                    continue
                if number in verses:
                    raise ValueError('Duplicate verse in source download.')
                verses[number] = text
            if not verses:
                raise ValueError('A chapter has no readable verses; this translation was not added.')
            number = str(chapter['number'])
            if number in chapters:
                raise ValueError('Duplicate chapter in source download.')
            chapters[number] = verses
        if len(chapters) != book['numberOfChapters']:
            raise ValueError('The download has an unexpected chapter count.')
        books[name] = chapters
        labels[name] = book['name']
    result = {'id':entry['id'],'name':entry['englishName']+' ('+entry['shortName']+')',
              'books':books,'book_labels':labels,'credit':credit,'license_notice':notice,
              'license_url':license_url,'source_url':API+entry['simpleCompleteTranslationApiLink'],
              'language':entry['language'],'text_direction':entry.get('textDirection','ltr'),
              'source_metadata':metadata}
    return validate_bible(result)


def fetch_translation(translation_id):
    entries = {x['id']:x for x in load_catalogue()}
    if translation_id not in entries:
        raise ValueError('This translation is not in the approved free catalogue.')
    entry = entries[translation_id]
    path = entry['simpleCompleteTranslationApiLink']
    if path != f'/api/{translation_id}/complete.simple.json':
        raise ValueError('Unexpected translation download link.')
    credit,notice,license_url = source_notice(entry)
    payload = json.loads(download(API+path))
    return convert_translation(payload,entry,credit,notice,license_url)
