"""Verified local archive of an online SQLite snapshot and uploaded files."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import time
import zipfile
from contextlib import closing
from pathlib import Path

from zoderise.config import settings


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_backup(path: Path) -> dict:
    """Read every archive entry and compare it with its recorded SHA-256 digest."""
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "zoderise-backup-v1":
            raise ValueError("Unknown Zoderise backup format")
        expected = manifest["files"]
        if set(archive.namelist()) != set(expected) | {"manifest.json"}:
            raise ValueError("Backup file list does not match its manifest")
        for name, digest in expected.items():
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("Unsafe path in backup")
            with archive.open(name) as source:
                hasher = hashlib.sha256()
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    hasher.update(chunk)
            if hasher.hexdigest() != digest:
                raise ValueError(f"Backup integrity check failed: {name}")
    return manifest


def create_backup() -> Path:
    """Snapshot SQLite online, archive current uploads, and verify the result."""
    db_path = settings.db_path
    if not db_path.is_file():
        raise FileNotFoundError("No Zoderise database exists yet")
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    destination = backup_dir / f"zoderise-{timestamp}-{os.urandom(3).hex()}.zip"
    with tempfile.TemporaryDirectory(prefix="zoderise-backup-") as temp_dir:
        snapshot = Path(temp_dir) / "zoderise.db"
        with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
        entries: dict[str, str] = {}
        try:
            with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                db_bytes = snapshot.read_bytes()
                archive.writestr("database/zoderise.db", db_bytes)
                entries["database/zoderise.db"] = _digest(db_bytes)
                if settings.storage_root.is_dir():
                    for path in settings.storage_root.rglob("*"):
                        if not path.is_file() or path.is_symlink():
                            continue
                        name = "storage/" + path.relative_to(settings.storage_root).as_posix()
                        # zipfile streams large files rather than reading them all into memory.
                        with path.open("rb") as source, archive.open(name, "w") as output:
                            hasher = hashlib.sha256()
                            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                                output.write(chunk)
                                hasher.update(chunk)
                        entries[name] = hasher.hexdigest()
                manifest = {"format": "zoderise-backup-v1", "created_at": int(time.time()), "files": entries}
                archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True))
            verify_backup(destination)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return destination
