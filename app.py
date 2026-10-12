from __future__ import annotations

import base64
import html
import io
import json
import os
import platform
import time
from pathlib import Path
from typing import Any, Optional, Sequence

import requests
import streamlit as st
from PIL import Image, ImageOps

from zoderise.ai import (
    build_evidence_prompt,
    build_system_prompt,
    chat_stream,
    model_status,
    ollama_online,
    ollama_tags,
    clear_model_cache,
)
from zoderise.config import security_configuration_issues, settings
from zoderise.database import (
    add_bookmark,
    admin_delete_user,
    admin_revoke_session,
    admin_update_user,
    audit,
    change_password,
    cleanup_maintenance,
    collect_chat_attachments,
    compact_database,
    create_conversation,
    create_session,
    current_user_from_token,
    dashboard_stats,
    delete_account_records,
    delete_conversation,
    delete_saved_output,
    ensure_admin,
    get_conversation,
    get_messages,
    get_preferences,
    get_retrieval_rows,
    init_db,
    list_bookmarks,
    list_conversations,
    list_documents,
    list_active_sessions,
    list_saved_outputs,
    list_users,
    purge_chat_history,
    recent_audit,
    register_user,
    remove_bookmark,
    rename_conversation,
    revoke_session,
    save_message,
    save_exchange,
    save_output,
    set_conversation_flag,
    update_preferences,
    update_user_profile,
    authenticate,
    login_blocked,
    record_login_failure,
    clear_login_failures,
)
from zoderise.documents import (
    ALLOWED_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    delete_stored_document,
    document_preview,
    file_capabilities,
    process_ephemeral_document,
    remove_chat_attachments,
    remove_user_storage,
    retrieve_chunks,
    retrieve_ephemeral,
    save_chat_image,
    save_document,
    validate_upload,
)
from zoderise.domains import (
    DEPLOYMENT_PROFILES,
    DOMAIN_NAMES,
    DOMAINS,
    LANGUAGES,
    MODES,
    PRIVACY_MODES,
    ROLES,
    domain_info,
)
from zoderise.local_tools import UNIT_GROUPS, convert_unit, format_json, safe_calculate, sha256_text
from zoderise.ui import footer, hero_core, inject_css, render_topbar, render_art_header
from zoderise.classroom import render_classroom_studio
from zoderise.appearance import sync_device_appearance, render_appearance_page, save_appearance
from zoderise.chat_utils import object_list, export_chat
from zoderise.hub import hub_urls, qr_png
from zoderise.inference_queue import inference_queue
from zoderise.backup import create_backup, verify_backup

try:
    import psutil
except Exception:
    psutil = None


st.set_page_config(
    page_title="Zoderise Horizon | Local workspace",
    page_icon=str(Path(__file__).resolve().parent / "assets" / "zoderise-icon.png"),
    layout="wide",
    initial_sidebar_state="auto",
)


# -----------------------------------------------------------------------------
# Startup
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def initialize_database():
    init_db()
    ensure_admin()
    return True


initialize_database()
if "maintenance_done" not in st.session_state:
    cleanup_maintenance()
    st.session_state.maintenance_done = True


def ss_default(key: str, value: Any) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


ss_default("session_token", None)
ss_default("page", "Home")
ss_default("conversation_id", None)
ss_default("prefs_loaded_for", None)
ss_default("domain", "General Intelligence")
ss_default("language", "English")
ss_default("mode", "Chat")
ss_default("model", settings.text_model)
ss_default("animation", "Balanced")
ss_default("reduced_motion", False)
ss_default("privacy_mode", settings.default_privacy_mode if settings.default_privacy_mode in PRIVACY_MODES else "Ephemeral")
ss_default("detail_level", "Balanced")
ss_default("deployment_profile", "School")
ss_default("ephemeral_messages", [])
ss_default("ephemeral_sources", [])
ss_default("show_purge_confirm", False)


def load_user_preferences(user: Any) -> None:
    uid = int(user["id"])
    if st.session_state.prefs_loaded_for == uid:
        return
    prefs = get_preferences(uid)
    st.session_state.domain = prefs["domain"] if prefs["domain"] in DOMAIN_NAMES else "General Intelligence"
    st.session_state.language = prefs["language"] if prefs["language"] in LANGUAGES else "English"
    st.session_state.mode = prefs["mode"] if prefs["mode"] in MODES else "Chat"
    st.session_state.model = prefs["model"] or settings.text_model
    st.session_state.animation = prefs["animation"] or "Balanced"
    st.session_state.reduced_motion = bool(prefs["reduced_motion"])
    st.session_state.privacy_mode = prefs["privacy_mode"] if prefs["privacy_mode"] in PRIVACY_MODES else "Ephemeral"
    st.session_state.detail_level = prefs["detail_level"] or "Balanced"
    st.session_state.deployment_profile = prefs["deployment_profile"] if prefs["deployment_profile"] in DEPLOYMENT_PROFILES else "School"
    st.session_state.prefs_loaded_for = uid


def user_is_admin(user: Any) -> bool:
    return str(user["role"]) == "admin"


def make_system_prompt(user: Any, mode: str, query: str) -> str:
    return build_system_prompt(
        domain=st.session_state.domain,
        selected_language=st.session_state.language,
        mode=mode,
        user_query=query,
        user_role=str(user["role"]),
        deployment_profile=st.session_state.deployment_profile,
        detail_level=st.session_state.detail_level,
        privacy_mode=st.session_state.privacy_mode,
    )


def model_ready(model: str) -> bool:
    return model in set(ollama_tags())


def safe_attachment_path(path_value: str, user_id: int) -> Optional[Path]:
    try:
        path = Path(path_value).resolve()
        root = (settings.storage_root / "uploads" / f"user_{user_id}").resolve()
        path.relative_to(root)
        return path if path.is_file() else None
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------
def page_auth() -> None:
    inject_css("General Intelligence", "Balanced", False)
    left, center = st.columns([1.2, 1], gap="large")
    with left:
        render_art_header("A new horizon for your ideas.", "Private intelligence for learning, research, and everything you want to build.", label="ZODERISE / HORIZON", variant="z-auth-hero")
    issues = security_configuration_issues()
    if issues:
        with st.expander("Security setup notice"):
            for issue in issues:
                st.warning(issue)

    with center:
        st.caption("YOUR PRIVATE WORKSPACE")
        st.header("Welcome to Zoderise.")
        st.caption("Sign in to continue. Your work stays on the host laptop.")
        sign_in, create = st.tabs(["Sign in", "Create account"])
        with sign_in, st.form("sign_in_form"):
            identifier = st.text_input("Email or username", key="auth_identifier")
            password = st.text_input("Password", type="password", key="auth_password")
            if st.form_submit_button("Sign in", type="primary", width="stretch", key="auth_login"):
                blocked, seconds = login_blocked(identifier)
                if blocked:
                    st.error(f"Too many failed attempts. Try again in about {seconds} seconds.")
                else:
                    user = authenticate(identifier, password)
                    if user:
                        clear_login_failures(identifier)
                        st.session_state.session_token = create_session(int(user["id"]))
                        st.session_state.prefs_loaded_for = None
                        st.session_state.ephemeral_messages = []
                        st.session_state.page = "Home"
                        st.rerun()
                    else:
                        record_login_failure(identifier)
                        st.error("Invalid credentials, inactive account, or account awaiting approval.")

        with create:
            if not settings.enable_registration:
                st.info("Self-registration is disabled. Ask an administrator to create your account.")
            else:
                name = st.text_input("Full name", key="reg_name")
                username = st.text_input("Username", key="reg_username")
                email = st.text_input("Email", key="reg_email")
                organization = st.text_input("School / company / organization", key="reg_org")
                department = st.text_input("Department / class (optional)", key="reg_department")
                grade = st.text_input("Grade / team (optional)", key="reg_grade")
                pw1 = st.text_input("Password", type="password", key="reg_pw1")
                pw2 = st.text_input("Confirm password", type="password", key="reg_pw2")
                if st.button("Create local account", width="stretch", key="auth_register"):
                    if pw1 != pw2:
                        st.error("Passwords do not match.")
                    else:
                        ok, message = register_user(name, username, email, pw1, organization, department, grade)
                        (st.success if ok else st.error)(message)
    footer()


user = current_user_from_token(st.session_state.session_token)
if not user:
    if st.session_state.session_token:
        st.session_state.clear()
        st.rerun()
    page_auth()
    st.stop()

load_user_preferences(user)
sync_device_appearance(int(user["id"]))
inject_css(st.session_state.domain, st.session_state.animation, st.session_state.reduced_motion, st.session_state.get("appearance"))


