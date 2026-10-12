from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from .config import settings
from .domains import DOMAIN_NAMES, LANGUAGES, MODES, PRIVACY_MODES, ROLES
from .security import hash_password, hash_session_token, new_session_token, validate_password_strength, verify_password


@contextmanager
def connect():
    conn = sqlite3.connect(settings.db_path, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_column_if_missing(conn: sqlite3.Connection, table: str, definition: str) -> None:
    name = definition.split()[0]
    if name not in _column_names(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                organization TEXT NOT NULL DEFAULT '',
                department TEXT NOT NULL DEFAULT '',
                grade_level TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                approved INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                last_login REAL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                domain TEXT NOT NULL,
                workspace TEXT NOT NULL DEFAULT 'General',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                mode TEXT,
                attachment_json TEXT,
                sources_json TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ready',
                domain TEXT NOT NULL DEFAULT 'General Intelligence',
                visibility TEXT NOT NULL DEFAULT 'private',
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                page INTEGER,
                section TEXT,
                text TEXT NOT NULL,
                embedding_json TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS preferences (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'English',
                domain TEXT NOT NULL DEFAULT 'General Intelligence',
                model TEXT NOT NULL DEFAULT 'zoderise:latest',
                mode TEXT NOT NULL DEFAULT 'Chat',
                animation TEXT NOT NULL DEFAULT 'Balanced',
                reduced_motion INTEGER NOT NULL DEFAULT 0,
                privacy_mode TEXT NOT NULL DEFAULT 'Ephemeral',
                detail_level TEXT NOT NULL DEFAULT 'Balanced',
                deployment_profile TEXT NOT NULL DEFAULT 'School',
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER,
                action TEXT NOT NULL,
                metadata_json TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                conversation_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL,
                UNIQUE(user_id, message_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS saved_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_document_ids TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                identifier_hash TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL DEFAULT 0,
                blocked_until REAL NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, expires_at);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, archived, pinned, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_chunks_user_doc ON chunks(user_id, document_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_saved_outputs_user ON saved_outputs(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_login_attempts_updated ON login_attempts(updated_at);
            """
        )

        # Backward-compatible migration from ZODERISE Horizon V6.
        for definition in [
            "organization TEXT NOT NULL DEFAULT ''",
            "department TEXT NOT NULL DEFAULT ''",
            "grade_level TEXT NOT NULL DEFAULT ''",
            "approved INTEGER NOT NULL DEFAULT 1",
        ]:
            _add_column_if_missing(conn, "users", definition)
        _add_column_if_missing(conn, "conversations", "workspace TEXT NOT NULL DEFAULT 'General'")
        for definition in [
            "domain TEXT NOT NULL DEFAULT 'General Intelligence'",
            "visibility TEXT NOT NULL DEFAULT 'private'",
            "tags_json TEXT NOT NULL DEFAULT '[]'",
        ]:
            _add_column_if_missing(conn, "documents", definition)
        for definition in [
            f"privacy_mode TEXT NOT NULL DEFAULT '{settings.default_privacy_mode if settings.default_privacy_mode in PRIVACY_MODES else 'Ephemeral'}'",
            "detail_level TEXT NOT NULL DEFAULT 'Balanced'",
            "deployment_profile TEXT NOT NULL DEFAULT 'School'",
        ]:
            _add_column_if_missing(conn, "preferences", definition)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_visibility ON documents(visibility, created_at DESC)")
        # Normalize legacy V6 values so upgraded installations do not silently fall back.
        conn.execute("UPDATE users SET role='student' WHERE role='user'")
        domain_map = {
            'General Knowledge': 'General Intelligence',
            'Advanced Technology & CS': 'Computer Science',
            'Physics & Science': 'Physics',
            'Geography & History': 'Geography',
            'Cybersecurity & Hacking': 'Cybersecurity',
        }
        for old, new in domain_map.items():
            conn.execute("UPDATE preferences SET domain=? WHERE domain=?", (new, old))
            conn.execute("UPDATE conversations SET domain=? WHERE domain=?", (new, old))
            conn.execute("UPDATE documents SET domain=? WHERE domain=?", (new, old))
        conn.commit()


def audit(actor_user_id: Optional[int], action: str, metadata: Optional[dict[str, Any]] = None) -> None:
    payload = json.dumps(metadata or {}, ensure_ascii=False)
    with connect() as conn:
        conn.execute(
            "INSERT INTO audit_logs(actor_user_id,action,metadata_json,created_at) VALUES(?,?,?,?)",
            (actor_user_id, action[:120], payload[:20_000], time.time()),
        )
        conn.commit()


def cleanup_maintenance() -> dict[str, int]:
    now = time.time()
    cutoff = now - settings.audit_retention_days * 86400
    with connect() as conn:
        s = conn.execute("DELETE FROM sessions WHERE revoked=1 OR expires_at<=?", (now,)).rowcount
        a = conn.execute("DELETE FROM audit_logs WHERE created_at<?", (cutoff,)).rowcount
        l = conn.execute("DELETE FROM login_attempts WHERE updated_at<? AND blocked_until<?", (now - 86400, now)).rowcount
        conn.commit()
    return {"sessions": max(0, int(s)), "audit_logs": max(0, int(a)), "login_attempts": max(0, int(l))}


def ensure_admin() -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    ok, _ = validate_password_strength(settings.admin_password)
    if not ok:
        # Do not create a weak bootstrap account.
        return
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE lower(email)=?", (settings.admin_email,)).fetchone()
        if row:
            return
        username = re.sub(r"[^a-z0-9_]+", "_", settings.admin_username)[:24] or "admin"
        base = username
        suffix = 1
        while conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            suffix += 1
            username = f"{base[:24 - len(str(suffix))]}{suffix}"
        now = time.time()
        cur = conn.execute(
            """
            INSERT INTO users(name,username,email,password_hash,role,is_active,approved,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (settings.admin_name, username, settings.admin_email, hash_password(settings.admin_password), "admin", 1, 1, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO preferences(user_id,model,privacy_mode) VALUES(?,?,?)",
            (cur.lastrowid, settings.text_model, settings.default_privacy_mode),
        )
        conn.commit()


def register_user(
    name: str,
    username: str,
    email: str,
    password: str,
    organization: str = "",
    department: str = "",
    grade_level: str = "",
) -> tuple[bool, str]:
    if not settings.enable_registration:
        return False, "Self-registration is disabled by the administrator."
    name = name.strip()
    username = username.strip().lower()
    email = email.strip().lower()
    if not 2 <= len(name) <= 80:
        return False, "Enter a valid full name."
    if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
        return False, "Username must be 3–24 characters using letters, numbers, or underscore."
    if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Enter a valid email address."
    valid, message = validate_password_strength(password)
    if not valid:
        return False, message
    role = settings.default_role if settings.default_role in ROLES else "student"
    approved = 0 if settings.require_admin_approval else 1
    first_account = False
    try:
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            first_account = int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]) == 0
            if first_account:
                role = "admin"
                approved = 1
            cur = conn.execute(
                """
                INSERT INTO users(
                    name,username,email,password_hash,role,organization,department,grade_level,is_active,approved,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    name,
                    username,
                    email,
                    hash_password(password),
                    role,
                    organization.strip()[:120],
                    department.strip()[:120],
                    grade_level.strip()[:40],
                    1,
                    approved,
                    time.time(),
                ),
            )
            conn.execute(
                "INSERT INTO preferences(user_id,model,privacy_mode) VALUES(?,?,?)",
                (cur.lastrowid, settings.text_model, settings.default_privacy_mode),
            )
            conn.commit()
            user_id = int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return False, "That username or email is already registered."
    audit(user_id, "registration", {"approved": bool(approved)})
    if first_account:
        return True, "First local account created as administrator. You can sign in."
    if approved:
        return True, "Account created. You can sign in."
    return True, "Account created and is waiting for administrator approval."


def _login_key(identifier: str) -> str:
    import hashlib
    normalized = identifier.strip().lower()
    with connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE lower(email)=? OR lower(username)=?", (normalized, normalized)).fetchone()
    identity = f"user:{row['id']}" if row else normalized
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def login_blocked(identifier: str) -> tuple[bool, int]:
    if not identifier.strip():
        return False, 0
    now = time.time()
    key = _login_key(identifier)
    with connect() as conn:
        row = conn.execute("SELECT attempts,blocked_until FROM login_attempts WHERE identifier_hash=?", (key,)).fetchone()
        if not row:
            return False, 0
        blocked_until = float(row["blocked_until"] or 0)
        if blocked_until > now:
            return True, max(1, int(blocked_until - now) + 1)
        if blocked_until:
            conn.execute("DELETE FROM login_attempts WHERE identifier_hash=?", (key,))
            conn.commit()
    return False, 0


def record_login_failure(identifier: str) -> None:
    if not identifier.strip():
        return
    now = time.time()
    key = _login_key(identifier)
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT attempts FROM login_attempts WHERE identifier_hash=?", (key,)).fetchone()
        attempts = int(row["attempts"] if row else 0) + 1
        blocked_until = now + settings.login_lock_seconds if attempts >= settings.login_max_attempts else 0.0
        stored_attempts = 0 if blocked_until else attempts
        conn.execute(
            "INSERT INTO login_attempts(identifier_hash,attempts,blocked_until,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(identifier_hash) DO UPDATE SET attempts=excluded.attempts,blocked_until=excluded.blocked_until,updated_at=excluded.updated_at",
            (key, stored_attempts, blocked_until, now),
        )
        conn.commit()


def clear_login_failures(identifier: str) -> None:
    if not identifier.strip():
        return
    with connect() as conn:
        conn.execute("DELETE FROM login_attempts WHERE identifier_hash=?", (_login_key(identifier),))
        conn.commit()


def authenticate(identifier: str, password: str):
    identifier = identifier.strip().lower()
    if not identifier:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM users
            WHERE (lower(email)=? OR lower(username)=?) AND is_active=1 AND approved=1
            """,
            (identifier, identifier),
        ).fetchone()
        if not row:
            return None
        valid, needs_rehash = verify_password(password, row["password_hash"])
        if not valid:
            return None
        if needs_rehash:
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(password), row["id"]))
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (time.time(), row["id"]))
        conn.commit()
        refreshed = conn.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
    audit(int(refreshed["id"]), "login")
    return refreshed


def create_session(user_id: int) -> str:
    raw, token_hash = new_session_token()
    now = time.time()
    expires = now + settings.session_hours * 3600
    with connect() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE user_id=? AND (revoked=1 OR expires_at<=?)",
            (user_id, now),
        )
        rows = conn.execute(
            "SELECT id FROM sessions WHERE user_id=? AND revoked=0 AND expires_at>? ORDER BY created_at DESC",
            (user_id, now),
        ).fetchall()
        if len(rows) >= settings.max_active_sessions:
            old = rows[settings.max_active_sessions - 1 :]
            if old:
                conn.executemany("UPDATE sessions SET revoked=1 WHERE id=?", [(r["id"],) for r in old])
        conn.execute(
            "INSERT INTO sessions(user_id,token_hash,created_at,expires_at,revoked) VALUES(?,?,?,?,0)",
            (user_id, token_hash, now, expires),
        )
        conn.commit()
    return raw


