# Run and deploy Zoderise Horizon

## Your Windows laptop

1. Run `setup_windows.bat` to create or repair the local virtual environment and install the pinned dependencies.
2. Install Ollama and make sure its service is reachable at the `OLLAMA_BASE_URL` in `.env`. The provided example defaults to **11434**. Earlier laptop configurations used **11435**; preserve that endpoint if your existing service uses it.
3. Double-click `start_ollama_and_zoderise.bat` and open http://127.0.0.1:8501.
4. Run `.venv\Scripts\python.exe preflight.py` to check artwork, configuration, and both models. Exit code 1 means required artwork or a model is unavailable.

The app supplies the updated creator identity on every AI request. Existing models do not need rebuilding for in-app identity changes. To use the same identity directly in Ollama, create models from this project's Modelfiles against the same endpoint:

```powershell
$env:OLLAMA_HOST = 'http://127.0.0.1:11435'
ollama pull dolphin3:8b
ollama pull llama3.2-vision:11b
ollama create zoderise -f Modelfile
ollama create zoderise-vision -f Modelfile-vision
```

Downloads are large; skip pulls for already installed base models. The separate original Modelfiles supplied as references were not modified.

## Performance profile

Defaults use 4,096 context tokens, batch size 128, and a three-minute model keep-alive. The launcher starts Ollama with one loaded model and one inference request at a time. Warm follow-up requests avoid reloading model weights. Set `ZODERISE_KEEP_ALIVE=0` in `.env` to release model memory after each answer if other apps need it. Restart after changing configuration.

An 11B vision model may spill into system RAM on an 8 GB GPU; actual speed depends on model quantization, available memory, drivers, and input images. No GPU throughput claim is made without an on-device benchmark. Balanced motion uses short entry and hover effects; Immersive adds slow artwork movement. Reduced mode and OS reduced-motion preferences suppress motion.

## Container deployment on one host

Requires Docker with Linux containers. NVIDIA inference also requires working GPU access in Docker (NVIDIA Container Toolkit on Linux or compatible Docker Desktop/WSL GPU support on Windows).

```powershell
docker compose -f compose.yaml -f compose.gpu.yaml up -d --build
docker compose exec ollama ollama pull dolphin3:8b
docker compose exec ollama ollama pull llama3.2-vision:11b
docker compose exec ollama ollama create zoderise -f /models/Modelfile
docker compose exec ollama ollama create zoderise-vision -f /models/Modelfile-vision
docker compose exec app python configure_owner.py
docker compose exec app python preflight.py
```

For CPU-only evaluation, omit `-f compose.gpu.yaml`. Use the same Compose file flags for subsequent `up` and `down` commands. The model and app data volumes survive restarts. `down -v` deletes them: do not use it for ordinary upgrades. The container installation starts with a separate, empty database; it does not copy your Windows accounts or documents.

The owner setup utility prompts locally for credentials. Registration is disabled in Compose by default. To enrol school accounts, enable registration with administrator approval, enrol users, then disable it again. Bootstrap the owner before allowing network traffic. Pin `OLLAMA_IMAGE` to an explicitly tested tag or image digest for a managed release; the default latest tag is convenient for initial setup but is mutable.

The app runs as a non-root user, drops Linux capabilities, has a health check, and publishes only on 127.0.0.1:8501. Ollama is internal to the Compose network. The image uses an allowlist build context so `.env`, databases, uploads, and backups are not copied into it. OCR is optional and is not installed in this image; text PDFs, DOCX, and vision chat work without it.

## School network / public hosting

The supplied configuration is a **single-host deployment**, with one AI answer at a time. For network access, place a TLS reverse proxy on the same host in front of 127.0.0.1:8501. Proxy WebSocket upgrades as well as HTTP, set upload limits and generous inference timeouts, and restrict access through the school firewall or VPN. Do not publish the Ollama port. A public hostname, certificate, firewall policy, and hosting account must be configured for the actual deployment target.

Run one application instance: local SQLite, uploaded-file paths, sessions, and the inference lock are not designed for independent replicas. Larger school deployments need a shared database, shared object storage, and a central inference queue.

## Backup and recovery

Administrators can use **Admin → Backups → Create and verify backup** to make a local ZIP with a consistent SQLite snapshot, uploaded files, and SHA-256 manifest. The app checks the archive after creation, and **Verify** rechecks it later. The ZIP is **unencrypted** and contains private data: copy it to protected storage. Pause uploads during a backup for a matching database/file snapshot. For manual backups, stop the app before copying **both** the database directory and storage directory configured in `.env`. Include SQLite sidecar files if present. Back up `.env` separately in protected storage. For Docker, stop the app service and snapshot the `app-data` volume. Resume after the copy completes. Restore the entire matching snapshot while the app is stopped, preserving the same container paths or Windows storage paths. Keep a previous app image/source release with each backup.

## Verification commands

```powershell
.venv\Scripts\python.exe tests\smoke_test.py
.venv\Scripts\python.exe tests\regression_test.py
.venv\Scripts\python.exe tests\ui_test.py
.venv\Scripts\python.exe tests\horizon_test.py
docker compose -f compose.yaml -f compose.gpu.yaml config --quiet
```

The automated tests use temporary databases, with mocked inference for UI workflows. A passing test is not proof of local model quality or a successful GPU/container deployment.

References: [Streamlit Docker deployment](https://docs.streamlit.io/deploy/tutorials/docker) and [Ollama runtime configuration](https://github.com/ollama/ollama/blob/main/envconfig/config.go).
