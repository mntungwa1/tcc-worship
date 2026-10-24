import copy
import gzip
import json
import pytest

from bible import load_bible
from core import new_workspace,item,media_data
from saved_services import make_project,read_project,restore_project


def test_saved_presentation_restores_order_media_background_and_bibles():
    workspace=new_workspace()
    song=item('Prepared hymn','song','[Verse 1]\nFirst line\nSecond line')
    video=item('Background','video',src=media_data(b'media','video/mp4'))
    workspace['service']=[song,workspace['service'][0]]
    workspace['library'].extend([song,video])
    workspace['theme']['background_media']={'kind':'video','src':video['src'],'name':video['title']}
    bibles=[load_bible()]
    extra=copy.deepcopy(bibles[0]);extra['name']='Second test version';bibles.append(extra)
    project=make_project(workspace,bibles)
    raw=gzip.compress(json.dumps(project).encode())
    restored,versions=restore_project(new_workspace(),read_project(raw))
    assert restored==workspace
    assert len(versions)==2
    assert versions[1]['name']=='Second test version'
    assert restored['theme']['background_media']['src']==video['src']


def test_saved_data_are_independent_snapshots():
    workspace=new_workspace()
    snapshot=make_project(workspace,[load_bible()])
    workspace['service'][0]['title']='Changed after saving'
    assert snapshot['workspace']['service'][0]['title']!='Changed after saving'
    assert read_project(json.dumps(snapshot).encode())==snapshot


def test_song_list_restores_order_and_retains_current_library():
    workspace=new_workspace()
    song=item('Only song','song','Praise together')
    workspace['service'].append(song)
    saved=make_project(workspace,[load_bible()],'songlist')
    assert len(saved['workspace']['service'])==1
    current=new_workspace()
    current['library'].append(item('Another library song','song','Other lyrics'))
    result,_=restore_project(current,saved)
    assert result['service'][0]['title']=='Only song'
    assert any(x['title']=='Another library song' for x in result['library'])


def test_invalid_saved_files_are_rejected():
    with pytest.raises(ValueError):read_project(b'not a project')
    project=make_project(new_workspace(),[load_bible()])
    project['workspace']['theme']['background']='bad colour'
    with pytest.raises(ValueError):read_project(json.dumps(project).encode())
    with pytest.raises(ValueError):make_project(new_workspace(),[load_bible()],'songlist')