def revoke_session(raw: str) -> None:
    if not raw:
        return
    with connect() as conn:
        conn.execute("UPDATE sessions SET revoked=1 WHERE token_hash=?", (hash_session_token(raw),))
        conn.commit()


def revoke_all_sessions(user_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (user_id,))
        conn.commit()


def current_user_from_token(raw: str | None):
    if not raw:
        return None
    with connect() as conn:
        return conn.execute(
            """
            SELECT u.* FROM users u
            JOIN sessions s ON s.user_id=u.id
            WHERE s.token_hash=? AND s.revoked=0 AND s.expires_at>? AND u.is_active=1 AND u.approved=1
            """,
            (hash_session_token(raw), time.time()),
        ).fetchone()


def change_password(user_id: int, current_password: str, new_password: str) -> tuple[bool, str]:
    valid_strength, msg = validate_password_strength(new_password)
    if not valid_strength:
        return False, msg
    with connect() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id=? AND is_active=1", (user_id,)).fetchone()
        if not row:
            return False, "Account not found."
        valid, _ = verify_password(current_password, row["password_hash"])
        if not valid:
            return False, "Current password is incorrect."
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_password), user_id))
        conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (user_id,))
        conn.commit()
    audit(user_id, "password_changed")
    return True, "Password changed. Sign in again."


