import base64
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from core import new_workspace,backup_bytes,load_backup,export_html,duplicate,search_items,item,slides_from_text
from bible import load_bible,parse_reference,passage_item

def test_backup_roundtrip():
    w=new_workspace();assert load_backup(backup_bytes(w))==w
    clone=duplicate(w['library'][1]);clone['slides'][0]['text']='Changed'
    assert clone['id']!=w['library'][1]['id']
    assert w['library'][1]['slides'][0]['text']!='Changed'

def test_invalid_restore_is_rejected():
    w=new_workspace();w['theme']['background']='red; background:url(evil)'
    with pytest.raises(ValueError):load_backup(json.dumps(w).encode())
    w=new_workspace();w['library'][1]['slides'][0]['src']='javascript:alert(1)'
    with pytest.raises(ValueError):load_backup(json.dumps(w).encode())
    with pytest.raises(ValueError):load_backup(b'null')

def test_search_lyrics_and_sections():
    w=new_workspace();assert len(search_items(w['library'],'gather hope'))==1
    assert slides_from_text('[Chorus]\nSing\n\n[Verse]\nPray')==[{'label':'Chorus','text':'Sing'},{'label':'Verse','text':'Pray'}]

def test_export_does_not_allow_script_injection():
    w=new_workspace();w['service'][0]['title']='</script><script>alert(1)</script>'
    result=export_html(w).decode()
    assert '</script><script>alert(1)' not in result
    assert '\\u003c/script>' in result
    assert '/*__TCC_DATA__*/' not in result

def test_full_bible_and_references():
    bible=load_bible();assert len(bible['books'])==66
    assert parse_reference('John 3:16-18',bible)==('John','3',[16,17,18])
    assert parse_reference('Psalm 23:1',bible)==('Psalms','23',[1])
    assert parse_reference('1 Cor 13:1',bible)==('1 Corinthians','13',[1])
    with pytest.raises(ValueError):parse_reference('John 3:99',bible)
    with pytest.raises(ValueError):parse_reference('J 1:1',bible)
    obj=passage_item(bible,'John','3',[16,17]);assert len(obj['slides'])==2
    assert 'God' in obj['slides'][0]['text']
    assert 'Public Domain' in obj['credit']
