from __future__ import annotations
import html
import base64
from pathlib import Path
from typing import Any
import streamlit as st
from .config import settings

def inject_css(domain: str, animation: str = "Balanced", reduced_motion: bool = False, appearance: dict | None = None) -> None:
    if appearance:
        animation = appearance.get("motion", "Balanced")
        reduced_motion = animation == "Reduced"
    st.html("""<style>
    :root{--z-accent:#a7b7ff;--z-line:#30394c;--z-muted:#aab4c7}
    .stApp{background:#111521;color:#e9edf5;font-family:"Segoe UI",Tahoma,sans-serif}
    [data-testid="stMainBlockContainer"]{max-width:1280px;padding-top:4.5rem;padding-bottom:2rem}
    [data-testid="stSidebar"]{background:#171c2a;border-right:1px solid #30394c}
    [data-testid="stSidebar"] .stButton button{justify-content:flex-start;text-align:left}
    [data-testid="stSidebar"] hr{margin:.65rem 0}
    h1,h2,h3{letter-spacing:-.035em;font-weight:650!important}
    .z-brand{font-size:1.15rem;letter-spacing:.12em;font-weight:750;color:#f3f5fc}
    .z-sub,.z-kicker{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:#acbaff;margin:6px 0 14px}
    .z-top{display:flex;justify-content:space-between;gap:16px;align-items:center;border-bottom:1px solid #30394c;padding:0 0 18px;margin-bottom:28px}
    .z-top .z-sub{margin-bottom:0}
    .z-status-cluster,.z-chip-row{display:flex;flex-wrap:wrap;gap:8px}
    .z-pill,.z-chip{display:inline-flex;align-items:center;gap:7px;font-size:.78rem;border:1px solid #3c4660;background:#1c2333;color:#c9d2e4;border-radius:20px;padding:5px 11px}
    .z-dot{height:7px;width:7px;border-radius:50%;background:#70d6af}.z-dot.offline{background:#f2bd6a}
    .z-card{background:#1a2030;border:1px solid #30394c;border-radius:16px;padding:24px}
    .z-title{font-size:clamp(2rem,4.2vw,3.6rem);font-weight:650;letter-spacing:-.055em;line-height:1.1;color:#f5f7fc}
    .accent{color:#acbaff}.z-lead{font-size:1rem;color:#b5bfd2;line-height:1.7;margin:18px 0;max-width:680px}
    .z-label{font-size:.75rem;color:#b2bed4;letter-spacing:.08em;text-transform:uppercase}
    .z-value{font-size:1.15rem;font-weight:650;color:#f3f5fb;margin:8px 0}.z-small{font-size:.84rem;line-height:1.6;color:#b1bdd1}
    .z-grid-hero{display:grid;grid-template-columns:1.5fr 1fr;gap:20px;margin-bottom:24px}.z-hero-copy{padding:32px}
    .z-core-panel{background:#222b45;display:flex;flex-direction:column;justify-content:center;gap:15px}
    .z-core-symbol{font-size:3.5rem;font-weight:300;color:#b4c2ff;line-height:1}
    .z-chat-welcome{padding:32px;margin-bottom:20px;max-width:900px}.z-chat-welcome .z-core-panel{display:none}
    .z-auth-intro{max-width:680px;margin:0 auto 26px;text-align:center;padding:16px}.z-auth-intro .z-title{font-size:2.6rem}.z-auth-intro .z-lead{margin:16px auto}
    [data-testid="stAppDeployButton"]{display:none}
    .z-editorial-hero{position:relative;isolation:isolate;min-height:365px;border-radius:22px;overflow:hidden;border:1px solid #3d4155;margin:4px 0 18px;background:#151a26}
    .z-editorial-hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:70% 60%;z-index:-2}
    .z-editorial-hero:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(12,16,26,.94) 0%,rgba(12,16,26,.75) 34%,rgba(12,16,26,.12) 76%);z-index:-1}
    .z-editorial-copy{padding:40px;width:60%;position:relative}
    .z-editorial-copy h1{font-size:clamp(2.2rem,4vw,3.8rem);line-height:1.07;font-weight:600!important;letter-spacing:-.06em;margin:20px 0;color:#f4f2ef}
    .z-editorial-copy p{font-size:.95rem;line-height:1.7;color:#c3cad9;max-width:400px}
    .z-eyebrow{display:flex;align-items:center;gap:10px;font-size:.68rem;letter-spacing:.19em;text-transform:uppercase;font-weight:650;color:#d3c5a9}
    .z-eyebrow:before{content:"";width:22px;height:1px;background:#d3c5a9}
    .z-art-credit{position:absolute;bottom:18px;right:22px;color:#e0d5c3;font-size:.63rem;letter-spacing:.18em;text-transform:uppercase}
    .z-auth-hero{min-height:590px;margin:0}.z-auth-hero img{object-position:72% center}.z-auth-hero:after{background:linear-gradient(180deg,rgba(12,16,26,.7),rgba(12,16,26,.03) 40%,rgba(12,16,26,.88))}
    .z-auth-hero .z-editorial-copy{width:100%;padding:34px}.z-auth-hero .z-editorial-copy h1{font-size:2.9rem;max-width:380px}.z-auth-hero .z-editorial-copy p{max-width:320px}
    .z-section-hero{min-height:205px;margin-bottom:24px}.z-section-hero .z-editorial-copy{padding:28px 32px}.z-section-hero h1{font-size:2.3rem;margin:13px 0}.z-section-hero p{margin:0;font-size:.86rem}
    .z-workspace-number{display:flex;align-items:center;justify-content:space-between;color:#aebee6;font-size:.73rem;letter-spacing:.14em;margin:0 0 12px}
    .z-workspace-number span:last-child{color:#d2bb8f;font-size:1.1rem}
    div[class*="st-key-workspace_"]{background:linear-gradient(145deg,#1b2232,#151b29);border-radius:14px}
    div[class*="st-key-workspace_"] h3{font-size:1.24rem!important;letter-spacing:-.025em}
    div[class*="st-key-workspace_"] [data-testid="stCaptionContainer"]{min-height:36px}
    .z-top{margin-bottom:20px}.z-top .z-brand{font-size:.92rem;letter-spacing:.05em}
    .stTabs [aria-selected="true"]{color:#c7ceff!important}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.55rem}
    [data-testid="stSidebar"] .stButton button{min-height:37px}
    @media(max-width:760px){.z-editorial-hero{min-height:330px}.z-editorial-copy{padding:27px;width:86%}.z-editorial-copy h1{font-size:2.55rem}.z-editorial-hero:after{background:linear-gradient(90deg,rgba(12,16,26,.93),rgba(12,16,26,.5))}.z-auth-hero{min-height:300px}.z-auth-hero .z-editorial-copy h1{font-size:2.25rem}.z-section-hero{min-height:215px}.z-section-hero .z-editorial-copy{padding:25px}.z-section-hero h1{font-size:2rem}.z-art-credit{display:none}}
    .z-stat-grid,.z-trust{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:22px 0}
    .z-footer{font-size:.75rem;color:#a2adc2;margin-top:32px;padding-top:18px;border-top:1px solid #30394c}
    .stButton button,.stDownloadButton button{min-height:42px;border-radius:9px;font-weight:500}
    button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid #b4c2ff!important;outline-offset:3px}
    [data-testid="stChatMessage"]{background:#1a2030;border:1px solid #30394c;border-radius:14px;margin-bottom:12px}
    [data-testid="stChatMessageContent"]{line-height:1.7;unicode-bidi:plaintext}
    [data-testid="stChatInput"] textarea{unicode-bidi:plaintext}
    @media(max-width:760px){.z-grid-hero,.z-stat-grid,.z-trust{grid-template-columns:1fr}.z-top{align-items:flex-start;flex-direction:column}.z-hero-copy,.z-chat-welcome{padding:22px}.z-title{font-size:2.3rem}[data-testid="stMainBlockContainer"]{padding:4.5rem 1rem 1rem}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
    </style>""")
    st.html(f"<style>{(Path(__file__).resolve().parents[1] / 'assets' / 'horizon.css').read_text(encoding='utf-8')}</style>")
    if not reduced_motion and animation != "Reduced":
        st.html("""<style>@media(prefers-reduced-motion:no-preference){
        .z-editorial-hero{animation:z-enter .6s ease-out both}
        .stButton button,div[class*="st-key-workspace_"]{transition:transform .24s ease,box-shadow .24s ease,border-color .24s ease}
        @media(hover:hover){div[class*="st-key-workspace_"]:hover{transform:perspective(1000px) translateY(-5px) rotateX(1deg);border-color:#8d8065!important;box-shadow:0 18px 36px #0005}.stButton button:hover{transform:translateY(-1px)}}
        }</style>""")
        if animation == "Immersive":
            st.html('<style>@media(prefers-reduced-motion:no-preference) and (min-width:761px){.z-orbit{animation:z-orbit 16s ease-in-out infinite}.z-editorial-hero img{animation:z-drift 20s ease-in-out infinite}.z-sculpture{animation:z-float 7s ease-in-out infinite}.z-sculpture-2{animation-delay:-2s}.z-sculpture-3{animation-delay:-4s}.z-sculpture-4{animation-delay:-1s}}</style>')
    if appearance:
        from .appearance import appearance_css
        st.html(f"<style>{appearance_css(appearance)}</style>")

