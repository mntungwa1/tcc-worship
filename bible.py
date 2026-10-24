"""Offline Bible navigation and import, shared by the Holyrics-inspired desk."""
import json
import re
from pathlib import Path
from core import item

BOOKS = ['Genesis','Exodus','Leviticus','Numbers','Deuteronomy','Joshua','Judges','Ruth','1 Samuel','2 Samuel','1 Kings','2 Kings','1 Chronicles','2 Chronicles','Ezra','Nehemiah','Esther','Job','Psalms','Proverbs','Ecclesiastes','Song of Solomon','Isaiah','Jeremiah','Lamentations','Ezekiel','Daniel','Hosea','Joel','Amos','Obadiah','Jonah','Micah','Nahum','Habakkuk','Zephaniah','Haggai','Zechariah','Malachi','Matthew','Mark','Luke','John','Acts','Romans','1 Corinthians','2 Corinthians','Galatians','Ephesians','Philippians','Colossians','1 Thessalonians','2 Thessalonians','1 Timothy','2 Timothy','Titus','Philemon','Hebrews','James','1 Peter','2 Peter','1 John','2 John','3 John','Jude','Revelation']

def load_bible():
    return validate_bible(json.loads(Path(__file__).with_name('data').joinpath('web.json').read_text()))

def validate_bible(data):
    if not isinstance(data, dict) or not isinstance(data.get('name'), str) or not isinstance(data.get('books'), dict) or not data['books']:
        raise ValueError('Bible JSON needs a name and a non-empty books object.')
    for book, chapters in data['books'].items():
        if not isinstance(book, str) or not isinstance(chapters, dict) or not chapters:
            raise ValueError('Invalid book structure.')
        for chapter, verses in chapters.items():
            if not str(chapter).isdigit() or int(chapter) < 1 or not isinstance(verses, dict) or not verses:
                raise ValueError('Invalid chapter structure.')
            for verse, text in verses.items():
                if not str(verse).isdigit() or int(verse) < 1 or not isinstance(text, str) or not text.strip():
                    raise ValueError('Each verse needs a positive number and non-empty text.')
    if not isinstance(data.get('credit', ''), str):
        raise ValueError('Bible credit must be text.')
    return data

def parse_reference(reference, bible):
    m = re.fullmatch(r'\s*(.+?)\s+(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*', reference)
    if not m:
        raise ValueError('Use a reference such as John 3:16 or Psalms 23:1-6.')
    name, chapter, first, last = m.groups()
    norm = lambda t: re.sub(r'[^a-z0-9]', '', t.casefold())
    aliases={'psalm':'psalms','songofsongs':'songofsolomon'}
    key=aliases.get(norm(name),norm(name))
    matches=[b for b in bible['books'] if norm(b)==key]
    if not matches:
        matches=[b for b in bible['books'] if norm(b).startswith(key)]
    if len(matches)!=1:
        raise ValueError('Book name is missing or ambiguous.')
    book=matches[0]
    chapter=str(int(chapter));first=int(first);last=int(last or first)
    verses=bible['books'][book].get(chapter,{})
    if last < first or last-first>175 or not all(str(v) in verses for v in range(first,last+1)):
        raise ValueError('That chapter or verse range is not available.')
    return book,chapter,list(range(first,last+1))

def passage_item(bible,book,chapter,numbers):
    numbers=sorted(set(numbers))
    if not numbers: raise ValueError('Select at least one verse.')
    result=item(f'{book} {chapter}:{",".join(map(str,numbers))}', 'scripture', 'temporary')
    result['slides']=[{'label':f'{book} {chapter}:{n}', 'text':f'{bible["books"][book][str(chapter)][str(n)]}\n\n{book} {chapter}:{n}'} for n in numbers]
    result['credit']=bible.get('credit') or bible['name']
    return result
