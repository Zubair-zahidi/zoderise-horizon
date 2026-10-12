# Security Notes

## Fixed in this version

- No real administrator password is shipped in the project.
- Passwords use `scrypt` hashing; existing PBKDF2 hashes can be verified and rehashed at successful login.
- Session tokens are random and only their SHA-256 hash is stored in SQLite.
- Expired/revoked sessions are cleaned, and active sessions are capped per user.
- Failed login attempts are throttled in memory on the local server.
- Ollama must be a loopback endpoint by default.
- Streamlit binds to `127.0.0.1` in the supplied launcher.
- Upload file signatures are checked for common binary types.
- DOCX archives are inspected for unsafe paths and excessive uncompressed size.
- PDFs have a page-count limit.
- Images have a total-pixel limit.
- Attachments have per-file, count, and total-size limits.
- Uploaded files are stored in per-user directories with generated filenames.
- Path checks are applied before displaying/deleting stored chat images.
- Audit records have configurable retention.
- Ephemeral chat allows session-only message retention.

## Threat model

The default deployment assumes one trusted Windows/Linux host. It aims to protect against accidental data leakage to cloud AI services, cross-account access through normal application use, unsafe filenames/path traversal, weak credential storage, and uncontrolled upload sizes.

It does **not** protect against an attacker who already has administrator/root access to the host operating system. It also does not make an exposed Streamlit server safe for the public internet by itself.

## Required host controls for sensitive deployments

- Full-disk encryption (for example BitLocker on Windows).
- Strong OS login credentials and separate user accounts.
- Automatic security updates.
- Firewall rules.
- Restricted physical access.
- Offline/encrypted backups.
- Antivirus/endpoint protection appropriate for the organization.
- TLS reverse proxy and network allow-list if accessed over a LAN.
- A policy defining who can publish shared knowledge files.

## Secrets

Never put a real password, API key, private key, or token in source control. `.env` is ignored by Git. If a credential was previously stored in a file that was shared or committed, treat it as exposed and rotate it.

## AI-specific security

- Uploaded document text is untrusted. It is evidence, not a source of system permissions.
- The model is explicitly told not to follow instructions embedded in documents that attempt to override application behavior.
- Local AI can still hallucinate or make mistakes. Evidence-sensitive workflows should show the retrieved source text and citations.
- Cybersecurity guidance is framed for defensive or authorized testing use, which is more appropriate for school/company deployments.
