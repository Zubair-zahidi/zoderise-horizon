# ZODERISE HORIZON V8 FINAL — Architecture

## Runtime

```text
Browser
  │
  ▼
Streamlit UI (localhost:8501)
  │
  ├─ Authentication / roles / preferences
  ├─ Chat / Research / Study / Knowledge / Admin
  ├─ SQLite local application database
  ├─ Local file storage
  ├─ Lexical/BM25-style document retrieval
  │
  └─ Ollama (127.0.0.1:11434)
       ├─ zoderise:latest
       └─ zoderise-vision:latest
```

No cloud AI service and no third embedding model are required.

## Modules

- `app.py` — routing and Streamlit workflows.
- `zoderise/config.py` — validated local configuration and security checks.
- `zoderise/database.py` — SQLite schema, migrations, users, sessions, conversations, knowledge metadata, saved outputs, audit log, login throttling.
- `zoderise/security.py` — scrypt password hashes, session-token hashes, input helpers.
- `zoderise/ai.py` — local Ollama model discovery, streaming chat, prompts, language handling.
- `zoderise/documents.py` — upload validation, extraction, OCR, chunking, storage isolation, lexical retrieval.
- `zoderise/domains.py` — domain definitions, role/profile values, visual accents and prompt guidance.
- `zoderise/local_tools.py` — deterministic offline utilities.
- `zoderise/ui.py` — dependency-free Horizon V8 visual system.

## Retrieval design

Document retrieval intentionally does not require embeddings. Text is chunked locally and ranked with a BM25-inspired scorer using term frequency, inverse document frequency, query coverage, and phrase bonuses. This keeps the full system usable with only `zoderise:latest` and `zoderise-vision:latest`.

## Data boundary

By default both Streamlit and Ollama are expected on loopback. ZODERISE rejects a non-loopback Ollama endpoint unless explicitly allowed by configuration. Files and SQLite data stay on the local host unless the operator changes that deployment boundary.
