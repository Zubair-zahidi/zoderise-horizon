"""Exercise real Streamlit pages and generation-save reruns with mocked inference."""
import os
import sys
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
tmp = tempfile.TemporaryDirectory()
os.environ.update(ZODERISE_DB=str(Path(tmp.name)/'ui.db'), ZODERISE_STORAGE=str(Path(tmp.name)/'storage'), ZODERISE_ADMIN_EMAIL='', ZODERISE_ADMIN_PASSWORD='')
from streamlit.testing.v1 import AppTest
from zoderise import database as db, ai
from zoderise.documents import save_document
from zoderise.security import hash_password
from configure_owner import provision_owner

uid = provision_owner('owner@example.com', hash_password('LocalOwner8'))
doc_id, _, _ = save_document(uid, 'lesson.txt', b'Pascal pressure in a liquid is transmitted equally.', 'text/plain', domain='Physics')
status = {'online':True,'models':['zoderise:latest','zoderise-vision:latest'],'text_ready':True,'vision_ready':True,'endpoint':'http://127.0.0.1:11434','local_endpoint':True}

def check(at, label):
    assert not at.exception, f'{label}: {[e.message for e in at.exception]}'
    print('PASS',label)

with patch.object(ai, 'model_status', return_value=status), patch.object(ai, 'ollama_online', return_value=True), patch.object(ai, 'ollama_tags', return_value=status['models']), patch.object(ai, 'chat_stream', return_value=iter(['Evidence-backed answer [1].'])):
    at = AppTest.from_file(str(ROOT/'app.py'), default_timeout=20).run()
    check(at, 'Sign in screen')
    at.text_input(key='auth_identifier').set_value('owner@example.com')
    at.text_input(key='auth_password').set_value('LocalOwner8')
    at.button(key='auth_login').click().run()
    check(at, 'Owner login and home')
    for page in ['Chat','Knowledge','Research','Study Lab','History','Saved','Tools','Account','Settings','About','Diagnostics','Admin','Home']:
        at.button(key=f'nav_{page}').click().run()
        check(at, page)
    at.button(key='nav_Research').click().run()
    at.text_area[0].set_value('Explain pressure')
    at.button(key='research_run').click().run()
    check(at, 'Research generation rerun')
    assert at.session_state['research_result']['answer']
    at.button(key='save_research_output').click().run()
    check(at, 'Research save')
    assert len(db.list_saved_outputs(uid)) == 1
    assert at.button(key='save_research_output').disabled
    with patch.object(ai, 'chat_stream', return_value=iter(['Study material [1].'])):
        at.button(key='nav_Study Lab').click().run()
        at.multiselect(key='study_sources').set_value([doc_id])
        at.button(key='study_generate').click().run()
        check(at, 'Study generation rerun')
        at.button(key='save_study_output').click().run()
        check(at, 'Study save')
        assert len(db.list_saved_outputs(uid)) == 2
    at.button(key='nav_Account').click().run()
    at.checkbox(key='delete_account_confirm').check()
    at.button(key='delete_account_button').click().run()
    check(at,'Last administrator cannot delete account')
    assert any('administrator' in e.value for e in at.error)
    with patch.object(ai, 'chat_stream', side_effect=lambda *a, **k: iter(['A local answer.'])):
        at.button(key='new_session').click().run()
        at.chat_input[0].set_value('Hello local AI').run()
        check(at, 'Ephemeral chat')
        assert at.session_state['ephemeral_messages'][-1]['role'] == 'assistant'
        assert not db.list_conversations(uid)
        at.button(key='new_session').click().run()
        assert not at.session_state['ephemeral_messages']
        at.session_state['privacy_mode'] = 'Persistent'
        at.run()
        at.chat_input[0].set_value('Save this conversation').run()
        check(at, 'Persistent chat')
        cid = at.session_state['conversation_id']
        assert len(db.get_messages(uid,cid)) == 2
        at.button(key=f'archive_{cid}').click().run()
        at.button(key='nav_History').click().run()
        at.checkbox[0].check().run()
        at.button(key=f'history_restore_{cid}').click().run()
        check(at, 'Archive and restore')
        at.button(key=f'history_open_{cid}').click().run()
        check(at, 'Open restored conversation')
    db.revoke_session(at.session_state['session_token'])
    at.run()
    check(at, 'Expired session clears private state')
    assert not at.session_state['ephemeral_messages']
    at.text_input(key='auth_identifier').set_value('owner@example.com')
    at.text_input(key='auth_password').set_value('LocalOwner8')
    at.button(key='auth_login').click().run()
    at.button(key='logout').click().run()
    check(at, 'Logout')
    assert at.text_input(key='auth_identifier')
print('UI workflow tests passed.')
