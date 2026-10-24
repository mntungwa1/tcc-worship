import copy
import pytest

from bible_catalogue import load_catalogue,is_free_translation,convert_translation,source_notice,NoticeParser


def fixture():
    entry=next(x for x in load_catalogue() if x['id']=='BSB')
    entry=copy.deepcopy(entry)
    entry['numberOfBooks']=1
    payload={'translation':entry,'books':[{'id':'JHN','name':'John','numberOfChapters':1,'chapters':[{'chapter':{'number':3,'content':[{'type':'heading','text':'Not scripture'},{'type':'verse','number':16,'text':'For God so loved the world…'},{'type':'verse','number':17,'text':'Two\nlines'}]}}]}]}
    return entry,payload


def test_curated_twelve_have_open_permissions_and_full_book_counts():
    catalogue=load_catalogue()
    assert len(catalogue)==12
    assert len({x['id'] for x in catalogue})==12
    assert all(is_free_translation(x) and x['numberOfBooks']==66 for x in catalogue)
    assert {'eng_kjv','BSB','eng_web','eng_fbv','eng_lsv'}<={x['id'] for x in catalogue}


def test_conversion_preserves_text_and_attribution():
    entry,payload=fixture()
    result=convert_translation(payload,entry,'copyright credit','Full notice','https://example.org/license')
    assert result['books']['John']['3']=={'16':'For God so loved the world…','17':'Two\nlines'}
    assert result['credit']=='copyright credit'
    assert result['license_notice']=='Full notice'


def test_changed_permissions_and_incomplete_download_are_rejected():
    entry,payload=fixture()
    payload['translation']['license']['commercialUse']='not-allowed'
    with pytest.raises(ValueError,match='permissions'):
        convert_translation(payload,entry,'','','')
    entry,payload=fixture()
    payload['books'][0]['numberOfChapters']=2
    with pytest.raises(ValueError,match='chapter count'):
        convert_translation(payload,entry,'','','')


def test_kjv_carries_territorial_notice():
    entry=next(x for x in load_catalogue() if x['id']=='eng_kjv')
    credit,notice,url=source_notice(entry)
    assert 'United Kingdom' in credit


def test_legacy_http_license_link_is_captured_as_https():
    parser=NoticeParser()
    parser.feed('<p>Copyright © 2020 Publisher</p><a href="http://creativecommons.org/licenses/by-sa/4.0/">Licence</a><script>do not include</script>')
    assert parser.licenses==['https://creativecommons.org/licenses/by-sa/4.0/']
    assert 'do not include' not in ''.join(parser.parts)
