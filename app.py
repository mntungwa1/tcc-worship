import copy
import hmac
import html
import io
import json
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from core import (new_workspace, item, duplicate, slides_from_text, search_items,
                  backup_bytes, load_backup, media_data, export_html, MAX_BACKUP)
from bible import BOOKS, load_bible, validate_bible, parse_reference, passage_item

st.set_page_config(page_title='TCC Worship | Tabernacle Christian Centre', page_icon='✝', layout='wide')
st.markdown('''<style>
.block-container{padding-top:2rem}h1{letter-spacing:-.04em}div[data-testid="stMetric"]{background:#142039;border:1px solid #2c3a53;border-radius:12px;padding:14px}div[data-testid="stSidebar"]{border-right:1px solid #27354d}.eyebrow{color:#e8bc73;font-size:12px;letter-spacing:2px}.subtle{color:#a7b6cc}.stButton>button{border-radius:8px}.desk-title{font-size:22px;font-weight:650}.bible-label{font-size:12px;color:#e8bc73;letter-spacing:1px;margin-bottom:8px}
</style>''', unsafe_allow_html=True)

def secret(name, default=''):
    try: return st.secrets.get(name, os.getenv(name, default))
    except Exception: return os.getenv(name, default)

password = secret('APP_PASSWORD')
if password and not st.session_state.get('authenticated'):
    st.image(str(Path(__file__).parent/'assets/tcc_logo.png'), width=340)
    st.title('TCC Worship')
    st.caption('TABERNACLE CHRISTIAN CENTRE • WORSHIP DESK')
    with st.form('login'):
        entered=st.text_input('Church access password',type='password')
        if st.form_submit_button('Open worship desk',type='primary'):
            if hmac.compare_digest(entered,password):
                st.session_state.authenticated=True;st.rerun()
            else:st.error('Incorrect password.')
    st.stop()

if 'workspace' not in st.session_state:
    st.session_state.workspace = new_workspace()
    st.session_state.bibles = [load_bible()]
    st.session_state.verse_history = []
    st.session_state.verse_favourites = []
w=st.session_state.workspace

def notify(message):
    st.session_state.notice=message
    st.rerun()

def queue(obj):
    w['service'].append(duplicate(obj))
    notify('Added to the service.')

def preview(obj, slide=0, height=260):
    if obj['kind']=='video':st.video(obj['src']);return
    if obj['kind']=='image':st.image(obj['src']);return
    s=obj['slides'][slide]
    if s.get('src'):st.image(s['src']);return
    text=html.escape(s.get('text','')).replace('\n','<br>')
    credit=html.escape(obj.get('credit',''))
    components.html(f'''<div style="box-sizing:border-box;height:{height-10}px;background:{w['theme']['background']};color:white;font:clamp(18px,2.2vw,30px)/1.35 Arial;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;border:1px solid #34435c;border-radius:10px;padding:20px;overflow:auto"><div>{text}</div><div style="font-size:11px;color:#acb8cd;margin-top:16px">{credit}</div></div>''',height=height)

with st.sidebar:
    st.image(str(Path(__file__).parent/'assets/tcc_logo.png'),width='stretch')
    st.markdown('<div class="eyebrow">TABERNACLE CHRISTIAN CENTRE</div>',unsafe_allow_html=True)
    st.title('TCC Worship')
    st.caption('Prepare with purpose. Present with confidence.')
    page=st.radio('Workspace',['Overview','Songs & library','Bible desk','Service planner','Media & presentations','Presentation desk','Settings & backups'],label_visibility='collapsed')
    st.divider()
    st.caption(f"{len(w['library'])} library items · {len(w['service'])} service items")
    st.info('Save a backup before closing. Cloud sessions are temporary; there is no shared database in this first release.')
    if password and st.button('Lock desk'):
        st.session_state.authenticated=False;st.rerun()

st.markdown('<div class="eyebrow">TCC WORSHIP / TABERNACLE CHRISTIAN CENTRE</div>',unsafe_allow_html=True)
st.title(page)
if st.session_state.get('notice'):st.success(st.session_state.pop('notice'))