def render_topbar(user: Any, domain: str, mode: str, online: bool, privacy_mode: str) -> None:
    privacy = "Session only" if privacy_mode == "Ephemeral" else "Saved on host laptop"
    st.html(f'''<div class="z-top"><div><div class="z-brand">ZODERISE <span style="font-weight:400;color:#a7b7ff">/ Horizon</span></div>
    <div class="z-sub">{html.escape(domain)}</div></div><div class="z-status-cluster">
    <span class="z-pill"><span class="z-dot {'' if online else 'offline'}"></span>{'AI connected' if online else 'AI offline'}</span>
    <span class="z-pill">{privacy}</span><span class="z-pill">{html.escape(str(user['name']))}</span></div></div>''')

def hero_core(status_text: str = "YOUR LOCAL WORKSPACE") -> str:
    return f'''<div class="z-card z-core-panel"><div class="z-core-symbol">z.</div>
    <div class="z-label">{html.escape(status_text)}</div><div class="z-value">Your ideas. Your private workspace.</div>
    <div class="z-small">Learn, write, research, and understand images with your local AI models.</div>
    <div class="z-chip-row"><span class="z-chip">English</span><span class="z-chip">دری</span><span class="z-chip">پښتو</span></div></div>'''

def footer() -> None:
    st.html(f'<div class="z-footer">Zoderise Horizon · Created by Zubair Zahidi · Built for Kardan Private School<br>{html.escape(settings.app_version)} · Local AI can make mistakes. Check important answers against the sources.</div>')


