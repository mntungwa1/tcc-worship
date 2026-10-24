import pytest
from core import new_workspace,item,media_data,backup_bytes,load_backup,export_html


@pytest.mark.parametrize('kind,mime',[('image','image/png'),('video','video/mp4')])
def test_background_and_media_library_survive_backup_and_export(kind,mime):
    workspace=new_workspace()
    src=media_data(b'test-media',mime)
    asset=item('Worship background',kind,src=src)
    workspace['library'].append(asset)
    workspace['theme']['background_media']={'kind':kind,'src':src,'name':asset['title'],'library_id':asset['id']}
    workspace['theme']['background_overlay']=0.6
    restored=load_backup(backup_bytes(workspace))
    assert restored['theme']['background_media']['src']==src
    assert restored['library'][-1]['src']==src
    assert src in export_html(restored).decode()


def test_background_rejects_remote_media_and_invalid_darkening():
    workspace=new_workspace()
    workspace['theme']['background_media']={'kind':'video','src':'https://example.com/movie.mp4','name':'Invalid'}
    with pytest.raises(ValueError,match='embedded'):
        backup_bytes(workspace)
    workspace['theme'].pop('background_media')
    workspace['theme']['background_overlay']=2
    with pytest.raises(ValueError,match='darkening'):
        backup_bytes(workspace)
