"""Isolated regression suite. Never opens the user's application database."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP = tempfile.TemporaryDirectory()
os.environ.update(ZODERISE_DB=str(Path(TMP.name)/'test.db'), ZODERISE_STORAGE=str(Path(TMP.name)/'storage'), ZODERISE_ADMIN_EMAIL='', ZODERISE_ADMIN_PASSWORD='')
from zoderise import database as db
from zoderise import documents as docs
from zoderise import ai
from zoderise.security import hash_password, verify_password
from zoderise.local_tools import safe_calculate
from zoderise.config import is_loopback_url
from zoderise.inference_queue import inference_queue
from configure_owner import provision_owner


class Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.owner = provision_owner('owner@example.com', hash_password('LocalOwner8'))
        ok, msg = db.register_user('Second User', 'second', 'second@example.com', 'Strong-Password-123!')
        assert ok, msg
        cls.member = db.authenticate('second', 'Strong-Password-123!')['id']
        cls.doc, _, _ = docs.save_document(cls.owner, 'physics.txt', b'Pascal pressure in a liquid is transmitted equally.', 'text/plain', domain='Physics')

    def test_owner_login(self):
        self.assertEqual(db.authenticate('owner@example.com', 'LocalOwner8')['role'], 'admin')
        self.assertIsNone(db.authenticate('owner@example.com', 'wrong'))

    def test_salted_hash(self):
        a,b = hash_password('Example123'), hash_password('Example123')
        self.assertNotEqual(a,b)
        self.assertTrue(verify_password('Example123', a)[0])

    def test_no_match_returns_no_evidence(self):
        self.assertEqual(docs.retrieve_chunks(self.owner, 'astronaut galaxy'), [])
        self.assertEqual(docs.retrieve_ephemeral('astronaut', [{'text':'Pascal pressure','filename':'a'}]), [])

    def test_retrieval_matches(self):
        self.assertEqual(docs.retrieve_chunks(self.owner, 'pressure')[0]['document_id'], self.doc)

    def test_private_document_isolation(self):
        self.assertEqual(docs.retrieve_chunks(self.member, 'pressure'), [])
        self.assertIsNone(db.get_document_for_access(self.member, self.doc))
        with self.assertRaises(PermissionError):
            db.delete_document(self.member, self.doc, is_admin=True)

    def test_empty_selection_does_not_search_everything(self):
        self.assertEqual(db.get_retrieval_rows(self.owner, []), [])

    def test_shared_write_requires_admin(self):
        with self.assertRaises(PermissionError):
            docs.save_document(self.member, 'shared.txt', b'Shared content', 'text/plain', domain='Physics', visibility='shared')

    def test_shared_read(self):
        document_id, _, _ = docs.save_document(self.owner, 'public.txt', b'Photosynthesis uses sunlight.', 'text/plain', domain='Biology & Health', visibility='shared')
        self.assertIsNotNone(db.get_document_for_access(self.member, document_id))

    def test_admin_mutations_require_role(self):
        with self.assertRaises(PermissionError):
            db.admin_update_user(self.member, self.member, role='admin')
        with self.assertRaises(PermissionError):
            db.admin_delete_user(self.member, self.owner)

    def test_last_admin_protected(self):
        with self.assertRaises(ValueError):
            db.admin_update_user(self.owner, self.owner, active=False)
        with self.assertRaises(ValueError):
            db.delete_account_records(self.owner)

    def test_conversation_isolation(self):
        cid = db.create_conversation(self.owner, 'Private', 'Physics')
        db.save_message(self.owner, cid, 'user', 'Secret')
        self.assertEqual(db.get_messages(self.member, cid), [])
        with self.assertRaises(PermissionError):
            db.save_message(self.member, cid, 'assistant', 'Injected')

    def test_revoked_session(self):
        token = db.create_session(self.member)
        self.assertIsNotNone(db.current_user_from_token(token))
        db.revoke_session(token)
        self.assertIsNone(db.current_user_from_token(token))

    def test_throttle(self):
        for _ in range(5): db.record_login_failure('unknown')
        self.assertTrue(db.login_blocked('unknown')[0])
        db.clear_login_failures('unknown')
        self.assertFalse(db.login_blocked('unknown')[0])

    def test_throttle_email_username_share_counter(self):
        for _ in range(5): db.record_login_failure('second')
        self.assertTrue(db.login_blocked('second@example.com')[0])
        db.clear_login_failures('second@example.com')
        self.assertFalse(db.login_blocked('second')[0])

    def test_unicode_retrieval(self):
        self.assertEqual(docs._query_terms('كتاب'), docs._query_terms('کتاب'))

    def test_calculator_resource_bounds(self):
        self.assertEqual(safe_calculate('sqrt(144)+8'), 20)
        for expression in ['((2**1000)**1000)**1000', '__import__("os")', '1e309', 'True']:
            with self.assertRaises(ValueError): safe_calculate(expression)

    def test_endpoint_validation(self):
        self.assertTrue(is_loopback_url('http://127.0.0.1:11434'))
        for endpoint in ['file://localhost/x', 'https://example.com', 'http://user:pw@localhost:11434']:
            self.assertFalse(is_loopback_url(endpoint))

    def test_upload_validation(self):
        for name, raw in [('fake.pdf', b'not pdf'), ('empty.txt', b''), ('evil.exe', b'MZ')]:
            with self.assertRaises(ValueError): docs.validate_upload(name, raw)

    def response(self, lines):
        result = MagicMock()
        result.__enter__.return_value = result
        result.is_redirect = False
        result.iter_lines.return_value = lines
        return result

    def test_stream_success(self):
        with patch.object(ai.requests, 'post', return_value=self.response([b'{"message":{"content":"Hello"},"done":false}',b'{"done":true}'])) as request:
            self.assertEqual(''.join(ai.chat_stream('model',[{'role':'user','content':'Hi'}])), 'Hello')
            self.assertEqual(request.call_args.kwargs['json']['options']['num_ctx'], 4096)

    def test_stream_failures(self):
        for lines in [[b'{"error":"out of memory"}'], [b'{"message":{"content":"partial"}}'], [b'bad json'], [b'{"done":true}']]:
            with patch.object(ai.requests,'post',return_value=self.response(lines)):
                with self.assertRaises(RuntimeError): list(ai.chat_stream('model',[{'role':'user','content':'Hi'}]))
        self.assertFalse(inference_queue.snapshot()["busy"])

    def test_context_budget(self):
        messages = [{'role':'system','content':'System'}, {'role':'user','content':'old'*4000}, {'role':'user','content':'latest'}]
        result = ai.bounded_messages(messages)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[-1]['content'], 'latest')


if __name__ == '__main__':
    unittest.main(verbosity=2)
