"""Regression checks for product identity and classroom workflows."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
temp = tempfile.TemporaryDirectory()
os.environ.update(ZODERISE_DB=str(Path(temp.name) / 'app.db'), ZODERISE_STORAGE=str(Path(temp.name) / 'files'), ZODERISE_ADMIN_EMAIL='', ZODERISE_ADMIN_PASSWORD='')
from zoderise.ai import build_system_prompt, bounded_messages
from zoderise.classroom import build_classroom_prompt
from zoderise import ai
from configure_owner import provision_owner
from zoderise.security import hash_password
from streamlit.testing.v1 import AppTest

prompt = build_system_prompt(domain='Mathematics', selected_language='English', mode='Chat', user_query='Who made you?')
bounded = bounded_messages([{'role':'system', 'content':prompt}, {'role':'user', 'content':'Who made you?'}])
assert 'Zubair Zahidi' in bounded[0]['content']
assert 'Kardan Private School' in bounded[0]['content']
assert 'fractions' in build_classroom_prompt('Lesson plan', 'fractions', 'Middle school', 'Dari', 40, '')
try:
    build_classroom_prompt('Lesson plan', ' ', 'Middle school', 'English', 40, '')
    raise AssertionError('Blank topic accepted')
except ValueError:
    pass
provision_owner('owner@example.com', hash_password('LocalOwner8'))
with patch.object(ai, 'ollama_online', return_value=False), patch.object(ai, 'model_status', return_value={'online':False, 'text_ready':False, 'vision_ready':False}):
    at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
    at.text_input(key='auth_identifier').set_value('owner@example.com')
    at.text_input(key='auth_password').set_value('LocalOwner8')
    at.button(key='auth_login').click().run()
    next(x for x in at.button if x.label == 'Create my starting brief').click().run()
    assert at.session_state['page'] == 'Home', 'Blank brief must stay on Home'
    at.text_input(key='home_idea').set_value('Solar energy')
    at.selectbox(key='home_goal').set_value('A practice quiz')
    next(x for x in at.button if x.label == 'Create my starting brief').click().run()
    assert not at.exception
    assert at.session_state['page'] == 'Chat'
    assert 'Solar energy' in at.chat_input[0].value
    assert 'practice quiz' in at.chat_input[0].value
    assert not at.session_state['ephemeral_messages'], 'Home brief must not auto-submit'
    at.button(key='nav_Prompt Studio').click().run()
    assert not at.exception
    next(x for x in at.text_input if x.label == 'Topic').set_value('Fractions')
    next(x for x in at.button if x.label == 'Build my brief').click().run()
    assert 'Fractions' in at.session_state['classroom_draft']
    next(x for x in at.button if x.label == 'Continue in chat').click().run()
    assert not at.exception
    assert at.session_state['page'] == 'Chat'
    assert not at.session_state['ephemeral_messages'], 'Draft should not auto-submit'
    at.button(key='nav_Settings').click().run()
    next(x for x in at.selectbox if x.label == 'Motion style').set_value('Immersive')
    at.button(key='settings_save').click().run()
    assert at.session_state['animation'] == 'Immersive'
    assert not at.exception
print('Identity, prompt studio, draft handoff, and motion preferences passed.')
