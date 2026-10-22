"""Appearance validation, atomic chat persistence, and failure recovery regressions."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ.update(ZODERISE_DB=str(Path(TEMP.name) / 'test.db'), ZODERISE_STORAGE=str(Path(TEMP.name) / 'storage'), ZODERISE_ADMIN_EMAIL='', ZODERISE_ADMIN_PASSWORD='')
from zoderise import ai, database as db
from zoderise.appearance import normalize_appearance, appearance_css, DEFAULTS
from zoderise.chat_utils import object_list
from zoderise.security import hash_password
from configure_owner import provision_owner
from streamlit.testing.v1 import AppTest


class Customization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uid = provision_owner('owner@example.com', hash_password('LocalOwner8'))

    def test_import_validation(self):
        for raw in [None, [], 'text', {'palette': ['Forest']}, {'accent': '</style><script>bad</script>'}]:
            self.assertEqual(normalize_appearance(raw), DEFAULTS)
        self.assertNotIn('script', appearance_css({'palette': 'bad<script>'}))
        self.assertEqual(normalize_appearance({'density': 'Compact', 'admin': True})['density'], 'Compact')
        self.assertNotIn('admin', normalize_appearance({'admin': True}))

    def test_atomic_exchange_and_ownership(self):
        args = dict(domain='Physics', workspace='School', model='test', mode='Chat', attachments=[], sources=[])
        cid = db.save_exchange(self.uid, None, 'Question', 'Answer', **args)
        self.assertEqual([m['role'] for m in db.get_messages(self.uid, cid)], ['user', 'assistant'])
        with self.assertRaises(PermissionError):
            db.save_exchange(self.uid + 999, cid, 'Unauthorized', 'No', **args)
        self.assertEqual(len(db.get_messages(self.uid, cid)), 2)

    def test_legacy_attachment_shapes(self):
        self.assertEqual(object_list('{"filename":"old.png"}'), [{'filename': 'old.png'}])
        self.assertEqual(object_list('[null,7,{"filename":"x"}]'), [{'filename': 'x'}])
        self.assertEqual(object_list('broken'), [])

    def test_malformed_stream_releases_lock(self):
        for message in (None, 'invalid', {'content': 42}):
            response = MagicMock()
            response.__enter__.return_value = response
            response.is_redirect = False
            response.iter_lines.return_value = [json.dumps({'message': message}).encode()]
            with patch.object(ai.requests, 'post', return_value=response):
                with self.assertRaises(RuntimeError):
                    list(ai.chat_stream('test', [{'role': 'user', 'content': 'hi'}]))
            self.assertEqual(ai.inference_queue.snapshot(), {'busy': False, 'waiting': 0})
            # A subsequent request must actually acquire the gate again.
            with ai.inference_queue.slot():
                self.assertTrue(ai.inference_queue.snapshot()['busy'])

    def test_arabic_language(self):
        self.assertEqual(ai.detect_response_language('مرحبا', 'English'), 'Arabic')
        self.assertEqual(ai.detect_response_language('سلام', 'Dari'), 'Dari')

    def test_ui_failure_recovery_and_device_isolation(self):
        # CCv2 registration belongs to the AppTest runtime, not the earlier pure-unit import.
        sys.modules.pop('zoderise.appearance', None)
        status = {'online': True, 'text_ready': True, 'vision_ready': True, 'models': ['zoderise:latest', 'zoderise-vision:latest']}
        with patch.object(ai, 'model_status', return_value=status), patch.object(ai, 'ollama_online', return_value=True), patch.object(ai, 'ollama_tags', return_value=status['models']):
            at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30).run()
            at.text_input(key='auth_identifier').set_value('owner@example.com')
            at.text_input(key='auth_password').set_value('LocalOwner8')
            at.button(key='auth_login').click().run()
            at.button(key='nav_Appearance').click().run()
            self.assertFalse(at.exception)
            at.button(key='quick_preset_Forest studio').click().run()
            self.assertEqual(at.session_state['appearance']['palette'], 'Forest')
            at.button(key='quick_motion_Immersive').click().run()
            self.assertEqual(at.session_state['appearance']['motion'], 'Immersive')
            at.button(key='quick_motion_Reduced').click().run()
            self.assertEqual(at.session_state['appearance']['motion'], 'Reduced')
            self.assertFalse(at.exception)
            at.selectbox(key='appearance_preset').set_value('Phone essentials')
            at.button(key='apply_appearance_preset').click().run()
            self.assertEqual(at.session_state['appearance']['artwork'], 'Hidden')
            # Appearance is not written to account preferences shared by other devices.
            self.assertEqual(db.get_preferences(self.uid)['animation'], 'Balanced')
            at.button(key='new_session').click().run()
            with patch.object(ai, 'chat_stream', side_effect=RuntimeError('Model busy')):
                at.chat_input[0].set_value('A request that fails').run()
                self.assertFalse(at.exception)
                self.assertEqual(at.session_state['ephemeral_messages'], [])
                self.assertEqual(at.session_state['failed_chat_prompt'], 'A request that fails')
            at.run()
            at.button(key='restore_failed_prompt').click().run()
            self.assertFalse(at.exception)
            at.session_state['privacy_mode'] = 'Persistent'
            at.run()
            before = len(db.list_conversations(self.uid))
            with patch.object(ai, 'chat_stream', side_effect=RuntimeError('Interrupted')):
                at.chat_input[0].set_value('Should not leave an empty conversation').run()
            self.assertEqual(len(db.list_conversations(self.uid)), before)
            self.assertFalse(at.exception)


if __name__ == '__main__':
    unittest.main(verbosity=2)
