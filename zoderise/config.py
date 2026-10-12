from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


BASE_DIR = Path(__file__).resolve().parent.parent


def _env_int(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_float(name: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _path_env(name: str, default: str) -> Path:
    shared_home = os.getenv("ZODERISE_DATA_HOME")
    if shared_home and name in {"ZODERISE_DB", "ZODERISE_STORAGE"} and name not in os.environ:
        default = str(Path(shared_home) / ("zoderise.db" if name == "ZODERISE_DB" else "storage"))
    raw = os.getenv(name, default)
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def is_loopback_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or not host:
            return False
        if host.lower() in {"localhost", "localhost.localdomain"}:
            return True
        ip = ipaddress.ip_address(host)
        return ip.is_loopback
    except Exception:
        return False


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("ZODERISE_APP_NAME", "ZODERISE")
    app_version: str = os.getenv("ZODERISE_APP_VERSION", "8.2.0-HORIZON")
    app_tagline: str = os.getenv("ZODERISE_TAGLINE", "Sovereign Local Intelligence")

    db_path: Path = _path_env("ZODERISE_DB", "data/zoderise.db")
    storage_root: Path = _path_env("ZODERISE_STORAGE", "data/storage")

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    text_model: str = os.getenv("ZODERISE_TEXT_MODEL", "zoderise:latest")
    vision_model: str = os.getenv("ZODERISE_VISION_MODEL", "zoderise-vision:latest")
    allow_nonlocal_ollama: bool = _env_bool("ALLOW_NONLOCAL_OLLAMA", False)

    server_host: str = os.getenv("SERVER_HOST", "127.0.0.1")
    server_port: int = _env_int("SERVER_PORT", 8501, 1, 65535)

    max_upload_mb: int = _env_int("MAX_UPLOAD_MB", 25, 1, 250)
    max_chat_attachments: int = _env_int("ZODERISE_MAX_CHAT_ATTACHMENTS", 4, 1, 12)
    max_chat_total_mb: int = _env_int("ZODERISE_MAX_CHAT_TOTAL_MB", 50, 1, 500)
    max_pdf_pages: int = _env_int("ZODERISE_MAX_PDF_PAGES", 300, 1, 2000)
    max_image_pixels: int = _env_int("ZODERISE_MAX_IMAGE_PIXELS", 25_000_000, 1_000_000, 200_000_000)
    max_docx_uncompressed_mb: int = _env_int("ZODERISE_MAX_DOCX_UNCOMPRESSED_MB", 100, 5, 1000)

    max_context_messages: int = _env_int("MAX_CONTEXT_MESSAGES", 16, 2, 80)
    max_history_message_chars: int = _env_int("ZODERISE_MAX_HISTORY_MESSAGE_CHARS", 5000, 500, 50_000)
    max_prompt_chars: int = _env_int("MAX_PROMPT_CHARS", 16_000, 1000, 100_000)
    max_rag_context_chars: int = _env_int("ZODERISE_MAX_RAG_CONTEXT_CHARS", 14_000, 2000, 100_000)

    rag_top_k: int = _env_int("RAG_TOP_K", 6, 1, 20)
    rag_chunk_size: int = _env_int("RAG_CHUNK_SIZE", 1400, 400, 5000)
    rag_chunk_overlap: int = _env_int("RAG_CHUNK_OVERLAP", 220, 0, 1500)
    rag_similarity_threshold: float = _env_float("RAG_SIMILARITY_THRESHOLD", 0.15, -1.0, 1.0)
    max_retrieval_chunks: int = _env_int("ZODERISE_MAX_RETRIEVAL_CHUNKS", 8000, 100, 100_000)

    connect_timeout: float = _env_float("OLLAMA_CONNECT_TIMEOUT", 3.0, 0.5, 60.0)
    read_timeout: float = _env_float("OLLAMA_READ_TIMEOUT", 600.0, 10.0, 3600.0)
    keep_alive: str = os.getenv("ZODERISE_KEEP_ALIVE", "3m")
    ai_temperature: float = _env_float("AI_TEMPERATURE", 0.2, 0.0, 2.0)
    ai_num_predict: int = _env_int("AI_NUM_PREDICT", 2048, 128, 16_384)

    ai_num_ctx: int = _env_int("AI_NUM_CTX", 4096, 2048, 32768)
    ai_num_batch: int = _env_int("AI_NUM_BATCH", 128, 32, 512)
    ai_input_chars: int = _env_int("AI_INPUT_CHARS", 8500, 3000, 60000)

    session_hours: int = _env_int("SESSION_HOURS", 12, 1, 168)
    max_active_sessions: int = _env_int("ZODERISE_MAX_ACTIVE_SESSIONS", 8, 1, 64)
    login_max_attempts: int = _env_int("ZODERISE_LOGIN_MAX_ATTEMPTS", 5, 3, 20)
    login_lock_seconds: int = _env_int("ZODERISE_LOGIN_LOCK_SECONDS", 60, 15, 3600)
    audit_retention_days: int = _env_int("ZODERISE_AUDIT_RETENTION_DAYS", 90, 7, 3650)

    ocr_lang: str = os.getenv("ZODERISE_OCR_LANG", "eng+fas+pus")
    default_privacy_mode: str = os.getenv("ZODERISE_DEFAULT_PRIVACY_MODE", "Ephemeral")
    default_role: str = os.getenv("ZODERISE_DEFAULT_ROLE", "student")

    admin_name: str = os.getenv("ZODERISE_ADMIN_NAME", "ZODERISE Administrator").strip()
    admin_username: str = os.getenv("ZODERISE_ADMIN_USERNAME", "admin").strip().lower()
    admin_email: str = os.getenv("ZODERISE_ADMIN_EMAIL", "").strip().lower()
    admin_password: str = os.getenv("ZODERISE_ADMIN_PASSWORD", "")

    enable_registration: bool = _env_bool("ZODERISE_ENABLE_REGISTRATION", True)
    require_admin_approval: bool = _env_bool("ZODERISE_REQUIRE_ADMIN_APPROVAL", False)


settings = Settings()
settings.db_path.parent.mkdir(parents=True, exist_ok=True)
settings.storage_root.mkdir(parents=True, exist_ok=True)


def security_configuration_issues() -> list[str]:
    issues: list[str] = []
    if not settings.allow_nonlocal_ollama and not is_loopback_url(settings.ollama_base_url):
        issues.append(
            "OLLAMA_BASE_URL is not loopback. ZODERISE blocks non-local inference by default. "
            "Use 127.0.0.1/localhost or explicitly set ALLOW_NONLOCAL_OLLAMA=1 for a trusted LAN endpoint."
        )
    if settings.server_host not in {"127.0.0.1", "localhost", "::1"}:
        issues.append(
            "SERVER_HOST is not loopback. The interface may be reachable by other devices. "
            "Use firewall/TLS controls before exposing it on a LAN."
        )
    if settings.admin_password and len(settings.admin_password) < 12:
        issues.append("The bootstrap administrator password is shorter than 12 characters.")
    if settings.admin_password and settings.admin_password.upper() in {"CHANGE_THIS_LOCALLY", "PASSWORD", "ADMIN"}:
        issues.append("The bootstrap administrator password still uses a placeholder value.")
    return issues
