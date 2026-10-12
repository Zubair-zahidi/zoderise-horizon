"""Read-only deployment checks; never prints passwords or changes models."""
from pathlib import Path
import importlib.metadata
import json
import shutil
import sys

from zoderise.config import settings, security_configuration_issues
from zoderise.ai import model_status


def main() -> int:
    status = model_status()
    checks = {
        "python": sys.version.split()[0],
        "streamlit": importlib.metadata.version("streamlit"),
        "artwork_present": all((Path(__file__).parent / "assets" / f).is_file() for f in ("horizon-orbit.webp", "knowledge-studio.webp", "horizon.css")),
        "free_disk_gb": round(shutil.disk_usage(settings.db_path.parent).free / 1024**3, 1),
        "ai_online": status["online"],
        "text_model_ready": status["text_ready"],
        "vision_model_ready": status["vision_ready"],
        "context_tokens": settings.ai_num_ctx,
        "keep_alive": settings.keep_alive,
        "configuration_notes": security_configuration_issues(),
    }
    print(json.dumps(checks, indent=2))
    return 0 if checks["artwork_present"] and status["text_ready"] and status["vision_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
