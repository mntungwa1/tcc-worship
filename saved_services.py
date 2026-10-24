"""Portable saved-service format and browser-backed saved project controls."""
import copy
import gzip
import io
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from bible import validate_bible
from core import validate_workspace, backup_bytes, MAX_BACKUP, duplicate

MAX_PROJECT = 128 * 1024 * 1024
_store = components.declare_component('tcc_saved_services',path=str(Path(__file__).with_name('saved_services_component')))


def make_project(workspace,bibles,kind='presentation'):
    project={'format':'tcc-worship-service','version':1,'kind':kind,
             'workspace':copy.deepcopy(workspace),'bibles':copy.deepcopy(bibles)}
    if kind=='songlist':
        songs=[copy.deepcopy(x) for x in workspace['service'] if x['kind']=='song']
        if not songs:raise ValueError('Add songs to Service planner before saving a song list.')
        project['workspace']['service']=songs
        project['workspace']['library']=copy.deepcopy(songs)
    return validate_project(project)


def validate_project(project):
    if not isinstance(project,dict) or project.get('format')!='tcc-worship-service' or project.get('version')!=1 or project.get('kind') not in ('presentation','songlist'):
        raise ValueError('This is not a supported TCC saved service.')
    workspace=validate_workspace(project.get('workspace'))
    if len(backup_bytes(workspace))>MAX_BACKUP:raise ValueError('The saved workspace exceeds 45 MB.')
    bibles=project.get('bibles')
    if not isinstance(bibles,list) or not 1<=len(bibles)<=32:raise ValueError('The saved service needs 1–32 Bible versions.')
    for bible in bibles:validate_bible(bible)
    if project['kind']=='songlist' and (not workspace['service'] or any(x['kind']!='song' for x in workspace['service'])):
        raise ValueError('A saved song list must contain songs only.')
    return {'format':'tcc-worship-service','version':1,'kind':project['kind'],'workspace':workspace,'bibles':copy.deepcopy(bibles)}


def read_project(raw):
    if len(raw)>MAX_PROJECT:raise ValueError('The service file is too large.')
    if raw.startswith(b'\x1f\x8b'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:raw=stream.read(MAX_PROJECT+1)
    if len(raw)>MAX_PROJECT:raise ValueError('The expanded service file exceeds 128 MB.')
    try:return validate_project(json.loads(raw))
    except (json.JSONDecodeError,UnicodeDecodeError,TypeError,KeyError) as exc:raise ValueError('Could not read this TCC service file.') from exc


def restore_project(current,project):
    project=validate_project(project)
    if project['kind']=='presentation':return project['workspace'],project['bibles']
    result=copy.deepcopy(current)
    result['service']=copy.deepcopy(project['workspace']['service'])
    result['service_title']=project['workspace']['service_title']
    result['theme']=copy.deepcopy(project['workspace']['theme'])
    signatures={json.dumps({k:x.get(k) for k in ('title','kind','slides','src','credit')},sort_keys=True) for x in result['library']}
    ids={x['id'] for x in result['library']}
    for song in project['workspace']['library']:
        signature=json.dumps({k:song.get(k) for k in ('title','kind','slides','src','credit')},sort_keys=True)
        if signature not in signatures:
            entry=copy.deepcopy(song)
            if entry['id'] in ids:entry=duplicate(entry)
            result['library'].append(entry);signatures.add(signature);ids.add(entry['id'])
    validate_workspace(result)
    if len(backup_bytes(result))>MAX_BACKUP:raise ValueError('Opening this list would exceed the 45 MB workspace limit.')
    return result,project['bibles']


def controls(workspace,bibles,prefix):
    st.caption('Saved services stay in this browser on this computer. Download a service file for a separate backup or another computer. Use the same browser profile to reopen local saves.')
    try:project=make_project(workspace,bibles)
    except ValueError as exc:
        st.info(str(exc));project=None
    result=_store(project=project,active_id=st.session_state.get('saved_service_id'),active_name=st.session_state.get('saved_service_name',workspace['service_title']),active_revision=st.session_state.get('saved_service_revision'),session=st.session_state.presenter_session,key='service_store_'+prefix,default=None)
    processed=st.session_state.setdefault('service_store_events',set())
    if result and result.get('event') not in processed:
        processed.add(result.get('event'))
        action=result.get('action')
        if action=='open':
            try:
                checked=validate_project(result['project'])
                st.session_state.pending_saved_service={'action':'open','project':checked,'id':result.get('id'),'name':result.get('name'),'revision':result.get('revision')}
                st.rerun()
            except (ValueError,KeyError,TypeError) as exc:st.error(str(exc))
        elif action=='new':
            st.session_state.pending_saved_service={'action':'new'};st.rerun()
        elif action=='saved':
            st.session_state.saved_service_id=result.get('id')
            st.session_state.saved_service_name=result.get('name')
            st.session_state.saved_service_revision=result.get('revision')
            st.session_state.notice='Saved '+str(result.get('name'))+' in this browser.'
            st.rerun()
    with st.expander('Open a downloaded service file'):
        file=st.file_uploader('Choose a TCC service file',type=['tccworship','json','gz'],key=prefix+'_service_file')
        if st.button('Open service file',disabled=file is None,key=prefix+'_service_file_open'):
            try:
                st.session_state.pending_saved_service={'action':'open','project':read_project(file.getvalue()),'id':None,'name':Path(file.name).stem,'revision':None};st.rerun()
            except (ValueError,OSError,EOFError) as exc:st.error(str(exc))