# -----------------------------------------------------------------------------
# Sidebar and navigation
# -----------------------------------------------------------------------------
def ensure_persistent_conversation(user: Any) -> int:
    cid = st.session_state.get("conversation_id")
    if cid and get_conversation(int(user["id"]), int(cid)):
        return int(cid)
    cid = create_conversation(int(user["id"]), "New Chat", st.session_state.domain, st.session_state.deployment_profile)
    st.session_state.conversation_id = cid
    return cid


def wipe_ephemeral_chat() -> None:
    st.session_state.ephemeral_messages = []
    st.session_state.ephemeral_sources = []
    st.session_state.chat_document_ids = []
    st.session_state.pop("pending_chat_draft", None)
    st.session_state.pop("chat_composer", None)
    st.session_state.pop("failed_chat_prompt", None)
    st.session_state.pop("use_previous_image", None)
    st.session_state.upload_generation = st.session_state.get("upload_generation", 0) + 1


def render_sidebar(user: Any) -> None:
    uid = int(user["id"])
    with st.sidebar:
        st.markdown('<div class="z-brand">z. ZODERISE</div><div class="z-sub">Your local workspace</div>', unsafe_allow_html=True)
        if st.button("New chat", icon=":material/add:", type="primary", width="stretch", key="new_session"):
            wipe_ephemeral_chat()
            st.session_state.conversation_id = None
            st.session_state.page = "Chat"
            st.rerun()
        groups = {
            "WORKSPACE": [("Home", "space_dashboard"), ("Chat", "chat_bubble"), ("Prompt Studio", "auto_awesome"), ("Knowledge", "folder_open"), ("Research", "search"), ("Study Lab", "school")],
            "YOUR WORK": [("History", "history"), ("Saved", "bookmark"), ("Tools", "calculate"), ("Appearance", "palette")],
        }
        for group, pages in groups.items():
            st.caption(group)
            for page, icon in pages:
                if st.button(page, icon=f":material/{icon}:", type="primary" if st.session_state.page == page else "tertiary", width="stretch", key=f"nav_{page}"):
                    st.session_state.device_user_navigated = True
                    st.session_state.page = page
                    st.rerun()
        with st.expander("Conversation preferences"):
            domain = st.selectbox("Subject", DOMAIN_NAMES, index=DOMAIN_NAMES.index(st.session_state.domain))
            language = st.selectbox("Response language", LANGUAGES, index=LANGUAGES.index(st.session_state.language))
            mode = st.selectbox("Chat mode", ["Chat", "Documents", "Vision"], index=["Chat", "Documents", "Vision"].index(st.session_state.mode) if st.session_state.mode in ["Chat", "Documents", "Vision"] else 0)
            privacy = st.selectbox("Chat storage", PRIVACY_MODES, index=PRIVACY_MODES.index(st.session_state.privacy_mode), format_func=lambda x: "Session only" if x == "Ephemeral" else "Save on host laptop")
            st.caption("Changing storage clears the session-only conversation. Saved conversations remain in History.")
            if st.button("Apply preferences", key="apply_chat_preferences", width="stretch"):
                if privacy != st.session_state.privacy_mode:
                    wipe_ephemeral_chat()
                    st.session_state.conversation_id = None
                for key, value in {"domain": domain, "language": language, "mode": mode, "privacy_mode": privacy}.items():
                    st.session_state[key] = value
                st.session_state.model = settings.vision_model if mode == "Vision" else settings.text_model
                update_preferences(uid, domain=domain, language=language, mode=mode, privacy_mode=privacy, model=st.session_state.model)
                st.rerun()
        with st.expander("Account & system"):
            for page in ["Account", "Settings", "About"] + (["Diagnostics", "Admin"] if user_is_admin(user) else []):
                if st.button(page, width="stretch", key=f"nav_{page}"):
                    st.session_state.page = page
                    st.rerun()
        st.divider()
        st.caption(f"{user['name']} · {user['role'].title()}")
        st.caption("Session-only chat" if st.session_state.privacy_mode == "Ephemeral" else "Chat saved on host laptop")
        if st.button("Refresh AI connection", icon=":material/refresh:", key="refresh_ai", width="stretch"):
            clear_model_cache()
            st.rerun()
        if st.button("Sign out", icon=":material/logout:", width="stretch", key="logout"):
            revoke_session(st.session_state.session_token or "")
            st.session_state.clear()
            st.rerun()


render_sidebar(user)


def topbar(user: Any) -> None:
    render_topbar(user, st.session_state.domain, st.session_state.mode, ollama_online(), st.session_state.privacy_mode)
    with st.container(horizontal=True, key="mobile_navigation"):
        for label, destination in [("Home", "Home"), ("Chat", "Chat"), ("Library", "Knowledge"), ("Style", "Appearance")]:
            if st.button(label, key=f"mobile_{destination}", type="primary" if st.session_state.page == destination else "secondary"):
                st.session_state.page = destination
                st.session_state.device_user_navigated = True
                st.rerun()


# -----------------------------------------------------------------------------
# Home
# -----------------------------------------------------------------------------
def page_home(user: Any) -> None:
    topbar(user)
    status = model_status()
    st.html('<div class="z-edition"><span>YOUR PERSONAL ATELIER</span><span>LEARN / CREATE / DISCOVER</span></div>')
    render_art_header("An extraordinary space for your next idea.", f"Welcome back, {user['name'].split()[0]}. Bring your curiosity. Turn a question into understanding, a lesson into possibility.", label="ZODERISE HORIZON / KARDAN PRIVATE SCHOOL")
    with st.container(horizontal=True):
        if st.button("Start a new conversation", type="primary", icon=":material/add:", key="hero_new_chat"):
            wipe_ephemeral_chat()
            st.session_state.conversation_id = None
            st.session_state.mode = "Chat"
            st.session_state.page = "Chat"
            st.rerun()
        if st.button("Open your library", icon=":material/folder_open:", key="hero_library"):
            st.session_state.page = "Knowledge"
            st.rerun()
        if st.button("Plan a lesson", icon=":material/auto_awesome:", key="hero_studio"):
            st.session_state.page = "Prompt Studio"
            st.rerun()
    if not status["online"]:
        st.warning("Ollama is offline. Your library, saved work, and tools are available. Start Ollama to use AI.")
    elif not status["text_ready"] or not status["vision_ready"]:
        st.warning("One of your configured models is missing. Check Diagnostics before starting an AI task.")
    with st.container(border=True, key="idea_launchpad"):
        st.html('<div class="z-eyebrow">THE STARTING POINT</div>')
        st.subheader("Start with an idea")
        st.caption("Shape a useful brief in seconds. You can edit it before sending.")
        with st.form("idea_brief", border=False):
            idea = st.text_input("Your idea or topic", placeholder="e.g. Help my class understand solar energy", max_chars=1200, key="home_idea")
            goal_col, depth_col = st.columns([3, 2])
            with goal_col:
                goal = st.selectbox("What would you like to create?", ["A clear explanation", "A lesson outline", "A practice quiz", "A creative brainstorm"], key="home_goal")
            with depth_col:
                depth = st.selectbox("Level of detail", ["Balanced", "Quick overview", "Deep exploration"], key="home_depth")
            if st.form_submit_button("Create my starting brief", type="primary", icon=":material/arrow_forward:"):
                if not idea.strip():
                    st.warning("Add an idea or topic to begin.")
                else:
                    wipe_ephemeral_chat()
                    st.session_state.conversation_id = None
                    st.session_state.mode = "Chat"
                    st.session_state.model = settings.text_model
                    st.session_state.pending_chat_draft = f"Create {goal.lower()} about: {idea.strip()}\n\nDepth: {depth}. Use clear structure and concrete examples. Ask a clarifying question if essential context is missing."
                    st.session_state.page = "Chat"
                    st.rerun()
    st.html('<div class="z-section-heading"><div><span class="z-eyebrow">FOUR WAYS TO BEGIN</span><h2>Follow your curiosity.</h2></div><span class="z-section-note">Purposeful tools. Room to explore.</span></div>')
    actions = [
        ("Start a conversation", "Explain a concept, develop an idea, or write something new.", "Chat", "Chat", "chat_bubble"),
        ("Explore your documents", "Find answers in your files, with evidence you can inspect.", "Research", "Documents", "search"),
        ("Build study material", "Turn lessons into summaries, quizzes, or practice problems.", "Study Lab", "Chat", "school"),
        ("Understand an image", "Read a diagram, explore a photo, or explain a screenshot.", "Chat", "Vision", "image"),
    ]
    for offset in (0, 2):
        cols = st.columns(2)
        for col, (title, description, page, mode, icon) in zip(cols, actions[offset:offset + 2]):
            with col, st.container(border=True, key=f"workspace_{icon}"):
                number = actions.index((title, description, page, mode, icon)) + 1
                st.html(f'<div class="z-workspace-number"><span>0{number} / WORKSPACE</span><span>↗</span></div>')
                st.html(f'<div class="z-sculpture z-sculpture-{number}" aria-hidden="true"><i></i><i></i><i></i><b>0{number}</b></div>')
                st.subheader(title)
                st.caption(description)
                if st.button("Open workspace", icon=f":material/{icon}:", key=f"home_action_{icon}", width="stretch"):
                    st.session_state.page = page
                    st.session_state.mode = mode
                    st.session_state.model = settings.vision_model if mode == "Vision" else settings.text_model
                    st.rerun()
    docs = list_documents(int(user["id"]))
    conversations = list_conversations(int(user["id"]))
    outputs = list_saved_outputs(int(user["id"]))
    with st.container(horizontal=True):
        st.metric("Library documents", len(docs), border=True)
        st.metric("Saved conversations", len(conversations), border=True)
        st.metric("Saved outputs", len(outputs), border=True)
    st.subheader("Continue your work")
    if not conversations:
        st.info("Your saved conversations will appear here. Choose ‘Save on host laptop’ in conversation preferences to keep a chat.")
    for conv in conversations[:4]:
        if st.button(conv["title"], icon=":material/chat_bubble_outline:", key=f"recent_{conv['id']}", width="stretch"):
            open_conversation(user, conv)


