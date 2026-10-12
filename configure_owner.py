"""One-time local owner setup. Run from the computer that hosts Zoderise."""
import getpass
import re
import time
from zoderise.database import connect, init_db
from zoderise.security import hash_password, validate_password_strength
from zoderise.config import settings


def provision_owner(email: str, password_hash: str, name: str = "Zubair Zahidi") -> int:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid email address.")
    init_db()
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute("SELECT id FROM users WHERE lower(email)=?", (email,)).fetchone()
        if user:
            uid = int(user["id"])
            conn.execute("UPDATE users SET role='admin',is_active=1,approved=1,password_hash=? WHERE id=?", (password_hash, uid))
            conn.execute("UPDATE sessions SET revoked=1 WHERE user_id=?", (uid,))
        else:
            username = "zoderise_owner"
            n = 1
            while conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                n += 1
                username = f"zoderise_owner_{n}"
            cur = conn.execute("INSERT INTO users(name,username,email,password_hash,role,is_active,approved,created_at) VALUES(?,?,?,?,'admin',1,1,?)", (name, username, email, password_hash, time.time()))
            uid = int(cur.lastrowid)
        conn.execute("INSERT OR IGNORE INTO preferences(user_id,model,privacy_mode) VALUES(?,?,?)", (uid, settings.text_model, settings.default_privacy_mode))
        conn.commit()
        return uid


if __name__ == "__main__":
    email = input("Owner email: ").strip()
    password = getpass.getpass("Owner password (12+ characters, three character types): ")
    valid, message = validate_password_strength(password)
    if not valid:
        raise SystemExit(message)
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")
    provision_owner(email, hash_password(password))
    print("Owner configured. Sign in with the email and password you entered.")
