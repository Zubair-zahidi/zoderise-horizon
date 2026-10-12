from __future__ import annotations

import os
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["ZODERISE_DB"] = str(Path(tmp) / "test.db")
        os.environ["ZODERISE_STORAGE"] = str(Path(tmp) / "storage")
        os.environ["ZODERISE_ADMIN_EMAIL"] = ""
        os.environ["ZODERISE_ADMIN_PASSWORD"] = ""

        from zoderise.database import (
            authenticate,
            create_conversation,
            create_session,
            current_user_from_token,
            get_messages,
            init_db,
            register_user,
            save_message,
        )
        from zoderise.documents import chunk_text, validate_upload, _lexical_rank
        from zoderise.local_tools import convert_unit, safe_calculate

        init_db()
        ok, message = register_user(
            "Test Admin",
            "test_admin",
            "test@example.com",
            "Strong-Test-Password-123!",
            "Local Test",
            "QA",
            "",
        )
        assert ok, message
        user = authenticate("test_admin", "Strong-Test-Password-123!")
        assert user is not None
        assert user["role"] == "admin", "First account should become local administrator"

        token = create_session(int(user["id"]))
        assert current_user_from_token(token) is not None

        cid = create_conversation(int(user["id"]), "Smoke test", "General Intelligence")
        save_message(int(user["id"]), cid, "user", "hello")
        save_message(int(user["id"]), cid, "assistant", "hi")
        assert len(get_messages(int(user["id"]), cid)) == 2

        validate_upload("notes.txt", b"hello local knowledge")
        chunks = chunk_text("A sentence. " * 300, max_chars=200, overlap=30)
        assert len(chunks) > 1
        ranked = _lexical_rank("pascal pressure liquid", ["Pascal law explains pressure in a liquid.", "History of ancient cities."])
        assert ranked[0] > ranked[1]

        assert safe_calculate("sqrt(144) + 2^3".replace("^", "**")) == 20.0
        assert round(convert_unit("Length", 1, "km", "m"), 3) == 1000

    print("ZODERISE smoke test: OK")


if __name__ == "__main__":
    main()