def open_conversation(user: Any, conv: Any) -> None:
    wipe_ephemeral_chat()
    st.session_state.privacy_mode = "Persistent"
    st.session_state.conversation_id = int(conv["id"])
    st.session_state.domain = conv["domain"] if conv["domain"] in DOMAIN_NAMES else "General Intelligence"
    st.session_state.page = "Chat"
    update_preferences(int(user["id"]), privacy_mode="Persistent", domain=st.session_state.domain)
    st.rerun()


def page_history(user: Any) -> None:
    topbar(user)
    st.title("Conversation history")
    query = st.text_input("Search saved conversations", placeholder="Search by title or subject…")
    archived = st.checkbox("Include archived conversations")
    conversations = list_conversations(int(user["id"]), include_archived=archived)
    rows = [c for c in conversations if query.casefold() in (c["title"] + c["domain"]).casefold()]
    if not rows:
        st.info("No saved conversations match. Session-only chats are never added to history.")
    for conv in rows:
        with st.container(border=True):
            st.markdown(f"**{conv['title']}**")
            st.caption(f"{conv['domain']} · {time.strftime('%d %b %Y', time.localtime(conv['updated_at']))}" + (" · Archived" if conv["archived"] else ""))
            with st.container(horizontal=True):
                if st.button("Open", key=f"history_open_{conv['id']}"):
                    open_conversation(user, conv)
                if conv["archived"] and st.button("Restore", key=f"history_restore_{conv['id']}"):
                    set_conversation_flag(int(user["id"]), int(conv["id"]), "archived", False)
                    st.rerun()


