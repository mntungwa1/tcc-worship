from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=str(Path(__file__).resolve().parents[1]/'app.py')

def test_all_workspaces_render():
    at=AppTest.from_file(APP,default_timeout=30).run()
    assert not at.exception
    for page in ['Songs & library','Bible desk','Service planner','Media & presentations','Presentation desk','Saved services','Settings & backups','Overview']:
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
    song_id=next(x['id'] for x in at.session_state.workspace['library'] if x['title']=='Test hymn')
    next(b for b in at.button if b.key=='add'+song_id).click().run()
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


def test_live_desk_snapshot_changes_only_when_refreshed():
    at=AppTest.from_file(APP,default_timeout=30).run()
    next(x for x in at.radio if x.label=='Workspace').set_value('Presentation desk').run()
    assert not at.exception
    original=at.session_state.live_desk_html
    assert 'CONGREGATION · LIVE OUTPUT' in original
    assert 'id="preview"' in original and 'id="live"' in original
    at.session_state.workspace['service_title']='Updated service title'
    at.run()
    assert at.session_state.live_desk_html==original
    assert any('have changed' in x.value for x in at.info)
    next(x for x in at.button if x.label=='Load / refresh live desk').click().run()
    assert not at.exception
    assert at.session_state.live_desk_html!=original
    assert 'Updated service title' in at.session_state.live_desk_html


def test_media_categories_recategorisation_background_and_queue(tmp_path,monkeypatch):
    import io
    from PIL import Image
    from media_catalog import import_uploads
    monkeypatch.setenv('TCC_MEDIA_DIR',str(tmp_path/'media'))
    at=AppTest.from_file(APP,default_timeout=30).run()
    raw=io.BytesIO();Image.new('RGB',(32,20),'blue').save(raw,'PNG')
    raw.seek(0);raw.name='Morning.png'
    import_uploads(at.session_state.workspace,[raw],'image','Worship')
    asset=at.session_state.workspace['library'][-1]
    asset['credit']='Test creator · CC0'
    next(x for x in at.radio if x.label=='Workspace').set_value('Media & presentations').run()
    assert not at.exception

    next(x for x in at.selectbox if x.key=='image_browse_category').set_value('Worship').run()
    assert not at.exception
    next(x for x in at.selectbox if x.key=='media_category_'+asset['id']).set_value('Prayer')
    next(x for x in at.button if x.key=='media_category_save_'+asset['id']).click().run()
    assert at.session_state.workspace['library'][-1]['category']=='Prayer'
    next(x for x in at.selectbox if x.key=='image_browse_category').set_value('Prayer').run()
    next(x for x in at.button if x.key=='media_background_'+asset['id']).click().run()
    assert at.session_state.workspace['theme']['background_media']['src'].startswith('data:image/png;base64,')
    next(x for x in at.button if x.key=='media_queue_'+asset['id']).click().run()
    assert at.session_state.workspace['service'][-1]['src'].startswith('data:image/png;base64,')
    assert not at.exception


def test_empty_background_category_keeps_file_picker_and_explorer_upload_visible():
    at=AppTest.from_file(APP,default_timeout=30).run()
    next(x for x in at.radio if x.label=='Workspace').set_value('Presentation desk').run()
    next(x for x in at.radio if x.key=='live_bg_type').set_value('Video').run()
    next(x for x in at.selectbox if x.key=='live_bg_category_Video').set_value('Sunday School').run()
    chooser=next(x for x in at.selectbox if x.key=='live_bg_Video')
    assert chooser.disabled
    assert any('Browse your computer for video' in x.proto.label for x in at.get('file_uploader'))
    assert any('Click Browse files below' in x.value for x in at.info)
    assert next(x for x in at.button if x.key=='live_bg_apply').disabled
    assert not at.exception


def test_background_computer_upload_selects_file_then_applies(tmp_path,monkeypatch):
    import io
    import streamlit as st
    from PIL import Image
    monkeypatch.setenv('TCC_MEDIA_DIR',str(tmp_path/'media'))
    raw=io.BytesIO();Image.new('RGB',(32,20),'green').save(raw,'PNG')
    raw.seek(0);raw.name='Garden.png';raw.size=len(raw.getvalue())
    original=st.file_uploader
    def picker(label,*args,**kwargs):
        if label.startswith('Browse your computer for image'):
            return [raw] if kwargs['key'].endswith('_0') else []
        return original(label,*args,**kwargs)
    monkeypatch.setattr(st,'file_uploader',picker)
    at=AppTest.from_file(APP,default_timeout=30).run()
    next(x for x in at.radio if x.label=='Workspace').set_value('Presentation desk').run()
    next(x for x in at.radio if x.key=='live_bg_type').set_value('Image').run()
    next(x for x in at.selectbox if x.key=='live_bg_upload_category_Image').set_value('Sunday School').run()
    assert any('Selected files to add' in x.value for x in at.markdown)
    next(x for x in at.button if x.key=='live_bg_upload_add_Image').click().run()
    assert not at.exception
    asset=next(x for x in at.session_state.workspace['library'] if x['title']=='Garden')
    assert asset['category']=='Sunday School'
    assert next(x for x in at.selectbox if x.key=='live_bg_Image').value==asset['id']
    assert next(x for x in at.selectbox if x.key=='live_bg_category_Image').value=='Sunday School'
    assert not at.session_state.workspace['theme'].get('background_media')
    next(x for x in at.button if x.key=='live_bg_apply').click().run()
    assert not at.exception
    assert at.session_state.workspace['theme']['background_media']['name']=='Garden'
    assert at.session_state.workspace['theme']['background_media']['src'].startswith('data:image/png;base64,')