if page=='Overview':
    st.image(str(Path(__file__).parent/'assets/tcc_logo.png'),width=420)
    st.markdown('### One place to prepare your worship service')
    st.write('Build the service, choose your songs and scripture, then open a clean projector and stage view from your offline presentation package.')
    a,b,c=st.columns(3)
    a.metric('Library',len(w['library']))
    b.metric('Order of service',len(w['service']))
    c.metric('Bible versions',len(st.session_state.bibles))
    st.subheader(w['service_title'])
    for n,obj in enumerate(w['service'],1):st.write(f"**{n:02}. {obj['title']}** · {obj['kind'].title()}")
    st.caption('Start in Songs & library or Bible desk. Add items to Service planner, then use Presentation desk to export and present.')

elif page=='Songs & library':
    browse,edit=st.tabs(['Find & select','Create / edit'])
    with browse:
        cols=st.columns([3,2,1])
        q=cols[0].text_input('Search titles, lyrics and tags')
        lang=cols[1].selectbox('Language',['All']+sorted({x.get('language','') for x in w['library'] if x.get('language')}))
        fav=cols[2].checkbox('Favourites only')
        found=search_items(w['library'],q,lang,fav)
        if not found:st.info('No matching items. Create one in the next tab.')
        for obj in found:
            with st.expander(f"{'★ ' if obj.get('favourite') else ''}{obj['title']} · {obj['kind']}"):
                a,b=st.columns([3,2])
                with a:preview(obj)
                with b:
                    st.caption(obj.get('tags',''))
                    if st.button('Add to service',key='add'+obj['id'],type='primary'):queue(obj)
                    if st.button('Toggle favourite',key='fav'+obj['id']):obj['favourite']=not obj.get('favourite');notify('Favourite updated.')
    with edit:
        editable=[x for x in w['library'] if x['kind'] in ('song','announcement','scripture')]
        selected=st.selectbox('Edit an existing item',['New item']+[x['id'] for x in editable],format_func=lambda v: 'New item' if v=='New item' else next(x['title'] for x in editable if x['id']==v))
        original=next((x for x in editable if x['id']==selected),None)
        with st.form('editor'+selected):
            title=st.text_input('Title',value=original['title'] if original else '')
            kind=st.selectbox('Type',['song','announcement','scripture'],index=['song','announcement','scripture'].index(original['kind']) if original else 0)
            language=st.text_input('Language',value=original.get('language','') if original else '')
            tags=st.text_input('Tags / themes',value=original.get('tags','') if original else '')
            txt='\n\n'.join((('['+s['label']+']\n') if s.get('label') else '')+s['text'] for s in original['slides']) if original else ''
            text=st.text_area('Lyrics or text — separate slides with a blank line; use [Chorus] for labels',value=txt,height=250)
            credit=st.text_input('Author / copyright / licence attribution',value=original.get('credit','') if original else '')
            if st.form_submit_button('Save to library',type='primary'):
                if not title.strip() or not slides_from_text(text):st.error('Add a title and at least one slide of text.')
                else:
                    obj=item(title.strip(),kind,text,language=language,tags=tags,credit=credit)
                    if original:obj['id']=original['id'];obj['favourite']=original.get('favourite',False);w['library'][w['library'].index(original)]=obj
                    else:w['library'].append(obj)
                    notify('Saved. Existing service copies stay as prepared; add the revised item to use it.')

