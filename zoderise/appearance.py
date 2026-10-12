"""Validated browser-local appearance preferences. No credentials in browser storage."""
from __future__ import annotations

import json
import uuid
import streamlit as st

PALETTES = {
    "Midnight": {"bg": "#0b1020", "surface": "#142036", "sidebar": "#10192b", "text": "#edf1f7", "muted": "#b3c1d7", "line": "#3b4b65"},
    "Forest": {"bg": "#0b1817", "surface": "#152b29", "sidebar": "#102220", "text": "#eaf5ef", "muted": "#b3cec5", "line": "#365951"},
    "Graphite": {"bg": "#151619", "surface": "#23262d", "sidebar": "#191b20", "text": "#f0f1f4", "muted": "#bfc3cf", "line": "#494e5d"},
    "High contrast": {"bg": "#000000", "surface": "#111111", "sidebar": "#080808", "text": "#ffffff", "muted": "#e0e0e0", "line": "#8d96a8"},
}
ACCENTS = {"Iris": "#b6beff", "Gold": "#e8c48b", "Mint": "#88e0be", "Sky": "#8dd5fa", "Rose": "#efb0ce"}
OPTIONS = {
    "design": ["Editorial", "Modern"],
    "palette": list(PALETTES), "accent": list(ACCENTS),
    "density": ["Comfortable", "Compact"], "text_size": ["Standard", "Large", "Extra large"],
    "width": ["Balanced", "Wide", "Reading"], "artwork": ["Full", "Compact", "Hidden"],
    "motion": ["Reduced", "Balanced", "Immersive"], "start_page": ["Home", "Chat", "Prompt Studio", "Knowledge", "Study Lab"],
}
DEFAULTS = {"design": "Editorial", "palette": "Midnight", "accent": "Gold", "density": "Comfortable", "text_size": "Standard", "width": "Balanced", "artwork": "Full", "motion": "Balanced", "start_page": "Home", "focus": False}
PRESETS = {
    "Horizon": DEFAULTS,
    "Quiet reading": {**DEFAULTS, "palette": "Graphite", "width": "Reading", "artwork": "Hidden", "motion": "Reduced", "text_size": "Large"},
    "Forest studio": {**DEFAULTS, "palette": "Forest", "accent": "Mint", "artwork": "Compact"},
    "Phone essentials": {**DEFAULTS, "artwork": "Hidden", "motion": "Reduced", "density": "Compact", "start_page": "Chat"},
}


def normalize_appearance(raw: object) -> dict:
    values = raw if isinstance(raw, dict) else {}
    clean = dict(DEFAULTS)
    for key, options in OPTIONS.items():
        value = values.get(key)
        if isinstance(value, str) and value in options:
            clean[key] = value
    clean["focus"] = values.get("focus") is True
    return clean


_BRIDGE = st.components.v2.component(
    "zoderise_device_appearance",
    html='<span aria-hidden="true"></span>',
    js="""
export default function ({data, parentElement, setStateValue}) {
  const marker = parentElement.querySelector('span');
  if (!marker || !data) return;
  const key = 'zoderise.appearance.v1.' + data.user;
  if (!data.hydrated && marker.dataset.loaded !== key) {
    marker.dataset.loaded = key;
    try {
      const raw = localStorage.getItem(key);
      const prefs = raw && raw.length < 8192 ? JSON.parse(raw) : {};
      setStateValue('loaded', {prefs, available: true});
    } catch (_) { setStateValue('loaded', {prefs: {}, available: false}); }
  }
  if (data.write && data.write.token !== data.ack && marker.dataset.written !== data.write.token) {
    marker.dataset.written = data.write.token;
    try {
      localStorage.setItem(key, JSON.stringify(data.write.prefs));
      setStateValue('saved', {token: data.write.token, available: true});
    } catch (_) { setStateValue('saved', {token: data.write.token, available: false}); }
  }
}
""",
)


def sync_device_appearance(user_id: int) -> None:
    """Hydrate once per signed-in session, then persist explicit appearance saves."""
    result = _BRIDGE(
        key="device_appearance_bridge", height=1,
        data={"user": str(user_id), "hydrated": st.session_state.get("device_hydrated", False), "write": st.session_state.get("device_write"), "ack": st.session_state.get("device_ack")},
        on_loaded_change=lambda: None, on_saved_change=lambda: None,
    )
    loaded = result.loaded
    if isinstance(loaded, dict) and not st.session_state.get("device_hydrated"):
        st.session_state.appearance = normalize_appearance(loaded.get("prefs"))
        st.session_state.device_hydrated = True
        st.session_state.device_storage_available = bool(loaded.get("available"))
        if st.session_state.page == "Home" and not st.session_state.get("device_user_navigated"):
            st.session_state.page = st.session_state.appearance["start_page"]
    saved = result.saved
    if isinstance(saved, dict):
        st.session_state.device_ack = saved.get("token")
        st.session_state.device_storage_available = bool(saved.get("available"))


