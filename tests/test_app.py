from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=str(Path(__file__).resolve().parents[1]/'app.py')

def test_all_workspaces_render():
    at=AppTest.from_file(APP,default_timeout=30).run()
    assert not at.exception
    for page in ['Songs & library','Bible desk','Service planner','Media & presentations','Presentation desk','Settings & backups','Overview']:
        next(x for x in at.radio if x.label=='Workspace').set_value(page).run()
        assert not at.exception, (page,at.exception)

def test_create_song_search_and_queue():
    at=AppTest.from_file(APP,default_timeout=30).run()
    next(x for x in at.radio if x.label=='Workspace').set_value('Songs & library').run()
    next(x for x in at.text_input if x.label=='Title').set_value('Test hymn')
    next(x for x in at.text_area).set_value('[Verse 1]\nA line of praise\n\n[Chorus]\nTogether we sing')
    next(b for b in at.button if b.label=='Save to library').click().run()
    assert not at.exception
    next(x for x in at.text_input if x.label=='Search titles, lyrics and tags').set_value('Test hymn').run()
    next(b for b in at.button if b.label=='Add to service').click().run()
    assert at.session_state.workspace['service'][-1]['title']=='Test hymn'
    assert len(at.session_state.workspace['service'][-1]['slides'])==2

def test_bible_navigation_and_passage_queue():
    at=AppTest.from_file(APP,default_timeout=30).run()
    next(x for x in at.radio if x.label=='Workspace').set_value('Bible desk').run()
    next(x for x in at.text_input if x.label=='Quick reference').set_value('John 3:16-18')
    next(b for b in at.button if b.label=='Find passage').click().run()
    assert not at.exception
    assert at.session_state.bible_book=='John'
    assert at.session_state.bible_chapter==3
    next(b for b in at.button if b.label=='Add passage to service').click().run()
    assert not at.exception
    obj=at.session_state.workspace['service'][-1]
    assert obj['kind']=='scripture'
    assert len(obj['slides'])==3
    assert 'John 3:16' in obj['slides'][0]['text']