def get_preferences(user_id: int):
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO preferences(user_id,model,privacy_mode) VALUES(?,?,?)",
            (user_id, settings.text_model, settings.default_privacy_mode),
        )
        conn.commit()
        return conn.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,)).fetchone()


def update_preferences(user_id: int, **kwargs: Any) -> None:
    allowed = {
        "language",
        "domain",
        "model",
        "mode",
        "animation",
        "reduced_motion",
        "privacy_mode",
        "detail_level",
        "deployment_profile",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    if "language" in fields and fields["language"] not in LANGUAGES:
        fields.pop("language")
    if "domain" in fields and fields["domain"] not in DOMAIN_NAMES:
        fields.pop("domain")
    if "mode" in fields and fields["mode"] not in MODES:
        fields.pop("mode")
    if "privacy_mode" in fields and fields["privacy_mode"] not in PRIVACY_MODES:
        fields.pop("privacy_mode")
    if not fields:
        return
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO preferences(user_id,model,privacy_mode) VALUES(?,?,?)",
            (user_id, settings.text_model, settings.default_privacy_mode),
        )
        setters = ", ".join(f"{key}=?" for key in fields)
        conn.execute(f"UPDATE preferences SET {setters} WHERE user_id=?", [*fields.values(), user_id])
        conn.commit()