def save_appearance(values: dict) -> None:
    st.session_state.appearance = normalize_appearance(values)
    st.session_state.device_hydrated = True
    st.session_state.device_write = {"token": uuid.uuid4().hex, "prefs": st.session_state.appearance}


def appearance_css(raw: object) -> str:
    p = normalize_appearance(raw)
    c = PALETTES[p["palette"]]
    accent = ACCENTS[p["accent"]]
    width = {"Balanced": 1320, "Wide": 1720, "Reading": 960}[p["width"]]
    font = {"Standard": 16, "Large": 18, "Extra large": 20}[p["text_size"]]
    pad = 14 if p["density"] == "Compact" else 24
    css = f"""
    :root{{--z-surface:{c["surface"]};--z-bg:{c["bg"]};--z-accent:{accent};--z-gold:{accent};--z-muted:{c['muted']};--z-line:{c['line']}}}
    .stApp{{background:radial-gradient(ellipse at top right,{c['surface']},transparent 65%),{c['bg']};color:{c['text']}}}
    [data-testid="stSidebar"]{{background:{c['sidebar']};border-color:{c['line']}}}
    [data-testid="stMainBlockContainer"]{{max-width:{width}px}}
    [data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stChatMessageContent"]{{font-size:{font}px;line-height:1.75}}
    .z-card,[data-testid="stChatMessage"],[data-testid="stMetric"],div[class*="st-key-workspace_"]{{background:{c['surface']};border-color:{c['line']}!important}}
    [data-testid="stChatMessage"]{{padding:{pad}px}}
    .z-pill,.z-chip{{background:{c['surface']};border-color:{c['line']};color:{c['text']}}}
    .z-sub,.z-kicker,.z-eyebrow,.z-workspace-number span:last-child,[data-testid="stMetricValue"],.accent{{color:{accent}}}
    .z-lead,.z-small,.z-label,.z-footer{{color:{c['muted']}}}
    .stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]{{background:{accent};border-color:{accent};color:#101420}}
    button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{{outline:3px solid {accent}!important;outline-offset:3px}}
    [data-testid="stChatInput"]{{border-color:{accent};background:{c['surface']}}}
    [data-testid="stChatMessageContent"]{{overflow-wrap:anywhere;min-width:0}}
    [data-testid="stChatMessageContent"] pre{{overflow-x:auto;white-space:pre}}
    [data-testid="stChatMessageContent"] table{{display:block;max-width:100%;overflow-x:auto}}
    [data-testid="stChatMessageContent"] .katex-display{{overflow-x:auto;overflow-y:hidden}}
    @media(max-width:760px){{[data-testid="stMainBlockContainer"]{{padding-left:1rem;padding-right:1rem}}
    .z-top{{gap:8px}}.z-status-cluster{{gap:5px}}.z-pill{{font-size:.65rem}}
    .stButton button,.stDownloadButton button{{min-height:44px}}
    [data-testid="stChatMessage"]{{padding:12px}}[data-testid="stChatInput"] textarea{{font-size:16px!important}}
    .z-editorial-copy h1{{font-size:clamp(1.8rem,8vw,2.65rem)}}}}
    """
    if p["design"] == "Editorial":
        css += '.z-editorial-copy h1,.z-section-heading h2{font-family:Georgia,"Times New Roman",serif;letter-spacing:-.055em;font-weight:400!important}.z-editorial-copy h1{line-height:1.06}'
    if p["artwork"] == "Compact":
        css += '.z-editorial-hero{min-height:210px}.z-editorial-copy{padding:28px!important}.z-editorial-copy h1{font-size:2.5rem}.z-auth-hero{min-height:340px}'
    if p["artwork"] == "Hidden" or p["focus"]:
        css += '.z-editorial-hero{min-height:0;background:transparent;box-shadow:none;border:0}.z-editorial-hero img,.z-editorial-hero:after,.z-orbit,.z-art-credit{display:none}.z-editorial-copy{width:100%;padding:12px 0!important}.z-editorial-copy h1{font-size:2rem;margin:10px 0}.z-editorial-copy p{max-width:750px}'
    if p["focus"]:
        css += '.z-footer,.z-top .z-sub,.z-sculpture,.z-edition{display:none}'
    if p["motion"] == "Reduced" or p["focus"]:
        css += '.z-editorial-hero,.z-editorial-hero img,.z-orbit,.z-sculpture,.z-sculpture i{animation:none!important;transition:none!important}div[class*="st-key-workspace_"]:hover{transform:none!important}'
    return css