@st.cache_data(max_entries=4, show_spinner=False)
def artwork_data(name: str) -> str:
    assets = {"horizon-hero.png": "horizon-orbit.webp", "knowledge-studio.png": "knowledge-studio.webp", "study-atelier.png": "study-atelier.webp"}
    if name not in assets:
        raise ValueError("Unknown workspace artwork")
    asset = assets[name]
    path = Path(__file__).resolve().parents[1] / "assets" / asset
    return "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def render_art_header(title: str, subtitle: str, *, label: str = "ZODERISE HORIZON", artwork: str = "horizon-hero.png", variant: str = "") -> None:
    appearance = st.session_state.get("appearance", {})
    if appearance.get("artwork") == "Hidden" or appearance.get("focus"):
        st.html(f'<section class="z-editorial-hero {html.escape(variant)}"><div class="z-editorial-copy"><div class="z-eyebrow">{html.escape(label)}</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div></section>')
        return
    description = {"horizon-hero.png": "A gold and glass astrolabe above an obsidian platform", "knowledge-studio.png": "Floating glass documents and a sculptural notebook", "study-atelier.png": "An open glass book beneath golden orbital rings"}[artwork]
    st.html(f'''<section class="z-editorial-hero {html.escape(variant)}">
    <img src="{artwork_data(artwork)}" alt="{description}">
    <div class="z-editorial-copy"><div class="z-eyebrow">{html.escape(label)}</div>
    <h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>
    <div class="z-orbit" aria-hidden="true"></div><div class="z-art-credit">A space for discovery / Zoderise</div></section>''')
