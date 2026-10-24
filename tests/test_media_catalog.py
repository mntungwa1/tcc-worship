import io
import json
import zipfile

import pytest
from PIL import Image

from core import new_workspace, item, backup_bytes, load_backup, export_html, duplicate
from media_catalog import (CATEGORIES, import_uploads, source_path, is_cached_source,
                           embed_source, archive_library, asset_category)
from saved_services import make_project, read_project, restore_project


def image_bytes(colour='blue'):
    out=io.BytesIO()
    Image.new('RGB',(20,12),colour).save(out,'PNG')
    return out.getvalue()


def upload(name, raw):
    result=io.BytesIO(raw)
    result.name=name
    return result


def pack(entries):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        for name,raw in entries:z.writestr(name,raw)
    return upload('Images.zip',output.getvalue())


@pytest.fixture(autouse=True)
def media_directory(tmp_path,monkeypatch):
    monkeypatch.setenv('TCC_MEDIA_DIR',str(tmp_path/'media'))


def test_zip_folders_loose_fallback_credits_and_duplicate_content():
    w=new_workspace()
    files=pack([
        ('Images/Praise/sky.png',image_bytes()),
        ('Images/Sunday_School/kids.png',image_bytes('red')),
        ('Images/uncategorised.png',image_bytes('green')),
        ('Images/Praise/duplicate.png',image_bytes()),
        ('Images/README.txt','Collection notes'),
        ('Images/CREDITS.csv','file,title,author,license,source_page\nPraise/sky.png,Blue sky,Creator,CC0,https://example.com/sky\n')])
    result=import_uploads(w,[files],'image','Communion')
    assert result['added']==3 and result['duplicates']==1
    imported=[x for x in w['library'] if x.get('media_hash')]
    assert {x['category'] for x in imported}=={'Praise','Sunday School','Communion'}
    assert next(x for x in imported if x['title']=='Blue sky')['credit']=='Creator\nCC0\nhttps://example.com/sky'
    assert all(is_cached_source(x['src']) and source_path(x['src']).is_file() for x in imported)
    assert not any('base64,' in x['src'] for x in imported)
    restored=load_backup(backup_bytes(w))
    assert [x['category'] for x in restored['library'] if x.get('media_hash')]==[x['category'] for x in imported]


def test_invalid_batch_does_not_partly_change_workspace():
    w=new_workspace();before=backup_bytes(w)
    with pytest.raises(ValueError):
        import_uploads(w,[pack([('Praise/good.png',image_bytes()),('Worship/broken.png',b'not an image')])],'image')
    assert backup_bytes(w)==before
    with pytest.raises(ValueError,match='unsafe'):
        import_uploads(w,[pack([('../outside.png',image_bytes())])],'image')
    assert backup_bytes(w)==before


def test_missing_files_reconnect_after_json_restore_and_zip_reupload():
    w=new_workspace();raw=image_bytes()
    import_uploads(w,[pack([('Prayer/one.png',raw)])],'image')
    w=load_backup(backup_bytes(w));obj=w['library'][-1]
    source_path(obj['src']).unlink()
    with pytest.raises(ValueError,match='Re-upload'):embed_source(obj['src'])
    result=import_uploads(w,[pack([('Prayer/one.png',raw)])],'image')
    assert result['restored']==1 and result['added']==0
    assert len([x for x in w['library'] if x.get('media_hash')])==1
    assert embed_source(obj['src']).startswith('data:image/png;base64,')


def test_services_offline_exports_and_collection_zip_are_portable():
    w=new_workspace()
    import_uploads(w,[pack([('Prayer/used.png',image_bytes()),('Praise/unused.png',image_bytes('red'))])],'image')
    used=w['library'][-2];w['service']=[duplicate(used)]
    project=make_project(w,[__import__('bible').load_bible()])
    assert project['workspace']['service'][0]['src'].startswith('data:image/png;base64,')
    assert all(x['title']!='unused' for x in project['workspace']['library'])
    assert b'tcc-media:' not in export_html(w)
    assert read_project(json.dumps(project).encode())['workspace']['service'][0]['category']=='Prayer'
    reopened,_=restore_project(w,project)
    assert any(x['title']=='unused' for x in reopened['library'])
    packed=archive_library(w,'image')
    fresh=new_workspace()
    result=import_uploads(fresh,[upload('Images.zip',packed)],'image')
    assert result['added']==2 and result['duplicates']==1  # original logo is already present
    assert {asset_category(x) for x in fresh['library'] if x['kind']=='image'}=={'Welcome','Prayer','Praise'}


def test_manual_category_override_and_wrong_library_skip():
    w=new_workspace()
    assert import_uploads(w,[pack([('Praise/a.png',image_bytes())])],'image','Offering',False)['added']==1
    assert w['library'][-1]['category']=='Offering'
    result=import_uploads(w,[pack([('Praise/a.png',image_bytes())])],'video')
    assert result['added']==0 and result['ignored']==1
    assert len(CATEGORIES)==10