def render_appearance_page() -> None:
    current = normalize_appearance(st.session_state.get("appearance"))
    st.header("Make this space yours")
    st.caption("Appearance is saved for this account in this browser. Your phone and laptop can look different. Chat data stays on the host laptop.")
    if not st.session_state.get("device_storage_available", True):
        st.warning("Browser storage is unavailable. Changes apply to this session; export a profile to keep them.")
    st.subheader("Choose a look. Make it yours.")
    descriptions = ["Gold, glass, and editorial typography.", "Larger text and a distraction-free canvas.", "Soft mint highlights and a compact hero.", "Less decoration. More room on your phone."]
    names = list(PRESETS)
    for start in (0, 2):
        for col, name, description in zip(st.columns(2), names[start:start + 2], descriptions[start:start + 2]):
            p = normalize_appearance(PRESETS[name])
            palette, accent = PALETTES[p["palette"]], ACCENTS[p["accent"]]
            with col, st.container(border=True):
                st.html(f'<div class="z-preset-preview" style="--preview-bg:{palette["bg"]};--preview-surface:{palette["surface"]};--preview-accent:{accent}" aria-hidden="true"><div class="z-preset-sidebar"></div><div class="z-preset-title"></div><div class="z-preset-orb"></div><div class="z-preset-line"></div><div class="z-preset-tile"></div><div class="z-preset-tile second"></div></div>')
                st.markdown(f"**{name}**")
                st.caption(description)
                if st.button(f"Use {name}", key=f"quick_preset_{name}", width="stretch"):
                    save_appearance(PRESETS[name])
                    st.session_state.appearance_editor_generation = st.session_state.get("appearance_editor_generation", 0) + 1
                    st.rerun()
    with st.expander("Preset list"):
        preset = st.selectbox("Start from a design", list(PRESETS), key="appearance_preset")
        if st.button("Apply preset", key="apply_appearance_preset"):
            save_appearance(PRESETS[preset])
            st.session_state.appearance_editor_generation = st.session_state.get("appearance_editor_generation", 0) + 1
            st.rerun()
    st.subheader("Your current look")
    from .ui import render_art_header
    render_art_header("A little more you.", "This preview uses your saved colors, typography, artwork, and motion settings.", label=f'{current["palette"]} / {current["accent"]} / {current["design"]}', variant="z-section-hero")
    with st.container(horizontal=True):
        for label, motion in [("Quiet motion", "Reduced"), ("Gentle motion", "Balanced"), ("Moving 3D details", "Immersive")]:
            if st.button(label, key=f"quick_motion_{motion}", type="primary" if current["motion"] == motion else "secondary"):
                save_appearance({**current, "motion": motion})
                st.session_state.appearance_editor_generation = st.session_state.get("appearance_editor_generation", 0) + 1
                st.rerun()
    st.caption("Quiet stops decorative animation. Gentle adds short entrances. Moving 3D details animates the artwork on larger screens; phones keep a lighter view.")
    st.subheader("Fine-tune your space")
    generation = st.session_state.get("appearance_editor_generation", 0)
    with st.form(f"appearance_editor_{generation}"):
        values = {}
        left, right = st.columns(2)
        labels = {"design": "Design style", "palette": "Color palette", "accent": "Accent color", "density": "Spacing", "text_size": "Reading text size", "width": "Content width", "artwork": "Page artwork", "motion": "Motion style", "start_page": "Start page"}
        for index, (key, choices) in enumerate(OPTIONS.items()):
            with left if index % 2 == 0 else right:
                values[key] = st.selectbox(labels[key], choices, index=choices.index(current[key]))
        values["focus"] = st.checkbox("Focus layout — minimize decorative content", value=current["focus"])
        st.caption("Your operating system's reduced-motion preference always takes priority.")
        if st.form_submit_button("Save on this browser", type="primary"):
            save_appearance(values)
            st.rerun()
    with st.container(horizontal=True):
        st.download_button("Export appearance", json.dumps(current, indent=2), "zoderise-appearance.json", "application/json")
        if st.button("Reset appearance", key="reset_appearance"):
            save_appearance(DEFAULTS)
            st.session_state.appearance_editor_generation = generation + 1
            st.rerun()
    imported = st.file_uploader("Import an appearance profile", type=["json"], key="appearance_import")
    if imported is not None and st.button("Apply imported profile"):
        try:
            if imported.size > 8192:
                raise ValueError("Appearance files must be under 8 KB.")
            data = json.loads(imported.getvalue())
            if not isinstance(data, dict):
                raise ValueError("Choose an exported appearance profile.")
            save_appearance(data)
            st.session_state.appearance_editor_generation = generation + 1
            st.rerun()
        except (ValueError, UnicodeError) as exc:
            st.error(str(exc))