def list_conversations(user_id: int, include_archived: bool = False):
    sql = "SELECT * FROM conversations WHERE user_id=?"
    args: list[Any] = [user_id]
    if not include_archived:
        sql += " AND archived=0"
    sql += " ORDER BY pinned DESC, updated_at DESC"
    with connect() as conn:
        return conn.execute(sql, args).fetchall()


def create_conversation(user_id: int, title: str, domain: str, workspace: str = "General") -> int:
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO conversations(user_id,title,domain,workspace,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (user_id, (title.strip() or "New Chat")[:120], domain, workspace[:80], now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_conversation(user_id: int, conversation_id: int):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)
        ).fetchone()


def get_messages(user_id: int, conversation_id: int, limit: int | None = None):
    sql = """
        SELECT m.* FROM messages m
        JOIN conversations c ON c.id=m.conversation_id
        WHERE m.conversation_id=? AND c.user_id=?
        ORDER BY m.created_at ASC
    """
    args: list[Any] = [conversation_id, user_id]
    if limit is not None:
        sql = f"SELECT * FROM ({sql}) ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, args).fetchall()
        if limit is not None:
            rows = list(reversed(rows))
        return rows


def save_message(
    user_id: int,
    conversation_id: int,
    role: str,
    content: str,
    model: str = "",
    mode: str = "Chat",
    attachments: Optional[list[dict[str, Any]]] = None,
    sources: Optional[list[dict[str, Any]]] = None,
) -> int:
    if role not in {"user", "assistant"}:
        raise ValueError("Invalid message role")
    if not get_conversation(user_id, conversation_id):
        raise PermissionError("Conversation access denied")
    now = time.time()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages(conversation_id,role,content,model,mode,attachment_json,sources_json,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                conversation_id,
                role,
                content,
                model,
                mode,
                json.dumps(attachments or [], ensure_ascii=False),
                json.dumps(sources or [], ensure_ascii=False),
                now,
            ),
        )
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
        conn.commit()
        return int(cur.lastrowid)


def rename_conversation(user_id: int, conversation_id: int, title: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE conversations SET title=?,updated_at=? WHERE id=? AND user_id=?",
            ((title.strip() or "New Chat")[:120], time.time(), conversation_id, user_id),
        )
        conn.commit()


