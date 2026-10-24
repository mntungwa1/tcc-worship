import copy
import json
import re

from core import item,presentation_item,new_workspace,export_html
from song_import import load_bundled_songs


def normal(text):
    return ' '.join(text.split())


def test_sentences_and_long_verses_split_without_losing_words():
    song=item('Test','song','[Verse 1]\n'+('A long sentence of praise with every original word preserved '*5)+'. A second sentence.\n\n[Chorus]\nSing together\nPraise forever',credit='Original credit')
    original=copy.deepcopy(song)
    result=presentation_item(song)
    assert song==original
    assert len(result['slides'])>len(song['slides'])
    assert all(len(slide['text'].splitlines())<=2 for slide in result['slides'])
    assert all(len(line)<=44 for slide in result['slides'] for line in slide['text'].splitlines())
    assert normal(' '.join(s['text'] for s in result['slides']))==normal(' '.join(s['text'] for s in song['slides']))
    assert result['credit']==song['credit']
    assert result['slides'][-1]['source_label']=='Chorus'
    assert result['slides'][0]['label'].startswith('Verse 1 · 1/')


def test_all_included_songs_keep_their_lyrics_and_verse_order():
    for song in load_bundled_songs():
        result=presentation_item(song)
        assert normal(' '.join(x['text'] for x in result['slides']))==normal(' '.join(x['text'] for x in song['slides'])),song['title']
        assert len(result['slides'])<=500
        assert all(len(x['text'].splitlines())<=2 for x in result['slides'])


def test_export_uses_short_slides_and_leaves_saved_service_unchanged():
    workspace=new_workspace()
    song=item('Long song','song','[Verse 1]\n'+('Praise the Lord with joy and thanksgiving '*10))
    workspace['service']=[song]
    exported=export_html(workspace).decode()
    payload=json.loads(re.search(r'const DATA=(.*);\nconst BIBLES=',exported).group(1))
    assert len(payload['service'][0]['slides'])>1
    assert len(workspace['service'][0]['slides'])==1
    scripture=item('Scripture','scripture','A scripture sentence. Another sentence.')
    assert presentation_item(scripture)==scripture
