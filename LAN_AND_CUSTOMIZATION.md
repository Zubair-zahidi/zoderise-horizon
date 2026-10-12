# Phones, computers, and personal design

## Connect on the same network

Only the host laptop needs Python, Streamlit, and Ollama. Phones and other computers use their web browser.

1. On the laptop, run `setup_windows.bat` if the environment is not installed.
2. Set up the owner locally with `.venv\Scripts\python.exe configure_owner.py` before sharing access.
3. Run `start_hub.bat`. The launcher displays candidate laptop addresses, for example `http://192.168.1.20:8501`.
4. Connect the phone to the same trusted Wi-Fi and open the laptop address. Do not use `localhost` or `0.0.0.0` on the phone.
5. Sign in with a separate account for each person. In LAN mode new registrations require administrator approval.

If the address does not load: keep the laptop awake, check its current IPv4 address with `ipconfig`, avoid guest Wi-Fi/client isolation, and allow the Python app or TCP 8501 through Windows Firewall on the **Private** network profile only. This release does not change firewall rules automatically. Do not forward port 8501 or the Ollama port through your internet router. For sensitive school data, use the TLS/VPN deployment described in DEPLOYMENT.md; plain HTTP on Wi-Fi is not encrypted.

The LAN launcher refuses to start until an active administrator exists. It shares Streamlit, not the local Ollama service. The laptop processes one AI answer at a time; other users wait in a bounded first-in, first-out queue (up to 16 waiting, five-minute limit).

After signing in as administrator, open **Admin → Hub access** for the current connection address and QR code. The QR contains only the local app address, never a password or session token. Open **Admin → Sessions** to review active account sessions and revoke one when needed.

The Windows application can also host the Hub. Create a local administrator, then choose **Workspace → Enable Hub on this computer**. The server restarts in host mode and Admin → Hub access shows an address and QR code. On a client computer open **Workspace → Connect to Hub**, enter that address, and sign in. That computer does not need Python or Ollama. A saved Hub that is offline shows an explicit error rather than silently opening a different local account. **Workspace → Use this computer** deliberately returns it to its own local server. For access outside the home/school Wi-Fi, use a trusted VPN or HTTPS reverse proxy and enter its HTTPS URL; never forward ports 8501 or 11434 directly through the router.

## Customize each browser

Open **Appearance** (or **Style** in the mobile quick navigation). Choose a visual preset with its **Use** button for an immediate change. The current-look preview shows your saved style. Quick motion buttons apply immediately; the detailed form uses **Save on this browser**.

- Editorial or Modern headline typography.
- Four palettes: Midnight, Forest, Graphite, and High contrast.
- Five accent colors, three reading text sizes, compact/comfortable spacing.
- Balanced, wide, or reading width; full, compact, or hidden artwork.
- Quiet, Gentle, or Moving 3D details quick controls. Immersive motion animates CSS sculptures, orbit rings, and artwork only above 760px; operating-system reduced motion takes priority.
- Focus layout, a preferred start page, and four complete presets.
- Export/import a small appearance JSON file or reset to defaults.

Click **Save on this browser**. Preferences are kept in browser local storage, scoped to the signed-in account and site address. A phone and laptop can have different designs even for the same account. Changing IP address, port, browser profile, clearing site data, or private browsing can create/reset a separate profile. Export a profile to transfer it. If browser storage is blocked, settings still work for the session and the app shows a notice.

Appearance files contain design choices only, never passwords or chat history. Account-level language, subject, and AI settings remain separate. Uploaded documents and saved chats are stored on the **host laptop**, not on each phone. Session-only chat now supports Markdown download without requiring server-side history storage.

## Reliability fixes in this update

- Failed generation no longer leaves a half-saved chat turn or an empty saved conversation. Successful question/answer pairs commit together.
- Restore a failed question to the composer for editing and retry. Temporary chat image files are cleaned up after failure.
- Earlier images are reused only when explicitly selected, avoiding unexpected Vision requests for unrelated questions.
- Legacy attachment metadata and malformed model-stream messages are validated.
- Phone photo orientation is respected; stored chat images are bounded in size.
- Opening a saved conversation clears stale drafts/uploads from the previous chat.
- Study excerpts rotate across documents rather than letting the first file consume the source budget.
- Database initialization is cached; research/study streaming avoids redrawing for every tiny token.
- Owner setup uses the same strong-password validation as account registration.

This is a tested single-host application, not a claim that every possible bug or model error has been eliminated. Public hosting, large classroom load, and physical phone/network testing require validation on the target network.