def save_exchange(user_id: int, conversation_id: int | None, question: str, answer: str, *, domain: str, workspace: str, model: str, mode: str, attachments: list, sources: list) -> int:
    """Commit a complete successful exchange atomically; failed inference saves no turn."""
    now = time.time()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conversation_id is None:
            cur = conn.execute("INSERT INTO conversations(user_id,title,domain,workspace,created_at,updated_at) VALUES(?,?,?,?,?,?)", (user_id, question[:72], domain, workspace[:80], now, now))
            conversation_id = int(cur.lastrowid)
        elif not conn.execute("SELECT id FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)).fetchone():
            raise PermissionError("Conversation access denied")
        for offset, (role, content, files) in enumerate((("user", question, attachments), ("assistant", answer, []))):
            conn.execute("INSERT INTO messages(conversation_id,role,content,model,mode,attachment_json,sources_json,created_at) VALUES(?,?,?,?,?,?,?,?)", (conversation_id, role, content, model, mode, json.dumps(files, ensure_ascii=False), json.dumps(sources, ensure_ascii=False), now + offset * 0.000001))
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
        conn.commit()
    return conversation_id


def set_conversation_flag(user_id: int, conversation_id: int, flag: str, value: bool) -> None:
    if flag not in {"pinned", "archived"}:
        raise ValueError("Unsupported conversation flag")
    with connect() as conn:
        conn.execute(
            f"UPDATE conversations SET {flag}=?,updated_at=? WHERE id=? AND user_id=?",
            (int(value), time.time(), conversation_id, user_id),
        )
        conn.commit()


def delete_conversation(user_id: int, conversation_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id))
        conn.commit()


def purge_chat_history(user_id: int) -> int:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM conversations WHERE user_id=?", (user_id,)).fetchone()["c"]
        conn.execute("DELETE FROM conversations WHERE user_id=?", (user_id,))
        conn.commit()
        return int(count)


def list_documents(user_id: int, include_shared: bool = True):
    with connect() as conn:
        if include_shared:
            return conn.execute(
                """
                SELECT d.*, u.name AS owner_name
                FROM documents d JOIN users u ON u.id=d.user_id
                WHERE d.user_id=? OR d.visibility='shared'
                ORDER BY CASE WHEN d.user_id=? THEN 0 ELSE 1 END, d.created_at DESC
                """,
                (user_id, user_id),
            ).fetchall()
        return conn.execute(
            """
            SELECT d.*, u.name AS owner_name
            FROM documents d JOIN users u ON u.id=d.user_id
            WHERE d.user_id=? ORDER BY d.created_at DESC
            """,
            (user_id,),
        ).fetchall()


def get_document_for_access(user_id: int, document_id: int):
    with connect() as conn:
        return conn.execute(
            """
            SELECT d.*, u.name AS owner_name
            FROM documents d JOIN users u ON u.id=d.user_id
            WHERE d.id=? AND (d.user_id=? OR d.visibility='shared')
            """,
            (document_id, user_id),
        ).fetchone()