elif page=='Bible desk':
    st.caption('Holyrics-inspired Bible workspace • verse list on the left • book, chapter and verse grids on the right')
    versions=st.session_state.bibles
    vi=st.selectbox('Bible version',range(len(versions)),format_func=lambda i:versions[i]['name'])
    bible=versions[vi]
    with st.form('reference'):
        a,b=st.columns([5,1])
        ref=a.text_input('Quick reference',placeholder='John 3:16-18 or Psalms 23:1-6')
        go=b.form_submit_button('Find passage',type='primary')
    if go:
        try:
            book,ch,nums=parse_reference(ref,bible)
            st.session_state.bible_book=book;st.session_state.bible_chapter=int(ch)
            st.session_state.passage_selection=nums
        except ValueError as exc:st.error(str(exc))
    books=[x for x in BOOKS if x in bible['books']]+[x for x in bible['books'] if x not in BOOKS]
    if st.session_state.get('bible_book') not in books:st.session_state.bible_book=books[0]
    book=st.session_state.bible_book
    chapters=sorted(map(int,bible['books'][book]))
    if st.session_state.get('bible_chapter') not in chapters:st.session_state.bible_chapter=chapters[0]
    chapter=st.session_state.bible_chapter
    verses=bible['books'][book][str(chapter)]
    left,right=st.columns([1.25,1.05],gap='large')
    with right:
        st.markdown('<div class="bible-label">BOOKS</div>',unsafe_allow_html=True)
        group=st.radio('Testament',['Old Testament','New Testament','All'],horizontal=True,label_visibility='collapsed')
        visible=[b for b in books if group=='All' or (b in BOOKS[:39] if group=='Old Testament' else b in BOOKS[39:])]
        grid=st.columns(5)
        for n,b in enumerate(visible):
            if grid[n%5].button(b,key='book_'+b,type='primary' if b==book else 'secondary',width='stretch'):
                st.session_state.bible_book=b;st.session_state.bible_chapter=min(map(int,bible['books'][b]));st.session_state.passage_selection=[];st.rerun()
        st.markdown('<div class="bible-label">CHAPTERS</div>',unsafe_allow_html=True)
        grid=st.columns(10)
        for n,ch in enumerate(chapters):
            if grid[n%10].button(str(ch),key=f'ch_{book}_{ch}',type='primary' if ch==chapter else 'secondary',width='stretch'):
                st.session_state.bible_chapter=ch;st.session_state.passage_selection=[];st.rerun()
        st.markdown('<div class="bible-label">VERSES</div>',unsafe_allow_html=True)
        grid=st.columns(10)
        for n,v in enumerate(sorted(map(int,verses))):
            if grid[n%10].button(str(v),key=f'v_{book}_{chapter}_{v}',width='stretch'):
                st.session_state.passage_selection=[v];st.rerun()
    with left:
        st.subheader(f'{book} {chapter}')
        verse_numbers=sorted(map(int,verses))
        selection=[n for n in st.session_state.get('passage_selection',[]) if n in verse_numbers] or [verse_numbers[0]]
        # A changing widget key prevents a previous chapter's selection from leaking into this one.
        choose=st.multiselect('Select verses to present',verse_numbers,default=selection,key=f'sel_{vi}_{book}_{chapter}_{selection}')
        with st.container(height=260,border=True):
            for n in verse_numbers:
                color='#e8bc73' if n in choose else '#b9c7d9'
                st.markdown(f'<p style="color:{color}"><strong>{n}</strong> {html.escape(verses[str(n)])}</p>',unsafe_allow_html=True)
        if choose:
            passage=passage_item(bible,book,chapter,choose)
            preview(passage,height=240)
            a,b=st.columns(2)
            if a.button('Add passage to service',type='primary',width='stretch'):
                st.session_state.verse_history.insert(0,copy.deepcopy(passage));queue(passage)
            if b.button('★ Save passage',width='stretch'):
                st.session_state.verse_favourites.append(copy.deepcopy(passage));notify('Passage saved for this session.')
            comparison=st.checkbox('Compare with another imported version')
            if comparison:
                other=[x for i,x in enumerate(versions) if i!=vi]
                if not other:st.info('Import another authorised Bible version in Settings & backups.')
                else:
                    oi=st.selectbox('Compare version',range(len(other)),format_func=lambda i:other[i]['name'])
                    for n in choose:st.write(f"{n}. {other[oi]['books'].get(book,{}).get(str(chapter),{}).get(str(n),'Verse unavailable in this version.')}")
    st.divider()
    search=st.text_input('Search words or phrases throughout this Bible')
    if search.strip():
        hits=[]
        for bk,chs in bible['books'].items():
            for ch,vs in chs.items():
                for n,text in vs.items():
                    if search.casefold() in text.casefold():hits.append((bk,ch,n,text))
        st.caption(f'{len(hits)} matches · first 40 shown')
        for bk,ch,n,text in hits[:40]:
            if st.button(f'{bk} {ch}:{n} — {text[:110]}',key=f'hit_{bk}_{ch}_{n}'):
                st.session_state.bible_book=bk;st.session_state.bible_chapter=int(ch);st.session_state.passage_selection=[int(n)];st.rerun()
    for label,key in [('Favourite passages','verse_favourites'),('Passage history','verse_history')]:
        with st.expander(label):
            for n,obj in enumerate(st.session_state[key][:30]):
                if st.button('Add '+obj['title'],key=f'{key}_{n}'):queue(obj)

