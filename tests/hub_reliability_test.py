"""Exercise FIFO inference and verified backups with isolated data."""
import os
import tempfile
import threading
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory(prefix="zoderise-reliability-") as temp:
    os.environ["ZODERISE_DB"] = str(Path(temp) / "test.db")
    os.environ["ZODERISE_STORAGE"] = str(Path(temp) / "storage")
    from zoderise.config import settings
    from zoderise.database import init_db
    from zoderise.backup import create_backup, verify_backup
    from zoderise.inference_queue import InferenceQueue

    init_db()
    upload = settings.storage_root / "1" / "sample.txt"
    upload.parent.mkdir(parents=True, exist_ok=True)
    upload.write_text("Private classroom sample", encoding="utf-8")
    archive = create_backup()
    manifest = verify_backup(archive)
    assert "database/zoderise.db" in manifest["files"]
    assert "storage/1/sample.txt" in manifest["files"]
    print("PASS: SQLite and uploaded file backup verified")

    queue = InferenceQueue(max_waiting=2, wait_seconds=2)
    sequence = []
    release = threading.Event()
    first_entered = threading.Event()

    def first():
        with queue.slot(1):
            sequence.append(1)
            first_entered.set()
            release.wait(2)

    def second():
        with queue.slot(2):
            sequence.append(2)

    a = threading.Thread(target=first)
    b = threading.Thread(target=second)
    a.start()
    assert first_entered.wait(1)
    b.start()
    for _ in range(100):
        if queue.snapshot()["waiting"] == 1:
            break
        time.sleep(.01)
    assert queue.snapshot() == {"busy": True, "waiting": 1}
    try:
        with queue.slot(2):
            raise AssertionError("Duplicate user request should not enter")
    except RuntimeError:
        pass
    release.set()
    a.join(2)
    b.join(2)
    assert sequence == [1, 2] and not queue.snapshot()["busy"]
    print("PASS: second user waited and duplicate user request was rejected")