def insert_document_record(
    user_id: int,
    filename: str,
    stored_path: str,
    mime_type: str,
    size_bytes: int,
    checksum: str,
    extracted_text: str,
    status: str,
    domain: str,
    visibility: str,
    tags: Sequence[str],
) -> int:
    with connect() as conn:
        if visibility == "shared":
            require_admin(conn, user_id)
        cur = conn.execute(
            """
            INSERT INTO documents(
                user_id,filename,stored_path,mime_type,size_bytes,checksum,extracted_text,status,domain,visibility,tags_json,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                filename[:180],
                stored_path,
                mime_type[:120],
                size_bytes,
                checksum,
                extracted_text[:2_000_000],
                status,
                domain,
                visibility,
                json.dumps(list(tags)[:20], ensure_ascii=False),
                time.time(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_document_status(document_id: int, status: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE documents SET status=? WHERE id=?", (status[:40], document_id))
        conn.commit()


def insert_chunks(user_id: int, document_id: int, chunks: Sequence[tuple[Optional[int], str, str, Optional[str]]]) -> None:
    now = time.time()
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO chunks(document_id,user_id,page,section,text,embedding_json,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            [(document_id, user_id, page, section, text, embedding, now) for page, section, text, embedding in chunks],
        )
        conn.commit()


def find_duplicate_document(user_id: int, checksum: str):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM documents WHERE user_id=? AND checksum=? ORDER BY created_at DESC LIMIT 1",
            (user_id, checksum),
        ).fetchone()


def delete_document(user_id: int, document_id: int, is_admin: bool = False) -> Optional[str]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not row:
            return None
        if int(row["user_id"]) != user_id:
            require_admin(conn, user_id)
        conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
        conn.commit()
        return str(row["stored_path"])


def get_retrieval_rows(user_id: int, document_ids: Optional[Sequence[int]] = None):
    sql = """
        SELECT c.id,c.document_id,c.user_id,c.page,c.section,c.text,c.embedding_json,
               d.filename,d.visibility,d.domain,d.user_id AS document_owner_id
        FROM chunks c JOIN documents d ON d.id=c.document_id
        WHERE (d.user_id=? OR d.visibility='shared') AND d.status='ready'
    """
    args: list[Any] = [user_id]
    if document_ids is not None:
        if not document_ids:
            return []
        marks = ",".join("?" for _ in document_ids)
        sql += f" AND d.id IN ({marks})"
        args.extend(int(x) for x in document_ids)
    sql += " ORDER BY d.created_at DESC, c.id ASC LIMIT ?"
    args.append(settings.max_retrieval_chunks)
    with connect() as conn:
        return conn.execute(sql, args).fetchall()


def list_users():
    with connect() as conn:
        return conn.execute(
            """
            SELECT id,name,username,email,role,organization,department,grade_level,is_active,approved,created_at,last_login
            FROM users ORDER BY created_at DESC
            """
        ).fetchall()


def list_active_sessions():
    """Summarize signed-in sessions for the administrator without exposing tokens."""
    now = time.time()
    with connect() as conn:
        return conn.execute(
            """
            SELECT s.id,s.created_at,s.expires_at,u.id AS user_id,u.name,u.username,u.role
            FROM sessions s JOIN users u ON u.id=s.user_id
            WHERE s.revoked=0 AND s.expires_at>?
            ORDER BY s.created_at DESC
            """,
            (now,),
        ).fetchall()


def admin_revoke_session(actor_user_id: int, session_id: int) -> None:
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_admin(conn, actor_user_id)
        row = conn.execute("SELECT user_id FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row:
            conn.execute("UPDATE sessions SET revoked=1 WHERE id=?", (session_id,))
        conn.commit()
    if row:
        audit(actor_user_id, "admin_revoke_session", {"session_id": session_id, "target_user_id": int(row["user_id"])})


def require_admin(conn: sqlite3.Connection, user_id: int) -> None:
    row = conn.execute("SELECT 1 FROM users WHERE id=? AND role='admin' AND is_active=1 AND approved=1", (user_id,)).fetchone()
    if not row:
        raise PermissionError("Administrator access required.")


def protect_last_admin(conn: sqlite3.Connection, user_id: int) -> None:
    row = conn.execute("SELECT role,is_active,approved FROM users WHERE id=?", (user_id,)).fetchone()
    if row and row["role"] == "admin" and row["is_active"] and row["approved"]:
        count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1 AND approved=1").fetchone()[0]
        if count <= 1:
            raise ValueError("Keep at least one active, approved administrator.")


def admin_update_user(actor_user_id: int, target_user_id: int, *, role: Optional[str] = None, active: Optional[bool] = None, approved: Optional[bool] = None) -> None:
    if role is not None and role not in ROLES:
        raise ValueError("Invalid role")
    sets: list[str] = []
    values: list[Any] = []
    if role is not None:
        sets.append("role=?")
        values.append(role)
    if active is not None:
        sets.append("is_active=?")
        values.append(int(active))
    if approved is not None:
        sets.append("approved=?")
        values.append(int(approved))
    if not sets:
        return
    values.append(target_user_id)
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_admin(conn, actor_user_id)
        if role not in {None, "admin"} or active is False or approved is False:
            protect_last_admin(conn, target_user_id)
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", values)
        if active is False or approved is False or role is not None:
            conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (target_user_id,))
        conn.commit()
    audit(actor_user_id, "admin_update_user", {"target_user_id": target_user_id, "role": role, "active": active, "approved": approved})


def admin_delete_user(actor_user_id: int, target_user_id: int) -> tuple[bool, str]:
    if actor_user_id == target_user_id:
        return False, "You cannot delete your own administrator account from this screen."
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_admin(conn, actor_user_id)
        row = conn.execute("SELECT id,name,role FROM users WHERE id=?", (target_user_id,)).fetchone()
        if not row:
            return False, "User account not found."
        if row["role"] == "admin":
            return False, "Administrator accounts must be demoted before deletion."
        conn.execute("DELETE FROM users WHERE id=?", (target_user_id,))
        conn.commit()
    audit(actor_user_id, "admin_delete_user", {"target_user_id": target_user_id})
    return True, f"Deleted {row['name']}."


def dashboard_stats() -> dict[str, int]:
    with connect() as conn:
        return {
            "users": int(conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]),
            "active_users": int(conn.execute("SELECT COUNT(*) c FROM users WHERE is_active=1 AND approved=1").fetchone()["c"]),
            "conversations": int(conn.execute("SELECT COUNT(*) c FROM conversations").fetchone()["c"]),
            "messages": int(conn.execute("SELECT COUNT(*) c FROM messages").fetchone()["c"]),
            "documents": int(conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]),
            "shared_documents": int(conn.execute("SELECT COUNT(*) c FROM documents WHERE visibility='shared'").fetchone()["c"]),
        }


def recent_audit(limit: int = 100):
    with connect() as conn:
        return conn.execute(
            """
            SELECT a.*, u.name AS actor_name, u.username AS actor_username
            FROM audit_logs a LEFT JOIN users u ON u.id=a.actor_user_id
            ORDER BY a.created_at DESC LIMIT ?
            """,
            (max(1, min(limit, 500)),),
        ).fetchall()


def add_bookmark(user_id: int, conversation_id: int, message_id: int, note: str = "") -> bool:
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO bookmarks(user_id,conversation_id,message_id,note,created_at) VALUES(?,?,?,?,?)",
                (user_id, conversation_id, message_id, note[:1000], time.time()),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def list_bookmarks(user_id: int):
    with connect() as conn:
        return conn.execute(
            """
            SELECT b.*, m.content, m.role, c.title AS conversation_title
            FROM bookmarks b
            JOIN messages m ON m.id=b.message_id
            JOIN conversations c ON c.id=b.conversation_id
            WHERE b.user_id=? ORDER BY b.created_at DESC
            """,
            (user_id,),
        ).fetchall()


def remove_bookmark(user_id: int, bookmark_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM bookmarks WHERE id=? AND user_id=?", (bookmark_id, user_id))
        conn.commit()


def save_output(user_id: int, kind: str, title: str, content: str, source_document_ids: Sequence[int] = ()) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO saved_outputs(user_id,kind,title,content,source_document_ids,created_at) VALUES(?,?,?,?,?,?)",
            (
                user_id,
                kind[:40],
                title[:160],
                content,
                json.dumps([int(x) for x in source_document_ids]),
                time.time(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_saved_outputs(user_id: int, limit: int = 50):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM saved_outputs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, max(1, min(limit, 200))),
        ).fetchall()


def delete_saved_output(user_id: int, output_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM saved_outputs WHERE id=? AND user_id=?", (output_id, user_id))
        conn.commit()


def compact_database() -> None:
    with connect() as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")


def collect_chat_attachments(user_id: int, conversation_id: Optional[int] = None) -> list[dict[str, Any]]:
    sql = """
        SELECT m.attachment_json FROM messages m
        JOIN conversations c ON c.id=m.conversation_id
        WHERE c.user_id=?
    """
    args: list[Any] = [user_id]
    if conversation_id is not None:
        sql += " AND c.id=?"
        args.append(conversation_id)
    with connect() as conn:
        rows = conn.execute(sql, args).fetchall()
    attachments: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = json.loads(row["attachment_json"] or "[]")
        except Exception:
            value = []
        if isinstance(value, dict):
            value = [value]
        if isinstance(value, list):
            attachments.extend(x for x in value if isinstance(x, dict))
    return attachments


def delete_account_records(user_id: int) -> None:
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        protect_last_admin(conn, user_id)
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()


def update_user_profile(user_id: int, *, name: str, organization: str, department: str, grade_level: str) -> tuple[bool, str]:
    name = name.strip()
    if not 2 <= len(name) <= 80:
        return False, "Enter a valid name."
    with connect() as conn:
        conn.execute(
            "UPDATE users SET name=?,organization=?,department=?,grade_level=? WHERE id=?",
            (name, organization.strip()[:120], department.strip()[:120], grade_level.strip()[:40], user_id),
        )
        conn.commit()
    audit(user_id, "profile_updated")
    return True, "Profile updated."
