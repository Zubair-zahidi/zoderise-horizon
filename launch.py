"""Start the local workspace using the selected virtual environment."""
from pathlib import Path
import os
import subprocess
import sys
import time
import requests
import shutil
import socket
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def main() -> int:
    lan = "--lan" in sys.argv
    if lan:
        os.environ["ZODERISE_REQUIRE_ADMIN_APPROVAL"] = "1"
        os.environ["SERVER_HOST"] = "0.0.0.0"
    from zoderise.config import settings
    if lan:
        from zoderise.database import init_db, connect
        init_db()
        with connect() as conn:
            has_owner = conn.execute("SELECT 1 FROM users WHERE role='admin' AND is_active=1 AND approved=1 LIMIT 1").fetchone()
        if not has_owner:
            print("Create the owner on this laptop before enabling LAN access: python configure_owner.py")
            return 1
        print("LAN mode: accounts require administrator approval. Only the web app is shared; Ollama stays local.")
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET) if not item[4][0].startswith('127.')})
            for address in addresses:
                print(f"Phone/browser URL: http://{address}:{settings.server_port}")
        except OSError:
            print(f"Open http://<laptop IPv4 address>:{settings.server_port} on the same Wi-Fi.")
    if "--with-ollama" in sys.argv:
        try:
            requests.get(f"{settings.ollama_base_url}/api/tags", timeout=2).raise_for_status()
        except requests.RequestException:
            env = os.environ.copy()
            env.update(OLLAMA_MAX_LOADED_MODELS="1", OLLAMA_NUM_PARALLEL="1", OLLAMA_CONTEXT_LENGTH="4096", OLLAMA_NO_CLOUD="1")
            endpoint = urlparse(settings.ollama_base_url)
            if endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise RuntimeError("Start a remote Ollama server on its own host.")
            env['OLLAMA_HOST'] = settings.ollama_base_url
            # Prevent the separate llama.cpp installation from shadowing Ollama's DLLs.
            env['PATH'] = os.pathsep.join(part for part in env.get('PATH', '').split(os.pathsep) if 'ggml.llamacpp_' not in part.lower())
            model_path = os.getenv('ZODERISE_OLLAMA_MODELS')
            if model_path:
                env['OLLAMA_MODELS'] = model_path
            try:
                executable = shutil.which("ollama") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe")
                log_path = settings.db_path.parent / 'ollama-runtime.log'
                with log_path.open('a', encoding='utf-8') as log:
                    subprocess.Popen([executable, "serve"], env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), stdout=log, stderr=subprocess.STDOUT)
                for _ in range(40):
                    try:
                        requests.get(f"{settings.ollama_base_url}/api/tags", timeout=1).raise_for_status()
                        break
                    except requests.RequestException:
                        time.sleep(0.5)
            except FileNotFoundError:
                print("Ollama is not installed. The workspace will open with AI offline.")
    if '--check-models' in sys.argv:
        try:
            response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
            response.raise_for_status()
            installed = {model['name'] for model in response.json().get('models', [])}
            missing = {settings.text_model, settings.vision_model} - installed
            print('Missing models: ' + ', '.join(sorted(missing)) if missing else 'Both Zoderise models are available. No download or rebuild is needed.')
            return 1 if missing else 0
        except requests.RequestException:
            print('Ollama is not responding. Review data/ollama-runtime.log.')
            return 1
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
        "--server.address", "0.0.0.0" if lan else settings.server_host, "--server.port", str(settings.server_port),
        "--server.enableStaticServing", "true",
        "--browser.gatherUsageStats", "false"])


if __name__ == "__main__":
    raise SystemExit(main())