# -----------------------------------------------------------------------------
# Chat
# -----------------------------------------------------------------------------
def _display_sources(sources: Sequence[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander(f"Local evidence · {len(sources)} source(s)"):
        for index, source in enumerate(sources, 1):
            page = f" · p.{source.get('page')}" if source.get("page") else ""
            st.markdown(f"**[{index}] {source.get('filename', 'source')}{page}**")
            st.caption(str(source.get("text", ""))[:1000])
        st.caption("These passages are ranked by text match. Check the original document before relying on an answer.")


def _render_persistent_messages(user: Any, cid: int) -> list[Any]:
    uid = int(user["id"])
    messages = get_messages(uid, cid)
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            try:
                attachments = json.loads(message["attachment_json"] or "[]")
            except Exception:
                attachments = []
            if isinstance(attachments, dict):
                attachments = [attachments]
            for attachment in attachments if isinstance(attachments, list) else []:
                st.caption(f"Attachment · {attachment.get('filename', 'file')}")
                path_value = attachment.get("stored_path")
                if path_value:
                    path = safe_attachment_path(path_value, uid)
                    if path and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                        st.image(str(path), width="stretch")
            try:
                sources = json.loads(message["sources_json"] or "[]")
            except Exception:
                sources = []
            _display_sources(sources if isinstance(sources, list) else [])
            if message["role"] == "assistant":
                if st.button("☆ Save answer", key=f"bookmark_message_{message['id']}"):
                    if add_bookmark(uid, cid, int(message["id"])):
                        st.toast("Saved to bookmarks.")
                    else:
                        st.toast("Already saved.")
    return messages


def _render_ephemeral_messages() -> list[dict[str, Any]]:
    messages = st.session_state.ephemeral_messages
    for index, message in enumerate(messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for attachment in message.get("attachments", []):
                st.caption(f"Attachment · {attachment.get('filename', 'file')}")
            _display_sources(message.get("sources", []))
            if message["role"] == "assistant":
                st.download_button("Download answer", message["content"], file_name="zoderise-answer.md", mime="text/markdown", key=f"ephemeral_export_{index}")
    return messages


def _conversation_tools(user: Any, cid: int) -> None:
    conv = get_conversation(int(user["id"]), cid)
    if not conv:
        return
    with st.expander("Conversation controls"):
        new_title = st.text_input("Title", value=conv["title"], key=f"rename_conv_{cid}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Rename", width="stretch", key=f"rename_go_{cid}"):
                rename_conversation(int(user["id"]), cid, new_title)
                st.rerun()
        with c2:
            if st.button("Unpin" if conv["pinned"] else "Pin", width="stretch", key=f"pin_{cid}"):
                set_conversation_flag(int(user["id"]), cid, "pinned", not bool(conv["pinned"]))
                st.rerun()
        with c3:
            if st.button("Archive", width="stretch", key=f"archive_{cid}"):
                set_conversation_flag(int(user["id"]), cid, "archived", True)
                st.session_state.conversation_id = None
                st.rerun()
        with c4:
            confirm_delete = st.checkbox("Confirm deletion", key=f"confirm_conv_{cid}")
            if st.button("Delete", disabled=not confirm_delete, width="stretch", key=f"delete_conv_{cid}"):
                attachments = collect_chat_attachments(int(user["id"]), cid)
                remove_chat_attachments(attachments, int(user["id"]))
                delete_conversation(int(user["id"]), cid)
                st.session_state.conversation_id = None
                st.rerun()

        export_messages = get_messages(int(user["id"]), cid)
        md = f"# {conv['title']}\n\n" + "\n\n".join(
            f"## {m['role'].title()}\n\n{m['content']}" for m in export_messages
        )
        payload = [dict(m) for m in export_messages]
        e1, e2 = st.columns(2)
        with e1:
            st.download_button("Export Markdown", md, file_name=f"zoderise_chat_{cid}.md", mime="text/markdown", width="stretch")
        with e2:
            st.download_button("Export JSON", json.dumps(payload, ensure_ascii=False, indent=2), file_name=f"zoderise_chat_{cid}.json", mime="application/json", width="stretch")


def page_chat(user: Any) -> None:
    topbar(user)
    st.caption("Attach an image to use Vision automatically. Document attachments remain available for follow-up questions in this chat.")
    uid = int(user["id"])
    persistent = st.session_state.privacy_mode == "Persistent"
    current_id = st.session_state.get("conversation_id")
    cid: Optional[int] = int(current_id) if persistent and current_id and get_conversation(uid, int(current_id)) else None
    messages: Sequence[Any]
    if persistent and cid is not None:
        messages = _render_persistent_messages(user, cid)
    elif persistent:
        messages = []
    else:
        messages = _render_ephemeral_messages()

    if not messages:
        render_art_header("What will you explore today?", "Ask a question, attach a document, or share an image. Start with a thought; build from there.", label=st.session_state.domain, variant="z-section-hero")
        with st.container(horizontal=True):
            for label, starter in [("Explain a concept", "Help me understand a concept. Ask me what topic and level I am studying first."), ("Make a practice quiz", "Help me practise with a short quiz. Ask me my subject and level first, then ask one question at a time."), ("Who created Zoderise?", "Who created Zoderise and who was it built for?")]:
                if st.button(label, key=f"starter_{label}"):
                    st.session_state["chat_composer"] = starter

    if persistent and cid is not None:
        _conversation_tools(user, cid)
    elif messages:
        st.download_button("Export this conversation", export_chat(messages), file_name="zoderise-conversation.md", mime="text/markdown", key="ephemeral_export_chat")

    if st.session_state.get("failed_chat_prompt"):
        st.info("Your last request did not finish. Your earlier conversation is unchanged.")
        if st.button("Restore question to composer", key="restore_failed_prompt"):
            st.session_state["chat_composer"] = st.session_state.pop("failed_chat_prompt")

    has_prior_images = any(
        (bool(m.get("images")) if isinstance(m, dict) else False)
        or any(a.get("stored_path") for a in object_list(m.get("attachments", []) if isinstance(m, dict) else m["attachment_json"]))
        for m in messages
    )
    reuse_images = st.checkbox("Use the previous image for this question", value=False, key="use_previous_image") if has_prior_images else False

    uploads = st.file_uploader(
        f"Attach up to {settings.max_chat_attachments} local files",
        type=[x.lstrip(".") for x in sorted(ALLOWED_EXTENSIONS)],
        accept_multiple_files=True,
        key=f"chat_uploads_{st.session_state.get('upload_generation', 0)}",
    )
    uploads = uploads or []
    if uploads:
        total_mb = sum(len(f.getvalue()) for f in uploads) / 1024 / 1024
        st.caption(f"{len(uploads)} attachment(s) · {total_mb:.2f} MB total")

    if st.session_state.get("pending_chat_draft"):
        st.session_state["chat_composer"] = st.session_state.pop("pending_chat_draft")
    prompt = st.chat_input("Ask a question, explain an idea, or work through a problem…", key="chat_composer")
    if not prompt:
        return
    prompt = prompt.strip()
    if not prompt:
        return
    st.session_state.failed_chat_prompt = prompt

    if len(prompt) > settings.max_prompt_chars:
        st.error(f"Please keep the question under {settings.max_prompt_chars:,} characters.")
        return

    if len(uploads) > settings.max_chat_attachments:
        st.error(f"Too many attachments. Limit: {settings.max_chat_attachments}.")
        return
    total_bytes = sum(len(f.getvalue()) for f in uploads)
    if total_bytes > settings.max_chat_total_mb * 1024 * 1024:
        st.error(f"Attachments exceed the {settings.max_chat_total_mb} MB total limit.")
        return

    sources: list[dict[str, Any]] = []
    image_payloads: list[str] = []
    attachment_info: list[dict[str, Any]] = []
    effective_mode = st.session_state.mode
    selected_model = settings.vision_model if effective_mode == "Vision" else settings.text_model
    if not model_ready(settings.vision_model if reuse_images or any(Path(f.name).suffix.lower() in IMAGE_EXTENSIONS for f in uploads) else selected_model):
        st.error("The required local model is unavailable. Start Ollama and check Diagnostics.")
        return

    exchange_saved = False
    try:
        ephemeral_chunks: list[dict[str, Any]] = []
        persistent_doc_ids: list[int] = []
        has_image = False
        has_document = False
        for upload in uploads:
            raw = upload.getvalue()
            ext = validate_upload(upload.name, raw)
            if ext in IMAGE_EXTENSIONS:
                has_image = True
                selected_model = settings.vision_model
                with Image.open(io.BytesIO(raw)) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.thumbnail((1536, 1536))
                    buf = io.BytesIO()
                    image.save(buf, format="JPEG", quality=88, optimize=True)
                    image_bytes = buf.getvalue()
                    image_payloads.append(base64.b64encode(image_bytes).decode("utf-8"))
                if persistent:
                    info = save_chat_image(uid, upload.name, raw)
                else:
                    info = {"filename": upload.name, "size_bytes": len(raw), "ephemeral": True}
                attachment_info.append(info)
            elif ext in DOCUMENT_EXTENSIONS:
                has_document = True
                if persistent:
                    doc_id, _, _ = save_document(
                        uid,
                        upload.name,
                        raw,
                        upload.type,
                        domain=st.session_state.domain,
                        visibility="private",
                        tags=["chat-attachment"],
                    )
                    persistent_doc_ids.append(doc_id)
                    attachment_info.append({"filename": upload.name, "document_id": doc_id, "size_bytes": len(raw)})
                else:
                    ephemeral_chunks.extend(process_ephemeral_document(upload.name, raw))
                    attachment_info.append({"filename": upload.name, "size_bytes": len(raw), "ephemeral": True})

        if not image_payloads and reuse_images:
            if persistent and cid:
                for message in reversed(get_messages(uid, cid, limit=settings.max_context_messages)):
                    attachments = object_list(message["attachment_json"])
                    for attachment in attachments:
                        path = safe_attachment_path(attachment.get("stored_path", ""), uid)
                        if path and path.suffix.lower() in IMAGE_EXTENSIONS:
                            with Image.open(path) as image:
                                image = ImageOps.exif_transpose(image).convert("RGB")
                                image.thumbnail((1536, 1536))
                                buf = io.BytesIO()
                                image.save(buf, format="JPEG", quality=88)
                                image_payloads.append(base64.b64encode(buf.getvalue()).decode("ascii"))
                    if image_payloads:
                        break
            elif not persistent:
                for message in reversed(st.session_state.ephemeral_messages):
                    if message.get("images"):
                        image_payloads = message["images"]
                        break
        if image_payloads:
            has_image = True
            selected_model = settings.vision_model
        if has_image:
            effective_mode = "Vision"
        elif has_document:
            effective_mode = "Documents"

        if persistent:
            previous = get_messages(uid, cid) if cid else []
            for message in previous:
                for attachment in object_list(message["attachment_json"]):
                    if isinstance(attachment, dict) and attachment.get("document_id"):
                        persistent_doc_ids.append(int(attachment["document_id"]))
            if persistent_doc_ids:
                sources = retrieve_chunks(uid, prompt, document_ids=list(set(persistent_doc_ids)))
            elif effective_mode == "Documents":
                sources = retrieve_chunks(uid, prompt)
        else:
            staged_sources = (st.session_state.ephemeral_sources + ephemeral_chunks)[-settings.max_retrieval_chunks:]
            if staged_sources:
                sources = retrieve_ephemeral(prompt, staged_sources)
            elif effective_mode == "Documents":
                sources = retrieve_chunks(uid, prompt)
        if sources or persistent_doc_ids or (not persistent and staged_sources):
            effective_mode = "Documents" if not has_image else "Vision"
        if effective_mode == "Documents" and not sources:
            st.warning("No matching document evidence was found. Try specific terms from the document, or use Study Lab for a summary.")
            return

        effective_prompt = build_evidence_prompt(prompt, sources, effective_mode) if sources else prompt[: settings.max_prompt_chars]

        with st.chat_message("user"):
            st.markdown(prompt)
            for info in attachment_info:
                st.caption(f"Attachment · {info.get('filename', 'file')}")

        if persistent:
            prior = get_messages(uid, cid, limit=settings.max_context_messages) if cid else []
            history = [
                {"role": item["role"], "content": str(item["content"])[: settings.max_history_message_chars]}
                for item in prior
                if item["role"] in {"user", "assistant"}
            ]
        else:
            history = [
                {"role": item["role"], "content": str(item["content"])[: settings.max_history_message_chars]}
                for item in st.session_state.ephemeral_messages[-settings.max_context_messages:]
                if item["role"] in {"user", "assistant"}
            ]

        if image_payloads and not model_ready(settings.vision_model):
            st.error(f"Vision model '{settings.vision_model}' is not installed in Ollama.")
            return
        if not ollama_online():
            st.error("The local Ollama engine is offline. Start Ollama and confirm the configured model is installed.")
            return
        if not model_ready(selected_model):
            st.error(f"Model '{selected_model}' is not installed in Ollama.")
            return

        system = {"role": "system", "content": make_system_prompt(user, effective_mode, prompt)}
        current: dict[str, Any] = {"role": "user", "content": effective_prompt}
        if image_payloads:
            current["images"] = image_payloads
        ollama_messages = [system, *history, current]

        with st.chat_message("assistant"):
            status_box = st.empty()
            output = st.empty()
            status_box.markdown('<div class="z-small">● Local model generating…</div>', unsafe_allow_html=True)
            parts: list[str] = []
            start = time.perf_counter()
            try:
                last_render = 0.0
                for token in chat_stream(selected_model, ollama_messages, user_id=uid,
                    on_wait=lambda ahead: status_box.info(f"Waiting for the laptop AI · {ahead} request(s) ahead")):
                    parts.append(token)
                    now = time.perf_counter()
                    if now - last_render >= 0.06:
                        output.markdown("".join(parts))
                        last_render = now
                reply = "".join(parts).strip() or "The local model returned an empty response."
                output.markdown(reply)
                elapsed = time.perf_counter() - start
                status_box.markdown(f'<div class="z-small">✓ Ready · {elapsed:.1f}s · {html.escape(selected_model)}</div>', unsafe_allow_html=True)
                _display_sources(sources)
            except requests.RequestException as exc:
                status_box.empty()
                st.error(f"Local AI request failed: {exc}")
                return

        if persistent:
            st.session_state.conversation_id = save_exchange(uid, cid, prompt, reply, domain=st.session_state.domain, workspace=st.session_state.deployment_profile, model=selected_model, mode=effective_mode, attachments=attachment_info, sources=sources)
        else:
            st.session_state.ephemeral_sources = staged_sources
            st.session_state.ephemeral_messages.append({"role": "user", "content": prompt, "attachments": attachment_info, "sources": sources, "images": image_payloads if uploads else []})
            st.session_state.ephemeral_messages.append({"role": "assistant", "content": reply, "attachments": [], "sources": sources})
        exchange_saved = True
        st.session_state.pop("failed_chat_prompt", None)
        st.session_state.upload_generation = st.session_state.get("upload_generation", 0) + 1
        st.rerun()

    except Exception as exc:
        st.error(f"Could not process this request safely: {exc}")
    finally:
        if persistent and not exchange_saved:
            remove_chat_attachments(attachment_info, uid)


# -----------------------------------------------------------------------------
# Knowledge base
# -----------------------------------------------------------------------------
def page_knowledge(user: Any) -> None:
    topbar(user)
    uid = int(user["id"])
    render_art_header("A home for your knowledge.", "Bring your files together. Find the ideas that matter.", label="KNOWLEDGE / LIBRARY", artwork="knowledge-studio.png", variant="z-section-hero")
    st.caption("Build an offline knowledge base. Private files are visible only to you; shared files are published by administrators for all local users.")

    with st.container(border=True):
        st.markdown("### Add knowledge")
        upload = st.file_uploader(
            "PDF, DOCX, TXT, MD, PNG, JPG, JPEG, WEBP",
            type=[x.lstrip(".") for x in sorted(ALLOWED_EXTENSIONS)],
            key="knowledge_upload",
        )
        c1, c2, c3 = st.columns([1.2, 1, 1.2])
        with c1:
            file_domain = st.selectbox("Domain", DOMAIN_NAMES, index=DOMAIN_NAMES.index(st.session_state.domain), key="knowledge_domain")
        with c2:
            visibility_options = ["private", "shared"] if user_is_admin(user) else ["private"]
            visibility = st.selectbox("Visibility", visibility_options, key="knowledge_visibility")
        with c3:
            tags_text = st.text_input("Tags", placeholder="grade-11, physics, policy", key="knowledge_tags")
        if upload and st.button("Process and index locally", width="stretch", key="knowledge_process"):
            try:
                tags = [x.strip() for x in tags_text.split(",") if x.strip()]
                with st.status("Extracting and indexing…", expanded=True) as status:
                    doc_id, count, state = save_document(
                        uid,
                        upload.name,
                        upload.getvalue(),
                        upload.type,
                        domain=file_domain,
                        visibility=visibility,
                        tags=tags,
                    )
                    if state == "duplicate":
                        status.update(label=f"Already indexed as document #{doc_id}", state="complete")
                    else:
                        status.write(f"Indexed {count} chunks")
                        status.update(label=f"Document ready · {state}", state="complete")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    docs = list_documents(uid)
    if not docs:
        st.info("No indexed documents yet.")
        return

    st.markdown("### Local library")
    query = st.text_input("Find a document", placeholder="Search filenames, subjects, or tags…")
    docs = [d for d in docs if query.casefold() in (d["filename"] + d["domain"] + d["tags_json"]).casefold()]
    if not docs:
        st.info("No documents match this search.")
    for doc in docs:
        owner = "you" if int(doc["user_id"]) == uid else doc["owner_name"]
        tags = []
        try:
            tags = json.loads(doc["tags_json"] or "[]")
        except Exception:
            pass
        c1, c2, c3, c4 = st.columns([4.2, 1.3, 1.1, 1])
        with c1:
            badge = "SHARED" if doc["visibility"] == "shared" else "PRIVATE"
            st.markdown(f"**{doc['filename']}** · `{badge}`")
            st.caption(f"{doc['domain']} · owner: {owner} · {doc['size_bytes']/1024/1024:.2f} MB · {doc['status']}" + (f" · tags: {', '.join(tags[:6])}" if tags else ""))
        with c2:
            if st.button("Preview", key=f"preview_doc_{doc['id']}"):
                st.session_state.preview_document_id = int(doc["id"])
        with c3:
            if st.button("Ask", key=f"ask_doc_{doc['id']}"):
                st.session_state.page = "Research"
                st.session_state.preselect_doc_id = int(doc["id"])
                st.rerun()
        with c4:
            can_delete = int(doc["user_id"]) == uid or user_is_admin(user)
            confirmed = st.checkbox("Confirm", key=f"confirm_doc_{doc['id']}") if can_delete else False
            if can_delete and st.button("Delete", disabled=not confirmed, key=f"delete_doc_{doc['id']}"):
                try:
                    delete_stored_document(uid, int(doc["id"]), is_admin=user_is_admin(user))
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    preview_id = st.session_state.get("preview_document_id")
    if preview_id:
        preview = document_preview(uid, int(preview_id), max_chars=7000)
        if preview:
            with st.expander(f"Preview · {preview['filename']}", expanded=True):
                st.text(preview["text"] or "No extracted text is available for this file.")


# -----------------------------------------------------------------------------
# Research
# -----------------------------------------------------------------------------
def render_generated_result(user: Any, kind: str) -> None:
    result = st.session_state.get(f"{kind}_result")
    if not result:
        return
    st.subheader(result["title"])
    st.markdown(result["answer"])
    _display_sources(result["sources"])
    with st.container(horizontal=True):
        if st.button("Saved" if result.get("saved") else "Save output", disabled=bool(result.get("saved")), key=f"save_{kind}_output"):
            save_output(int(user["id"]), kind, result["title"], result["answer"], result["ids"])
            result["saved"] = True
            st.rerun()
        st.download_button("Download Markdown", result["answer"], file_name=f"zoderise_{kind}.md", mime="text/markdown", key=f"download_{kind}")


def _run_ai_block(user: Any, mode: str, question: str, sources: Sequence[dict[str, Any]], model: Optional[str] = None) -> str:
    model = model or settings.text_model
    if not ollama_online():
        raise RuntimeError("Ollama is offline.")
    if not model_ready(model):
        raise RuntimeError(f"Model '{model}' is not installed.")
    prompt = build_evidence_prompt(question, sources, mode)
    messages = [
        {"role": "system", "content": make_system_prompt(user, mode, question)},
        {"role": "user", "content": prompt},
    ]
    placeholder = st.empty()
    parts: list[str] = []
    last_render = 0.0
    for token in chat_stream(model, messages, user_id=int(user["id"]),
        on_wait=lambda ahead: placeholder.info(f"Waiting for the laptop AI · {ahead} request(s) ahead")):
        parts.append(token)
        now = time.perf_counter()
        if now - last_render >= 0.06:
            placeholder.markdown("".join(parts))
            last_render = now
    reply = "".join(parts).strip() or "The local model returned an empty response."
    placeholder.markdown(reply)
    return reply


def page_research(user: Any) -> None:
    topbar(user)
    uid = int(user["id"])
    render_art_header("Go beyond the first answer.", "Connect ideas across your documents with evidence you can inspect.", label="RESEARCH / DISCOVERY", artwork="knowledge-studio.png", variant="z-section-hero")
    st.caption("Compare and synthesize information from your private library and administrator-shared local sources.")
    docs = list_documents(uid)
    if not docs:
        st.info("Add at least one file in Knowledge Center first.")
        return
    options = [int(d["id"]) for d in docs]
    default_ids: list[int] = []
    pre = st.session_state.pop("preselect_doc_id", None)
    if pre in options:
        default_ids = [pre]
    selected = st.multiselect(
        "Research sources",
        options=options,
        default=default_ids,
        format_func=lambda doc_id: next((d["filename"] for d in docs if int(d["id"]) == doc_id), str(doc_id)),
    )
    st.caption("No files selected: search all documents you can access. Select files to limit the evidence.")
    question = st.text_area("Research question", placeholder="Compare the main findings, explain disagreements, and cite the local evidence.", height=120)
    if st.button("Run local research", width="stretch", key="research_run") and question.strip():
        try:
            sources = retrieve_chunks(uid, question, top_k=max(settings.rag_top_k, 8), document_ids=selected or None)
            if not sources:
                st.warning("No sufficiently relevant evidence was retrieved.")
                return
            st.markdown("### Retrieved evidence")
            _display_sources(sources)
            st.markdown("### Synthesis")
            answer = _run_ai_block(user, "Research", question, sources)
            st.session_state.research_result = {"title": question[:100], "answer": answer, "sources": sources, "ids": sorted({s["document_id"] for s in sources})}
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


    render_generated_result(user, "research")

# -----------------------------------------------------------------------------
# Study Lab
# -----------------------------------------------------------------------------
def _study_sources(user_id: int, doc_ids: Sequence[int], max_sources: int = 12) -> list[dict[str, Any]]:
    rows = get_retrieval_rows(user_id, doc_ids)
    # Round-robin documents so the first file cannot consume the entire prompt.
    grouped: dict[int, list] = {}
    for row in rows:
        grouped.setdefault(int(row["document_id"]), []).append(row)
    ordered = []
    while grouped and len(ordered) < max_sources:
        for document_id in list(grouped):
            ordered.append(grouped[document_id].pop(0))
            if not grouped[document_id]:
                del grouped[document_id]
            if len(ordered) >= max_sources:
                break
    excerpt_limit = max(100, min(900, (settings.ai_input_chars - 4500) // max(1, len(ordered)) - 130))
    sources: list[dict[str, Any]] = []
    used = 0
    for row in ordered:
        text = str(row["text"])[:excerpt_limit]
        if used + len(text) > settings.max_rag_context_chars and sources:
            break
        sources.append(
            {
                "filename": row["filename"],
                "page": row["page"],
                "text": text,
                "score": 1.0,
                "document_id": int(row["document_id"]),
            }
        )
        used += len(text)
        if len(sources) >= max_sources:
            break
    return sources


def page_study(user: Any) -> None:
    topbar(user)
    uid = int(user["id"])
    render_art_header("Make understanding stick.", "Shape your learning material into something you can practise and remember.", label="STUDY / LEARNING", artwork="study-atelier.png", variant="z-section-hero")
    st.caption("Turn local school or training documents into summaries, quizzes, flashcards, lesson plans, key terms, and practice problems.")
    st.caption("Uses bounded excerpts from up to 12 sources; it does not read every page of long files in one answer. Select fewer files for more detail.")
    docs = list_documents(uid)
    if not docs:
        st.info("Add learning material in Knowledge Center first.")
        return
    ids = [int(d["id"]) for d in docs]
    selected = st.multiselect(
        "Study sources",
        ids,
        format_func=lambda doc_id: next((d["filename"] for d in docs if int(d["id"]) == doc_id), str(doc_id)),
        key="study_sources",
    )
    task = st.selectbox("Generate", ["Structured summary", "Quiz with answers", "Flashcards", "Lesson plan", "Key terms", "Practice problems"])
    level = st.selectbox("Difficulty", ["Easy", "Standard", "Advanced"])
    extra = st.text_area("Extra instructions (optional)", placeholder="Example: focus on formulas and definitions; write in Dari; make 15 questions.")
    if st.button("Generate study material", width="stretch", key="study_generate"):
        if not selected:
            st.warning("Select at least one source.")
            return
        sources = _study_sources(uid, selected)
        if not sources:
            st.warning("No readable indexed content was found in the selected files.")
            return
        task_prompt = (
            f"Create a {level.lower()} {task.lower()} using only the supplied local source material where source-specific facts are needed. "
            "Make the output clear, classroom-ready, and cite [1], [2], etc. when making claims tied to the source. "
            f"Additional instructions: {extra.strip() or 'None.'}"
        )
        try:
            st.markdown("### Generated material")
            answer = _run_ai_block(user, "Study", task_prompt, sources)
            title = f"{task} · {time.strftime('%Y-%m-%d')}"
            st.session_state.study_result = {"title": title, "answer": answer, "sources": sources, "ids": selected}
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


    render_generated_result(user, "study")

# -----------------------------------------------------------------------------
# Local tools
# -----------------------------------------------------------------------------
def page_tools(user: Any) -> None:
    topbar(user)
    st.markdown("## Offline Tools")
    st.caption("Small deterministic utilities that do not require the AI model.")
    calc, units, dev = st.tabs(["Calculator", "Unit converter", "Developer utilities"])
    with calc:
        expression = st.text_input("Expression", placeholder="sqrt(144) + 5 * 3")
        if st.button("Calculate", key="calc_run") and expression.strip():
            try:
                st.success(f"Result: {safe_calculate(expression)}")
            except Exception as exc:
                st.error(str(exc))
    with units:
        group = st.selectbox("Unit group", list(UNIT_GROUPS), key="unit_group")
        unit_names = list(UNIT_GROUPS[group])
        c1, c2, c3 = st.columns(3)
        with c1:
            value = st.number_input("Value", value=1.0)
        with c2:
            from_unit = st.selectbox("From", unit_names)
        with c3:
            to_unit = st.selectbox("To", unit_names, index=min(1, len(unit_names)-1))
        result = convert_unit(group, float(value), from_unit, to_unit)
        st.info(f"{value:g} {from_unit} = {result:g} {to_unit}")
    with dev:
        hash_text = st.text_area("SHA-256 text", key="hash_text")
        if st.button("Hash text", key="hash_run"):
            st.code(sha256_text(hash_text))
        json_text = st.text_area("JSON formatter", key="json_text", height=180)
        if st.button("Format JSON", key="json_run") and json_text.strip():
            try:
                st.code(format_json(json_text), language="json")
            except Exception as exc:
                st.error(str(exc))


# -----------------------------------------------------------------------------
# Saved outputs
# -----------------------------------------------------------------------------
def page_saved(user: Any) -> None:
    topbar(user)
    uid = int(user["id"])
    st.markdown("## Saved Library")
    tabs = st.tabs(["Bookmarks", "Research & Study"])
    with tabs[0]:
        bookmarks = list_bookmarks(uid)
        if not bookmarks:
            st.info("No saved chat answers yet.")
        for item in bookmarks:
            with st.expander(f"{item['conversation_title']} · {time.strftime('%Y-%m-%d %H:%M', time.localtime(item['created_at']))}"):
                st.markdown(item["content"])
                if st.button("Remove bookmark", key=f"remove_bm_{item['id']}"):
                    remove_bookmark(uid, int(item["id"]))
                    st.rerun()
    with tabs[1]:
        outputs = list_saved_outputs(uid)
        if not outputs:
            st.info("No saved research or study outputs yet.")
        for item in outputs:
            with st.expander(f"{item['kind'].title()} · {item['title']}"):
                st.markdown(item["content"])
                st.download_button(
                    "Download Markdown",
                    item["content"],
                    file_name=f"zoderise_{item['kind']}_{item['id']}.md",
                    mime="text/markdown",
                    key=f"download_output_{item['id']}",
                )
                if st.button("Delete saved output", key=f"delete_output_{item['id']}"):
                    delete_saved_output(uid, int(item["id"]))
                    st.rerun()


# -----------------------------------------------------------------------------
# Account and settings
# -----------------------------------------------------------------------------
def page_account(user: Any) -> None:
    topbar(user)
    uid = int(user["id"])
    st.markdown("## Account")
    st.markdown(
        f"<div class='z-card'><div class='z-label'>LOCAL IDENTITY</div><div class='z-value'>{html.escape(user['name'])}</div><div class='z-small'>@{html.escape(user['username'])} · {html.escape(user['email'])} · {html.escape(user['role'])}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Profile")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name", value=user["name"], key="account_name")
        organization = st.text_input("Organization", value=user["organization"], key="account_org")
    with c2:
        department = st.text_input("Department / class", value=user["department"], key="account_dept")
        grade = st.text_input("Grade / team", value=user["grade_level"], key="account_grade")
    if st.button("Save profile", width="stretch", key="account_save_profile"):
        ok, msg = update_user_profile(uid, name=name, organization=organization, department=department, grade_level=grade)
        (st.success if ok else st.error)(msg)
        if ok:
            st.rerun()

    st.markdown("### Change password")
    current = st.text_input("Current password", type="password", key="password_current")
    new = st.text_input("New password", type="password", key="password_new")
    confirm = st.text_input("Confirm new password", type="password", key="password_confirm")
    if st.button("Change password", width="stretch", key="password_change"):
        if new != confirm:
            st.error("New passwords do not match.")
        else:
            ok, msg = change_password(uid, current, new)
            if ok:
                st.session_state.clear()
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("### Data controls")
    if st.session_state.privacy_mode == "Ephemeral":
        st.info("Current chat is session-only. Starting a new session or logging out clears the in-memory chat.")
        if st.button("Clear current ephemeral chat", width="stretch", key="clear_ephemeral"):
            wipe_ephemeral_chat()
            st.rerun()
    confirm_purge = st.checkbox("I understand that purging saved chat history is permanent.", key="account_purge_confirm")
    if st.button("Purge saved chat history", width="stretch", key="account_purge"):
        if not confirm_purge:
            st.warning("Confirm first.")
        else:
            attachments = collect_chat_attachments(uid)
            remove_chat_attachments(attachments, uid)
            removed = purge_chat_history(uid)
            st.session_state.conversation_id = None
            st.success(f"Purged {removed} saved conversation(s).")

    st.markdown("### Danger zone")
    delete_confirm = st.checkbox("Delete my local account, conversations, files, and saved outputs.", key="delete_account_confirm")
    if st.button("Delete my account", width="stretch", key="delete_account_button"):
        if not delete_confirm:
            st.warning("Confirm account deletion first.")
        else:
            try:
                delete_account_records(uid)
            except ValueError as exc:
                st.error(str(exc))
                return
            remove_user_storage(uid)
            st.session_state.clear()
            st.rerun()


def page_settings(user: Any) -> None:
    topbar(user)
    uid = int(user["id"])
    st.markdown("## Settings")
    prefs = get_preferences(uid)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Experience")
        st.caption("Choose subtle movement or a still workspace. System reduced-motion preferences are always respected.")
        motion_options = ["Reduced", "Balanced", "Immersive"]
        effective_motion = st.session_state.get("appearance", {}).get("motion", prefs["animation"])
        animation = st.selectbox("Motion style", motion_options, index=motion_options.index(effective_motion if effective_motion in motion_options else "Balanced"))
        reduced = st.checkbox("Reduce motion", value=effective_motion == "Reduced")
        st.caption("More device-specific design controls are available in Appearance.")
        detail = st.selectbox("Answer depth", ["Concise", "Balanced", "Deep"], index=["Concise", "Balanced", "Deep"].index(prefs["detail_level"] if prefs["detail_level"] in {"Concise", "Balanced", "Deep"} else "Balanced"))
        profile = st.selectbox("Deployment profile", DEPLOYMENT_PROFILES, index=DEPLOYMENT_PROFILES.index(prefs["deployment_profile"] if prefs["deployment_profile"] in DEPLOYMENT_PROFILES else "School"))
    with c2:
        st.markdown("### AI defaults")
        language = st.selectbox("Default language", LANGUAGES, index=LANGUAGES.index(prefs["language"] if prefs["language"] in LANGUAGES else "English"), key="settings_language")
        mode = st.selectbox("Default mode", MODES, index=MODES.index(prefs["mode"] if prefs["mode"] in MODES else "Chat"), key="settings_mode")
        privacy = st.selectbox("Default privacy", PRIVACY_MODES, index=PRIVACY_MODES.index(prefs["privacy_mode"] if prefs["privacy_mode"] in PRIVACY_MODES else "Ephemeral"), key="settings_privacy")
        models = [settings.text_model] + ([settings.vision_model] if settings.vision_model != settings.text_model else [])
        default_model = settings.vision_model if mode == "Vision" else settings.text_model
        st.caption("Model selection is automatic: images use Vision; text uses the text model.")
    if st.button("Save settings", width="stretch", key="settings_save"):
        update_preferences(
            uid,
            animation=animation,
            reduced_motion=int(reduced),
            detail_level=detail,
            deployment_profile=profile,
            language=language,
            mode=mode,
            privacy_mode=privacy,
            model=default_model,
        )
        st.session_state.animation = animation
        st.session_state.reduced_motion = reduced
        if st.session_state.get("appearance"):
            save_appearance({**st.session_state.appearance, "motion": "Reduced" if reduced else animation})
        st.session_state.detail_level = detail
        st.session_state.deployment_profile = profile
        st.session_state.language = language
        st.session_state.mode = mode
        if st.session_state.privacy_mode != privacy:
            wipe_ephemeral_chat()
            st.session_state.conversation_id = None
        st.session_state.privacy_mode = privacy
        st.session_state.model = default_model
        st.success("Settings saved locally.")
        st.rerun()


# -----------------------------------------------------------------------------
# About / diagnostics / admin
# -----------------------------------------------------------------------------
def page_about(user: Any) -> None:
    topbar(user)
    st.markdown("## About ZODERISE HORIZON")
    st.info("Created by Zubair Zahidi, CEO of Zoderise Company, Kabul, Afghanistan. Built for Kardan Private School. Powered by separately developed local Ollama models.")
    st.markdown(
        """
        <div class="z-card">
          <div class="z-brand">ZODERISE HORIZON</div>
          <div class="z-sub">SOVEREIGN LOCAL INTELLIGENCE</div>
          <p class="z-lead">A local-first AI workspace designed for education, business, company operations, research, and private knowledge. It uses Ollama for local inference, SQLite for local application data, lexical document retrieval, optional OCR, and separate user accounts.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### What this version adds")
    st.markdown(
        """
- Expanded domains: mathematics, physics, chemistry, biology/health, science, computer science, AI/technology, cybersecurity, geography, history, agriculture, business/operations, engineering/robotics, languages/writing, and general intelligence.
- Two privacy behaviors: **Ephemeral** chat for session-only retention and **Persistent** chat for saved work.
- Private and administrator-shared knowledge libraries with local document retrieval and source evidence.
- Research Desk, Study Lab, offline tools, saved answers, role-aware accounts, admin governance, diagnostics, and safer local endpoint enforcement.
- More accurate product claims: local AI can still make mistakes; low temperature does not guarantee zero hallucinations or perfect determinism.
        """
    )
    st.markdown("### Security boundary")
    st.info("ZODERISE is local-first, not magically invulnerable. Protect the host OS with full-disk encryption, strong Windows accounts, updates, backups, and firewall rules. If you expose Streamlit on a LAN, place it behind trusted network controls and TLS rather than treating localhost assumptions as network security.")


def system_snapshot() -> dict[str, Any]:
    snap: dict[str, Any] = {
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cwd": str(Path.cwd()),
    }
    if psutil:
        try:
            snap["cpu_percent"] = psutil.cpu_percent(interval=0.08)
            snap["ram_percent"] = psutil.virtual_memory().percent
            snap["disk_percent"] = psutil.disk_usage(str(settings.db_path.parent)).percent
            snap["cpu_count"] = psutil.cpu_count(logical=True)
        except Exception:
            pass
    return snap


def page_diagnostics(user: Any) -> None:
    topbar(user)
    if not user_is_admin(user):
        st.error("Administrator access required.")
        return
    st.markdown("## System diagnostics")
    status = model_status()
    caps = file_capabilities()
    snap = system_snapshot()
    items = [
        ("Application", settings.app_version),
        ("Ollama", "ONLINE" if status["online"] else "OFFLINE"),
        ("Text model", "READY" if status["text_ready"] else "MISSING"),
        ("Vision model", "READY" if status["vision_ready"] else "MISSING"),
        ("OCR", "READY" if caps["ocr_available"] else "OPTIONAL / MISSING"),
        ("CPU", f"{snap.get('cpu_percent', '—')}%" if "cpu_percent" in snap else "Unavailable"),
        ("RAM", f"{snap.get('ram_percent', '—')}%" if "ram_percent" in snap else "Unavailable"),
    ]
    cols = st.columns(4)
    for index, (label, value) in enumerate(items):
        with cols[index % 4]:
            st.markdown(f"<div class='z-card'><div class='z-label'>{html.escape(label)}</div><div class='z-value'>{html.escape(str(value))}</div></div>", unsafe_allow_html=True)

    st.markdown("### Configuration checks")
    issues = security_configuration_issues()
    if not issues:
        st.success("No high-priority configuration warning was detected by the built-in checker.")
    else:
        for issue in issues:
            st.warning(issue)

    st.markdown("### Host and parser details")
    st.caption(f"Laptop profile: {settings.ai_num_ctx:,} context tokens · batch {settings.ai_num_batch} · one request at a time · model release after each answer.")
    try:
        running = requests.get(f"{settings.ollama_base_url}/api/ps", timeout=3).json().get("models", [])
        for model in running:
            if model.get("size_vram", 0) == 0:
                st.warning(f"{model.get('name', 'Model')} is using the CPU. Use the project launcher for the isolated GPU-compatible Ollama process.")
            else:
                st.info(f"{model.get('name', 'Model')} uses {model['size_vram'] / 1024**3:.1f} GB of GPU memory.")
    except requests.RequestException:
        pass
    st.json({
        "os": snap.get("os"),
        "python": snap.get("python"),
        "server_host": settings.server_host,
        "server_port": settings.server_port,
        "ollama_endpoint": status["endpoint"],
        "ollama_endpoint_is_loopback": status["local_endpoint"],
        "models": status["models"],
        "file_capabilities": caps,
    })
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Run maintenance", width="stretch", key="diag_maintenance"):
            result = cleanup_maintenance()
            st.success(f"Cleaned {result['sessions']} session rows, {result['audit_logs']} old audit rows, and {result.get('login_attempts', 0)} stale login-attempt rows.")
    with c2:
        if st.button("Compact local database", width="stretch", key="diag_compact"):
            with st.spinner("Compacting…"):
                compact_database()
            st.success("Database compacted.")


def page_admin(user: Any) -> None:
    topbar(user)
    if not user_is_admin(user):
        st.error("Administrator access required.")
        return
    uid = int(user["id"])
    st.markdown("## Administration")
    stats = dashboard_stats()
    cols = st.columns(3)
    for index, (label, value) in enumerate(stats.items()):
        with cols[index % 3]:
            st.metric(label.replace("_", " ").title(), value)

    hub_tab, users_tab, sessions_tab, audit_tab, backup_tab = st.tabs(["Hub access", "Users", "Sessions", "Audit log", "Backups"])
    with hub_tab:
        urls = hub_urls(settings.server_port)
        shared = settings.server_host not in {"127.0.0.1", "localhost", "::1"}
        status = model_status()
        c1, c2, c3 = st.columns(3)
        c1.metric("Hub", "ONLINE" if shared else "LOCAL ONLY")
        c2.metric("AI brain", "READY" if status["text_ready"] else "OFFLINE")
        queue_state = inference_queue.snapshot()
        c3.metric("AI queue", f"{queue_state['waiting']} waiting" if queue_state["waiting"] else ("Busy" if queue_state["busy"] else "Ready"))
        if not shared:
            st.info("Hub mode is off. In the Windows app, choose **Workspace → Enable Hub on this computer** after creating an administrator. Developers can use **start_hub.bat**.")
        elif not urls:
            st.warning("Hub mode is running, but no private IPv4 address was detected. Connect Wi-Fi/Ethernet and refresh this page.")
        else:
            st.success("This laptop is the Zoderise AI brain. Ollama remains private on the laptop; approved users reach only this application.")
            selected_url = st.selectbox("Connection address", urls, key="hub_connection_url")
            left, right = st.columns([1, 2])
            with left:
                image = qr_png(selected_url)
                if image:
                    st.image(image, caption="Scan on the same trusted Wi-Fi", width=240)
                else:
                    st.warning("Install the QR dependency with setup_windows.bat to show the scan code.")
            with right:
                st.code(selected_url, language=None)
                st.markdown("**Connect a phone or browser**")
                st.markdown("1. Join the same trusted Wi-Fi.\n2. Scan the code or enter the address.\n3. Create/sign in to an account.\n4. An administrator approves new LAN accounts here.")
                st.markdown("**Connect the Windows app**")
                st.markdown("Open **Workspace → Connect to Hub**, paste this address, then sign in. The client computer needs no Python or Ollama.")
        st.warning("LAN traffic uses plain HTTP unless you add TLS. Do not forward port 8501 or port 11434 through the router. For access outside this Wi-Fi, use a trusted VPN such as Tailscale or an HTTPS reverse proxy, then paste its HTTPS address into the Windows app.")
        st.caption("Keep the host awake and connected. If Windows asks about network access, allow the app only on Private networks. Each person should have their own account.")
        st.caption(f"Host data: {settings.db_path.parent}. The developer launcher and Windows app may use different data directories unless configured to share ZODERISE_DATA_HOME. Do not run two host servers against one data directory.")
    with users_tab:
        for item in list_users():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2.2, 1.5, 1.4, 1.2])
                with c1:
                    st.markdown(f"**{item['name']}** · `@{item['username']}`")
                    st.caption(f"{item['email']} · {item['organization'] or 'No organization'} · {item['department'] or 'No department'}")
                with c2:
                    role = st.selectbox("Role", ROLES, index=ROLES.index(item["role"]) if item["role"] in ROLES else 0, key=f"admin_role_{item['id']}")
                with c3:
                    active = st.checkbox("Active", value=bool(item["is_active"]), key=f"admin_active_{item['id']}")
                    approved = st.checkbox("Approved", value=bool(item["approved"]), key=f"admin_approved_{item['id']}")
                with c4:
                    if int(item["id"]) != uid and st.button("Apply", width="stretch", key=f"admin_apply_{item['id']}"):
                        admin_update_user(uid, int(item["id"]), role=role, active=active, approved=approved)
                        st.rerun()
                    if int(item["id"]) != uid and item["role"] != "admin":
                        confirm = st.checkbox("Delete", key=f"admin_delete_confirm_{item['id']}")
                        if st.button("Remove user", width="stretch", key=f"admin_delete_{item['id']}"):
                            if not confirm:
                                st.warning("Tick Delete first.")
                            else:
                                ok, msg = admin_delete_user(uid, int(item["id"]))
                                if ok:
                                    remove_user_storage(int(item["id"]))
                                (st.success if ok else st.error)(msg)
                                if ok:
                                    st.rerun()
    with sessions_tab:
        sessions = list_active_sessions()
        if not sessions:
            st.info("No active sessions.")
        else:
            st.caption("Session records identify accounts and sign-in times; the application does not collect device fingerprints.")
            for item in sessions:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.4, 2, 1])
                    with c1:
                        st.markdown(f"**{item['name']}** · `@{item['username']}`")
                        st.caption(str(item["role"]).title())
                    with c2:
                        st.caption(f"Signed in {time.strftime('%Y-%m-%d %H:%M', time.localtime(item['created_at']))}")
                        st.caption(f"Expires {time.strftime('%Y-%m-%d %H:%M', time.localtime(item['expires_at']))}")
                    with c3:
                        if st.button("Revoke", key=f"revoke_session_{item['id']}", width="stretch"):
                            admin_revoke_session(uid, int(item["id"]))
                            st.rerun()
    with audit_tab:
        logs = recent_audit(150)
        if not logs:
            st.info("No audit records.")
        for log in logs:
            actor = log["actor_name"] or "system"
            st.caption(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log['created_at']))} · {actor} · {log['action']} · {log['metadata_json'] or '{}'}")
    with backup_tab:
        st.markdown("### Host backup")
        st.caption("Creates an on-disk snapshot of the database and uploaded files, then verifies every file. The ZIP is unencrypted and contains private account and document data. Keep the host disk protected and copy backups to protected storage.")
        if st.button("Create and verify backup", key="admin_create_backup"):
            try:
                with st.spinner("Snapshotting and checking files…"):
                    backup_path = create_backup()
                st.success(f"Verified backup: {backup_path}")
                audit(uid, "backup_created", {"file": backup_path.name})
            except Exception as exc:
                st.error(f"Backup failed: {exc}")
        backup_dir = settings.db_path.parent / "backups"
        if backup_dir.is_dir():
            for backup_path in sorted(backup_dir.glob("zoderise-*.zip"), reverse=True)[:5]:
                col1, col2 = st.columns([4, 1])
                col1.caption(f"{backup_path.name} · {backup_path.stat().st_size / 1024**2:.1f} MB")
                if col2.button("Verify", key=f"verify_{backup_path.name}"):
                    try:
                        manifest = verify_backup(backup_path)
                        st.success(f"Verified {len(manifest['files'])} files in {backup_path.name}")
                    except Exception as exc:
                        st.error(f"Verification failed: {exc}")


# -----------------------------------------------------------------------------
# Routing
# -----------------------------------------------------------------------------
page = st.session_state.page
if page == "Home":
    page_home(user)
elif page == "History":
    page_history(user)
elif page == "Chat":
    page_chat(user)
elif page == "Prompt Studio":
    topbar(user)
    render_art_header("Designed for your next lesson.", "From a blank page to a thoughtful brief. Shape the details, then make it yours.", label="PROMPT STUDIO / TEACH & LEARN", artwork="study-atelier.png", variant="z-section-hero")
    render_classroom_studio()
elif page == "Appearance":
    topbar(user)
    render_appearance_page()
elif page == "Knowledge":
    page_knowledge(user)
elif page == "Research":
    page_research(user)
elif page == "Study Lab":
    page_study(user)
elif page == "Tools":
    page_tools(user)
elif page == "Saved":
    page_saved(user)
elif page == "Account":
    page_account(user)
elif page == "Settings":
    page_settings(user)
elif page == "About":
    page_about(user)
elif page == "Diagnostics":
    page_diagnostics(user)
elif page == "Admin":
    page_admin(user)
else:
    st.session_state.page = "Home"
    st.rerun()

footer()