elif page=='Service planner':
    w['service_title']=st.text_input('Service title',value=w['service_title']) or 'TCC Worship Service'
    st.caption('Use the arrows to reorder. Items are independent copies, keeping your prepared service stable when library entries change.')
    if not w['service']:st.info('Add songs, scripture or media to begin.')
    for n,obj in enumerate(w['service']):
        with st.container(border=True):
            a,b,c,d=st.columns([8,1,1,1])
            a.write(f"**{n+1:02}. {obj['title']}**")
            a.caption(f"{obj['kind'].title()} · {max(1,len(obj['slides']))} slides")
            if b.button('↑',key='up'+obj['id'],disabled=n==0):w['service'][n-1],w['service'][n]=w['service'][n],w['service'][n-1];st.rerun()
            if c.button('↓',key='down'+obj['id'],disabled=n==len(w['service'])-1):w['service'][n+1],w['service'][n]=w['service'][n],w['service'][n+1];st.rerun()
            if d.button('✕',key='remove'+obj['id']):w['service'].pop(n);st.rerun()
            with st.expander('Preview / duplicate'):
                preview(obj)
                if st.button('Duplicate item',key='dupe'+obj['id']):w['service'].insert(n+1,duplicate(obj));st.rerun()

elif page=='Media & presentations':
    st.write('Import images, MP4/WebM videos, PDF slides, or the text from a PowerPoint presentation.')
    st.caption('For faithful PowerPoint layout, export to PDF first. PPTX import here reads text only; it does not reproduce graphics, animations or slide design.')
    upload=st.file_uploader('Choose media or presentation',type=['png','jpg','jpeg','webp','mp4','webm','pdf','pptx'])
    if upload:
        st.caption(f'{upload.name} · {upload.size/1024/1024:.1f} MB')
        title=st.text_input('Media title',value=Path(upload.name).stem)
        if st.button('Import into library',type='primary'):
            try:
                if upload.size>20*1024*1024:raise ValueError('Each upload is limited to 20 MB in this release.')
                suffix=Path(upload.name).suffix.lower();raw=upload.getvalue()
                if suffix=='.pdf':
                    import fitz
                    with fitz.open(stream=raw,filetype='pdf') as pdf:
                        if len(pdf)>80:raise ValueError('Limit each PDF to 80 pages.')
                        obj=item(title,'presentation','temporary')
                        obj['slides']=[{'label':f'Slide {i+1}','text':'','src':media_data(p.get_pixmap(matrix=fitz.Matrix(1.25,1.25)).tobytes('png'),'image/png')} for i,p in enumerate(pdf)]
                elif suffix=='.pptx':
                    from pptx import Presentation
                    prs=Presentation(io.BytesIO(raw));obj=item(title,'presentation','temporary')
                    obj['slides']=[{'label':f'Slide {i+1}','text':'\n'.join(shape.text for shape in slide.shapes if shape.has_text_frame)} for i,slide in enumerate(prs.slides)]
                    obj['slides']=[s for s in obj['slides'] if s['text'].strip()]
                    if not obj['slides']:raise ValueError('No text found. Export the slides to PDF and import that instead.')
                else:
                    mime={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.mp4':'video/mp4','.webm':'video/webm'}[suffix]
                    obj=item(title,'video' if suffix in ('.mp4','.webm') else 'image',src=media_data(raw,mime))
                candidate=copy.deepcopy(w);candidate['library'].append(obj)
                if len(backup_bytes(candidate))>MAX_BACKUP:raise ValueError('Workspace would exceed 45 MB. Use smaller media or split services.')
                w['library'].append(obj);notify('Imported. Find the item in Songs & library and add it to the service.')
            except Exception as exc:st.error(f'Could not import: {exc}')

elif page=='Presentation desk':
    st.subheader('Ready for the projector')
    st.write('Download the offline presentation, open it on the church laptop in Chrome or Edge, and click **Open projector**. Move that window to the projector screen and select **Full screen**.')
    if w['service']:
        st.download_button('Download offline presentation',data=export_html(w, st.session_state.bibles),file_name='TCC_Worship_Live.html',mime='text/html',type='primary')
        st.caption('Includes this service and its embedded media. No internet connection is required. The exported controller must remain open.')
        idx=st.selectbox('Preview service item',range(len(w['service'])),format_func=lambda i:w['service'][i]['title'])
        obj=w['service'][idx]
        slide=st.slider('Preview slide',1,max(2,len(obj['slides'])),1) if len(obj['slides'])>1 else 1
        preview(obj,min(slide-1,max(0,len(obj['slides'])-1)),height=400)
    else:st.info('Your service is empty. Add some items before exporting.')
    with st.expander('Optional FreeShow local controls — experimental'):
        st.write('Requires this Streamlit app and FreeShow to run on the same computer. Enable the REST API in FreeShow Connections. These controls have not been tested against a running FreeShow installation.')
        if secret('TCC_LOCAL_MODE')!='1':st.info('Local controls are disabled. Start locally with TCC_LOCAL_MODE=1 to enable them.')
        else:
            port=st.number_input('FreeShow REST port',min_value=1024,max_value=65535,value=5506)
            auth=st.text_input('FreeShow auth key',type='password')
            action=st.selectbox('Command',['get_shows','next_slide','previous_slide','clear_all','restore_output'])
            if st.button('Send command to local FreeShow'):
                import urllib.parse,urllib.request
                query=urllib.parse.urlencode({'action':action,'data':'{}','auth':auth})
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{int(port)}?{query}',timeout=4) as r:
                        response=r.read(100000).decode('utf-8',errors='replace')
                    st.success('FreeShow accepted the HTTP request.');st.code(response or '(empty response)')
                except Exception:st.error('Could not complete the FreeShow command. Check the local app, API port and auth key.')

elif page=='Settings & backups':
    st.subheader('Presentation theme')
    a,b,c=st.columns(3)
    w['theme']['background']=a.color_picker('Background',w['theme']['background'])
    w['theme']['accent']=b.color_picker('Accent',w['theme']['accent'])
    w['theme']['font_size']=c.slider('Presentation text size',24,90,w['theme']['font_size'])
    st.subheader('Save and restore')
    st.write('The workspace is held in this browser session. Download backups regularly. This release does not automatically save to GitHub or provide team synchronisation.')
    st.download_button('Download workspace backup',backup_bytes(w),file_name='TCC_Worship_Backup.json',mime='application/json')
    restored=st.file_uploader('Restore TCC workspace JSON',type=['json'],key='restore')
    confirm=st.checkbox('Replace the current workspace with this backup')
    if st.button('Restore backup',disabled=not(restored and confirm)):
        try:
            replacement=load_backup(restored.getvalue())
            st.session_state.workspace=replacement
            notify('Workspace restored.')
        except ValueError as exc:st.error(str(exc))
    st.subheader('Additional Bible versions')
    st.caption('WEB is included offline. Import additional versions that you are authorised to use. Bible imports and verse favourites are session-only; save your Bible source files separately.')
    st.code('{"name":"Version name","credit":"Required attribution","books":{"John":{"3":{"16":"Verse text"}}}}',language='json')
    bf=st.file_uploader('Import authorised Bible JSON',type=['json'],key='bible_import')
    if st.button('Add Bible version',disabled=bf is None):
        try:
            if bf.size>20*1024*1024:raise ValueError('Bible import exceeds 20 MB.')
            bible=validate_bible(json.loads(bf.getvalue()));st.session_state.bibles.append(bible);notify('Bible version added.')
        except (ValueError,TypeError) as exc:st.error(str(exc))
    st.subheader('Access and deployment')
    st.write('For a shared deployment, set APP_PASSWORD in Streamlit Secrets. Keep passwords and media backups out of a public GitHub repository. See README.md for local and cloud setup.')
    st.caption('TCC Worship v0.1 • Original implementation inspired by worship presentation workflows. No Holyrics, FreeShow, Quelea or OpenLP source code is included.')
