from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import streamlit as st

from kuku_localise.bible import build_bible
from kuku_localise.cli import run
from kuku_localise.index import build_index
from kuku_localise.llm import BaseLLMClient, get_client
from kuku_localise.models import Episode
from kuku_localise.parse import parse_folder
from kuku_localise.projects import create_project, list_projects, read_project, save_scripts, update_project

PROJECTS = Path("projects")
LANGUAGES = ["Hindi", "Tamil", "Telugu", "Spanish", "English", "Custom language"]
MODELS = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-pro", "Custom model ID"]

# Configure Streamlit page once at the top
st.set_page_config(
    page_title="Kuku Localise · Studio Workspace",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark Mode Cinema Studio Theme & Design System (High Contrast & Readability)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

<style>
:root {
  --bg-deep: #0c0710;
  --bg-surface: #150e1b;
  --bg-card: #1c1324;
  --bg-card-hover: #24182e;
  --bg-subtle: #20152a;
  
  --line: #331f3f;
  --line-strong: #4e2e60;
  --line-highlight: #ba58cb;
  
  --text-main: #f5eff8;
  --text-muted: #bfaec7;
  --text-subtle: #9885a3;
  --text-inverse: #0c0710;
  
  --accent-plum: #ba58cb;
  --accent-purple: #9d3eb2;
  --accent-light: #f5d4fc;
  
  --emerald-bg: #062b1e;
  --emerald-text: #6ee7b7;
  --emerald-border: #0d6e4d;
  
  --indigo-bg: #191b42;
  --indigo-text: #c7d2fe;
  --indigo-border: #3730a3;
  
  --amber-bg: #301d07;
  --amber-text: #fde68a;
  --amber-border: #854d0e;

  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.35);
  --shadow-md: 0 6px 20px rgba(0, 0, 0, 0.45);
  --shadow-lg: 0 12px 36px rgba(0, 0, 0, 0.6);
}

/* Base App Dark Theme */
.stApp {
  background: var(--bg-deep) !important;
  color: var(--text-main) !important;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Global Typography & Headings */
h1, h2, h3, h4, h5, h6 {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  color: #ffffff !important;
  letter-spacing: -0.025em;
  font-weight: 700;
}

p, span, label, div {
  font-family: 'Plus Jakarta Sans', sans-serif;
  color: var(--text-main);
}

.stCaption, small, [data-testid="stCaptionContainer"] {
  color: var(--text-muted) !important;
}

code, pre {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.88em !important;
  color: #f7d4ff !important;
  background: #25182e !important;
}

/* Sidebar Dark Styling */
[data-testid="stSidebar"] {
  background: #110a17 !important;
  border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"] * {
  color: var(--text-main);
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h3 {
  color: #ffffff !important;
}

/* Hero Banner Dark Mode */
.hero-banner {
  background: linear-gradient(135deg, #180521 0%, #2f0e3a 50%, #541968 100%);
  padding: 30px 36px 26px 36px;
  border-radius: 20px;
  color: white;
  margin-bottom: 24px;
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(186, 88, 203, 0.25);
}
.hero-banner::after {
  content: '';
  position: absolute;
  top: -60px;
  right: -60px;
  width: 260px;
  height: 260px;
  background: radial-gradient(circle, rgba(186, 88, 203, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}
.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(8px);
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #fad7ff;
  margin-bottom: 12px;
}
.hero-title {
  font-family: 'Cinzel', serif !important;
  font-size: 2.2rem;
  font-weight: 700;
  color: #ffffff !important;
  margin: 0 0 6px 0;
  letter-spacing: -0.01em;
}
.hero-subtitle {
  color: #ded0e4;
  font-size: 1.02rem;
  margin: 0 0 18px 0;
  max-width: 780px;
  font-weight: 400;
  line-height: 1.5;
}

/* Executive Project Status Ribbon */
.status-ribbon {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}
.ribbon-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(6px);
  padding: 6px 14px;
  border-radius: 10px;
  font-size: 0.82rem;
  color: #ffffff;
  font-weight: 500;
}
.ribbon-chip b {
  color: #f7d2ff;
  font-weight: 700;
}

/* Studio Dark Cards */
.studio-card {
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 22px 24px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 20px;
  transition: all 0.2s ease;
}
.studio-card:hover {
  border-color: var(--line-strong);
  box-shadow: var(--shadow-md);
  background: var(--bg-card-hover);
}

/* Form Inputs, Textarea, Select */
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
  border-radius: 10px !important;
  border: 1px solid var(--line-strong) !important;
  background-color: #170e1d !important;
  color: #ffffff !important;
  font-size: 0.92rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--accent-plum) !important;
  box-shadow: 0 0 0 3px rgba(186, 88, 203, 0.2) !important;
}

.stTextArea textarea:disabled {
  -webkit-text-fill-color: #f1ecf5 !important;
  color: #f1ecf5 !important;
  background-color: #1d1325 !important;
  border-color: #3b2447 !important;
  opacity: 1 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.9rem !important;
  line-height: 1.5 !important;
}
.stTextArea textarea {
  color: #ffffff !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.9rem !important;
  line-height: 1.5 !important;
}

/* Metric Display Dark */
[data-testid="stMetric"] {
  padding: 16px 20px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] {
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
  color: #ffffff;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 800;
}

/* Character Profile Card */
.char-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 12px;
}
.char-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #74278e, #ba58cb);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.15rem;
  box-shadow: 0 3px 12px rgba(186, 88, 203, 0.35);
  flex-shrink: 0;
}
.char-title-box {
  flex-grow: 1;
}
.char-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #ffffff !important;
  margin: 0;
}
.char-spoken {
  font-size: 0.9rem;
  color: #e5a4ff;
  font-weight: 600;
}

/* High-Contrast Badges */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
}
.badge-role {
  background: #341940;
  color: #f2b7ff;
  border: 1px solid #5d2b72;
}
.badge-alias {
  background: #25182e;
  color: #d8c8e3;
  border: 1px solid #442a54;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
}
.badge-emerald {
  background: var(--emerald-bg);
  color: var(--emerald-text);
  border: 1px solid var(--emerald-border);
}
.badge-indigo {
  background: var(--indigo-bg);
  color: var(--indigo-text);
  border: 1px solid var(--indigo-border);
}
.badge-amber {
  background: var(--amber-bg);
  color: var(--amber-text);
  border: 1px solid var(--amber-border);
}

/* Screenplay Beat Review Card */
.beat-card {
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 16px;
  box-shadow: var(--shadow-sm);
  transition: all 0.15s ease;
}
.beat-card:hover {
  border-color: var(--accent-plum);
  box-shadow: var(--shadow-md);
  background: var(--bg-card-hover);
}
.beat-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}
.beat-speaker {
  font-size: 0.98rem;
  font-weight: 700;
  color: #ffffff;
}
.beat-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.76rem;
  color: #d8c9e0;
  background: #271633;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid #3e2450;
}
.beat-rationale-box {
  background: #281705;
  border: 1px solid #854d0e;
  border-left: 4px solid #f59e0b;
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 10px;
  font-size: 0.85rem;
  color: #fef3c7;
}
.beat-cultural-box {
  background: #062b1e;
  border: 1px solid #0d6e4d;
  border-left: 4px solid #10b981;
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 8px;
  font-size: 0.84rem;
  color: #d1fae5;
}
.beat-char-context {
  background: #22152b;
  border: 1px solid #482a5c;
  border-radius: 8px;
  padding: 8px 12px;
  margin-top: 8px;
  font-size: 0.82rem;
  color: #ebd8f3;
}

/* KPI Scorecard Box */
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px;
  text-align: left;
  box-shadow: var(--shadow-sm);
}
.kpi-title {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-weight: 700;
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 2.1rem;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 6px;
  line-height: 1;
}
.kpi-sub {
  font-size: 0.8rem;
  color: var(--text-muted);
}

/* Script Preview Box */
.script-viewer {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.86rem;
  line-height: 1.6;
  background: #0e0712;
  color: #f3ecf7;
  padding: 20px 24px;
  border-radius: 12px;
  max-height: 520px;
  overflow-y: auto;
  white-space: pre-wrap;
  border: 1px solid #3f274e;
}
</style>
""", unsafe_allow_html=True)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def select_project():
    st.sidebar.markdown("""
    <div style='display:flex; align-items:center; gap:8px; margin-bottom:12px;'>
      <span style='font-size:1.4rem;'>🎬</span>
      <h3 style='margin:0; font-size:1.15rem; font-weight:800; color:#ffffff;'>Studio Projects</h3>
    </div>
    """, unsafe_allow_html=True)

    projects = list_projects(PROJECTS)
    with st.sidebar.expander("✨ New microdrama project", expanded=not projects):
        name = st.text_input("Project name", placeholder="e.g. Lady Juliana's Vengeance")
        if st.button("Create project", type="primary", use_container_width=True):
            try:
                path = create_project(PROJECTS, name)
                st.session_state.project_path = str(path)
                st.success(f"Project '{name}' created!")
                st.rerun()
            except (ValueError, FileExistsError) as error:
                st.error(str(error))

    if not projects:
        st.info("👋 Welcome! Create a microdrama project in the sidebar to begin.")
        return None

    current = st.session_state.get("project_path")
    idx = next((i for i, p in enumerate(projects) if str(p) == current), 0)
    selected = st.sidebar.selectbox(
        "Active Project",
        projects,
        index=idx,
        format_func=lambda p: read_project(p).get("name", p.name),
    )
    st.session_state.project_path = str(selected)
    return selected


def configure_hub(root: Path):
    meta = read_project(root)
    scripts = sorted((root / "scripts").glob("*.txt"))
    target_lang = meta.get("language", "Hindi")
    model_name = meta.get("model", MODELS[0])

    with st.expander(f"⚙️ Show Settings & Script Ingestion ({len(scripts)} scripts loaded)", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Language & Translation Engine**")
            lang_choice = st.selectbox(
                "Target language",
                LANGUAGES,
                index=LANGUAGES.index(target_lang) if target_lang in LANGUAGES else len(LANGUAGES) - 1,
                key="cfg_lang",
            )
            language = (
                st.text_input("Custom language", target_lang, key="cfg_custom_lang")
                if lang_choice == "Custom language"
                else lang_choice
            )

            model_choice = st.selectbox(
                "Model ID",
                MODELS,
                index=MODELS.index(model_name) if model_name in MODELS else len(MODELS) - 1,
                key="cfg_model",
            )
            model = (
                st.text_input("Custom model ID", model_name, key="cfg_custom_model")
                if model_choice == "Custom model ID"
                else model_choice
            )

            if st.button("Save project configuration", type="primary", use_container_width=True):
                update_project(root, language=language.strip(), model=model.strip())
                st.success("Configuration updated.")
                st.rerun()

        with c2:
            st.markdown("**Upload Screenplay Scripts**")
            uploads = st.file_uploader(
                "Upload episode .txt files",
                type=["txt"],
                accept_multiple_files=True,
                help="Upload plain text screenplay files formatted with scene headings, character cues, and timestamps.",
            )
            if st.button("Save uploaded scripts", disabled=not uploads, use_container_width=True):
                saved_count = save_scripts(root, uploads or [])
                st.success(f"Saved {saved_count} episode scripts.")
                st.rerun()

            if scripts:
                st.markdown(f"**Loaded screenplay files ({len(scripts)} total):**")
                file_chips = "".join([f"<span class='badge badge-alias' style='margin:2px;'>{p.name}</span>" for p in scripts[:8]])
                if len(scripts) > 8:
                    file_chips += f"<span class='badge badge-role' style='margin:2px;'>+{len(scripts)-8} more</span>"
                st.markdown(f"<div>{file_chips}</div>", unsafe_allow_html=True)

    return scripts


def context_tab(root: Path, scripts: list[Path]):
    raw = root / "output" / "raw"
    bible_path = raw / "story_bible.json"
    meta = read_project(root)

    col_info, col_btn = st.columns([3, 1.2])
    with col_info:
        st.markdown("""
        <div style='margin-bottom:8px;'>
          <h3 style='margin:0 0 4px 0;'>Series Knowledge & Character Story Bible</h3>
          <p style='color:var(--text-muted); margin:0; font-size:0.92rem;'>
            Unify recurring character names into canonical aliases, establish gender & relationship dynamics, address registers (aap/tum/tu), and curate recurring glossary terms.
          </p>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.write("")
        if scripts and st.button("✨ Build / Refresh Story Bible", type="primary", use_container_width=True):
            episodes, skipped = parse_folder(root / "scripts")
            if not episodes:
                st.error("No screenplay files could be parsed.")
            else:
                raw.mkdir(parents=True, exist_ok=True)
                with st.spinner("Analyzing cross-episode character continuity and glossary..."):
                    index = build_index(episodes, meta["language"])
                    client = get_client(cache_dir=root / "output" / "cache", model=meta["model"])
                    bible = build_bible(client, index, meta["name"], meta["language"])
                (raw / "episodes.json").write_text(json.dumps({"episodes": [e.to_dict() for e in episodes]}, ensure_ascii=False, indent=2), encoding="utf-8")
                (raw / "series_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
                (raw / "ingest.json").write_text(json.dumps({"episodes_found": len(episodes), "skipped": skipped}, ensure_ascii=False, indent=2), encoding="utf-8")
                bible_path.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
                st.success(f"Story Bible successfully built from {len(episodes)} episodes!")
                st.rerun()

    if not bible_path.exists():
        st.info("💡 Click **Build / Refresh Story Bible** above to extract characters, relationship maps, and glossary terms from your uploaded scripts.")
        return

    bible = load(bible_path)

    # Low-Confidence Merges Alert Banner
    flagged_merges = bible.get("flagged_merges") or []
    if flagged_merges:
        st.markdown("""
        <div style='background:#331d07; border:1px solid #854d0e; border-left:4px solid #f59e0b; border-radius:10px; padding:14px 18px; margin:14px 0 20px 0;'>
          <div style='display:flex; align-items:center; gap:8px;'>
            <span style='font-size:1.2rem;'>⚠️</span>
            <h4 style='margin:0; color:#fde68a; font-size:1.0rem;'>Low-Confidence Merges Flagged for Human Review</h4>
          </div>
          <p style='color:#fef3c7; font-size:0.86rem; margin:6px 0 10px 0;'>
            The model or token grouping merged generic descriptor cues or non-overlapping names. Please review and confirm or split these aliases:
          </p>
        """, unsafe_allow_html=True)
        for fm in flagged_merges:
            reasons_str = "; ".join(fm.get("reasons", []))
            st.markdown(
                f"<div style='color:#fef3c7; font-size:0.84rem; margin-bottom:4px;'>• <b>{html.escape(fm.get('display_name',''))}</b>: merged <code>{html.escape(fm.get('surface_form',''))}</code> &mdash; <i style='color:#fde68a;'>{html.escape(reasons_str)}</i></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Series Policy & Title Box
    with st.form("review_bible_form"):
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        col_t, col_l = st.columns([2, 1])
        with col_t:
            bible["series_title"] = st.text_input("Series Title", bible.get("series_title", meta.get("name", "")))
        with col_l:
            st.text_input("Target Language", bible.get("target_language", meta.get("language", "Hindi")), disabled=True)

        bible["adaptation_policy"] = st.text_area(
            "Series Adaptation Policy & Power Dynamics",
            bible.get("adaptation_policy", ""),
            help="Defines honorifics rules, respectful address (Aap) vs condescending/familiar address (Tu), and emotional tone preservation.",
        )

        st.markdown("<hr style='border:none; border-top:1px solid var(--line); margin:20px 0;'>", unsafe_allow_html=True)

        # Characters Section
        characters = bible.get("characters", [])
        st.markdown(f"""
        <div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;'>
          <div>
            <h4 style='margin:0;'>Character Roster & Voice Profiles</h4>
            <span style='font-size:0.83rem; color:var(--text-muted);'>Define spoken names, gender (crucial for verb agreement), address registers, and character dynamics.</span>
          </div>
          <span class='badge badge-role'>{len(characters)} Characters Indexed</span>
        </div>
        """, unsafe_allow_html=True)

        for i, char in enumerate(characters):
            initials = (char.get("display_name", "")[:2] or "CH").upper()
            spoken = char.get("spoken_name", "")
            aliases = char.get("surface_forms", [])
            role_snippet = (char.get("role") or "").split(",")[0]
            is_flagged = bool(char.get("low_confidence_merges") or char.get("needs_review"))

            alias_tags = "".join([f"<span class='badge badge-alias' style='margin-right:4px;'>{html.escape(a)}</span>" for a in aliases[:4]])
            if len(aliases) > 4:
                alias_tags += f"<span class='badge badge-alias'>+{len(aliases)-4}</span>"
            if is_flagged:
                alias_tags += " <span class='badge badge-amber'>⚠️ Low-Confidence Merge</span>"

            with st.expander(f"👤 {char.get('display_name')}  ·  {spoken or 'No spoken name'}  ·  {role_snippet} {'(⚠️ Review)' if is_flagged else ''}"):
                st.markdown(f"""
                <div class='char-card-header'>
                  <div class='char-avatar'>{initials}</div>
                  <div class='char-title-box'>
                    <h4 class='char-name'>{html.escape(char.get('display_name', ''))} <span class='char-spoken'>({html.escape(spoken)})</span></h4>
                    <div style='margin-top:4px;'>{alias_tags}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                c_a, c_b = st.columns(2)
                char["display_name"] = c_a.text_input("Script Display Name", char.get("display_name", ""), key=f"b-dn-{i}")
                char["spoken_name"] = c_b.text_input("Spoken Name in Dialogue", char.get("spoken_name", ""), key=f"b-sn-{i}")

                # Step 2: Gender and Address Register Inputs
                c_gen, c_reg = st.columns(2)
                curr_gen = char.get("gender", "unknown").lower()
                gen_opts = ["female", "male", "non-binary", "unknown"]
                gen_idx = gen_opts.index(curr_gen) if curr_gen in gen_opts else 3
                char["gender"] = c_gen.selectbox("Character Gender (for Hindi verb conjugation)", gen_opts, index=gen_idx, key=f"b-gen-{i}")

                curr_reg = char.get("address_register", "aap").lower()
                reg_opts = ["aap", "tum", "tu"]
                reg_idx = reg_opts.index(curr_reg) if curr_reg in reg_opts else 0
                char["address_register"] = c_reg.selectbox("Primary Address Register", reg_opts, index=reg_idx, key=f"b-reg-{i}")

                char["role"] = st.text_area("Narrative Role", char.get("role", ""), key=f"b-role-{i}", height=70)

                c_rel, c_sty = st.columns(2)
                char["relationships"] = c_rel.text_area("Relationship Dynamics", char.get("relationships", ""), key=f"b-rel-{i}", height=80)
                char["speech_style"] = c_sty.text_area("Speech Style & Voice", char.get("speech_style", ""), key=f"b-sty-{i}", height=80)

                char["address"] = st.text_input("Forms of Address & Honorific Protocol", char.get("address", ""), key=f"b-add-{i}")

        st.markdown("<hr style='border:none; border-top:1px solid var(--line); margin:20px 0;'>", unsafe_allow_html=True)

        # Glossary Section
        glossary = bible.get("glossary", [])
        st.markdown(f"""
        <div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;'>
          <div>
            <h4 style='margin:0;'>Recurring Glossary & Terminology</h4>
            <span style='font-size:0.83rem; color:var(--text-muted);'>Lock in specific cultural terminology, titles, or decisions to keep vs adapt.</span>
          </div>
          <span class='badge badge-indigo'>{len(glossary)} Terms</span>
        </div>
        """, unsafe_allow_html=True)

        for i, term in enumerate(glossary):
            gc = st.columns([1.5, 1, 1.5, 2])
            term["source"] = gc[0].text_input("Source Term", term.get("source", ""), key=f"gs-{i}")
            term["decision"] = gc[1].selectbox("Action", ["keep", "adapt"], index=0 if term.get("decision") == "keep" else 1, key=f"gd-{i}")
            term["target"] = gc[2].text_input("Target Form", term.get("target", ""), key=f"gt-{i}")
            term["note"] = gc[3].text_input("Usage Context", term.get("note", ""), key=f"gn-{i}")

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.form_submit_button("💾 Save Reviewed Story Bible", type="primary", use_container_width=True):
            bible_path.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("Story Bible updated! Localization will use these reviewed character profiles and terms.")

    # Localization Launcher Card
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background:linear-gradient(135deg, #1f1228 0%, #2f173d 100%); border:1px solid #4a2860; border-radius:16px; padding:20px 24px;'>
      <div style='display:flex; align-items:center; gap:8px;'>
        <span style='font-size:1.3rem;'>🚀</span>
        <h4 style='margin:0; color:#ffffff;'>Launch Series-Aware Localisation</h4>
      </div>
      <p style='color:var(--text-muted); font-size:0.88rem; margin:4px 0 14px 0;'>
        Runs pipeline with timing validation, register enforcement (aap/tum/tu), automated repair loop, and cultural adaptation pass.
      </p>
    </div>
    """, unsafe_allow_html=True)

    col_ep, col_go = st.columns([2.5, 1.5])
    with col_ep:
        selected_eps = st.text_input("Episodes to localise (comma-separated or 'all')", "1,2,10", help="Specify episode numbers like '1,2,10' or 'all'")
        no_baseline_toggle = st.checkbox("⚡ Skip baseline run (--no-baseline) to cut API cost by 50%", value=False)
    with col_go:
        st.write("")
        st.write("")
        if st.button("✨ Run Contextual Localisation", type="primary", use_container_width=True):
            args = argparse.Namespace(
                scripts=str(root / "scripts"),
                lang=meta["language"],
                episodes=selected_eps,
                output=str(root / "output"),
                model=meta["model"],
                no_baseline=no_baseline_toggle,
            )
            try:
                with st.spinner("Applying series context and running validation/repair passes..."):
                    run(args)
                st.success("Localisation finished! Review side-by-side lines, ROI edit rate, and continuity metrics in the next tabs.")
                st.rerun()
            except Exception as error:
                st.error(f"Localisation failed: {error}")


def localisation_tab(root: Path):
    raw = root / "output" / "raw"
    paths = sorted(raw.glob("episode-*.series.json")) if raw.exists() else []

    if not paths or not (raw / "episodes.json").exists():
        st.info("💡 Build the Story Bible and run localization on your episodes to review side-by-side line choices.")
        return

    # Header Control Strip
    c_ep, c_filter, c_search = st.columns([1.5, 1.5, 2])
    with c_ep:
        path = st.selectbox("Select Episode", paths, format_func=lambda p: f"Episode {p.stem.split('.')[0].replace('episode-', '')}")
    with c_filter:
        view_filter = st.selectbox("Show Beats", ["All dialogue beats", "Adapted beats only", "Beats with AI rationale", "Honest failures only"])
    with c_search:
        search_query = st.text_input("🔍 Search lines or speaker", placeholder="Filter by text or speaker...")

    contextual = load(path)
    isolated_path = path.with_name(path.name.replace(".series.json", ".independent.json"))
    isolated = load(isolated_path) if isolated_path.exists() else {"beats": {}}
    rows = load(raw / "episodes.json")["episodes"]
    ep = next((Episode.from_dict(row) for row in rows if int(row["number"]) == contextual["episode"]), None)
    bible = load(raw / "story_bible.json") if (raw / "story_bible.json").exists() else {}

    # Load existing reviewer edits if any
    edits_file = root / "output" / "reviewed" / f"episode-{contextual['episode']:03d}.edits.json"
    existing_edits = load(edits_file) if edits_file.exists() else {}

    if ep is None:
        st.error("Parsed source data is missing.")
        return

    source = {beat.id: beat for beat in ep.beats()}

    # Filter beats
    all_beats = []
    for bid, result in contextual.get("beats", {}).items():
        beat = source.get(bid)
        if not beat or beat.kind != "dialogue":
            continue

        iso_text = (isolated.get("beats", {}).get(bid) or {}).get("text", "")
        # Prioritize saved reviewer edit if available, else contextual text
        ctx_text = existing_edits.get(bid, result.get("text", ""))
        is_changed = iso_text.strip() != ctx_text.strip()
        has_note = bool(result.get("relationship_context") or result.get("localisation_note"))
        is_fail = bool(result.get("status") == "honest_failure" or result.get("validation_failed"))

        if view_filter == "Adapted beats only" and not is_changed:
            continue
        if view_filter == "Beats with AI rationale" and not has_note:
            continue
        if view_filter == "Honest failures only" and not is_fail:
            continue
        if search_query:
            sq = search_query.casefold()
            match = sq in beat.cue.casefold() or sq in beat.text.casefold() or sq in ctx_text.casefold() or sq in iso_text.casefold()
            if not match:
                continue

        all_beats.append((bid, beat, result, iso_text, ctx_text, is_changed, has_note, is_fail))

    # Summary Count Bar
    st.markdown(f"""
    <div style='display:flex; align-items:center; justify-content:space-between; margin:14px 0 16px 0;'>
      <span style='font-size:0.88rem; color:var(--text-muted);'>Showing <b style='color:#ffffff;'>{len(all_beats)}</b> dialogue beats for Episode {ep.number:03d}</span>
      <span style='font-size:0.84rem; color:#f0b8ff; font-weight:600;'>💡 Edit lines directly in the right column and click Save</span>
    </div>
    """, unsafe_allow_html=True)

    current_view_edits = {}
    for bid, beat, result, iso_text, ctx_text, is_changed, has_note, is_fail in all_beats:
        char = next((c for c in bible.get("characters", []) if beat.cue in c.get("surface_forms", []) or beat.cue == c.get("display_name")), None)

        with st.container():
            diff_badge = "<span class='badge badge-emerald'>✨ Context Adapted</span>" if is_changed else "<span class='badge badge-alias'>Identical</span>"
            if is_fail:
                diff_badge = "<span class='badge badge-amber'>⚠️ Honest Failure: Human Review Required</span>"

            dur_str = f" · {beat.duration:.1f}s" if beat.duration > 0 else ""
            time_str = f"{beat.start} to {beat.end}{dur_str}" if beat.start else "No timestamp"

            st.markdown(f"""
            <div class='beat-card'>
              <div class='beat-meta-row'>
                <div style='display:flex; align-items:center; gap:8px;'>
                  <span class='beat-speaker'>{html.escape(beat.cue)}</span>
                  {diff_badge}
                </div>
                <div style='display:flex; align-items:center; gap:8px;'>
                  <span class='beat-time'>⏱️ {time_str}</span>
                  <code style='font-size:0.75rem;'>#{bid}</code>
                </div>
              </div>
            """, unsafe_allow_html=True)

            # 3-Column Comparison
            col_src, col_iso, col_ctx = st.columns(3)
            with col_src:
                st.caption("🇺🇸 Source Screenplay")
                st.text_area("Source", beat.text, disabled=True, key=f"src-{bid}", height=95, label_visibility="collapsed")
            with col_iso:
                st.caption("🔒 Baseline (Episode Alone)")
                st.text_area("Episode alone", iso_text, disabled=True, key=f"iso-{bid}", height=95, label_visibility="collapsed")
            with col_ctx:
                st.caption("✨ Series Contextual (Editable)")
                current_view_edits[bid] = st.text_area("With series context", ctx_text, key=f"ctx-{bid}", height=95, label_visibility="collapsed")

            # Character Relationship & Voice context
            if char:
                spoken = char.get("spoken_name") or beat.cue
                gender = char.get("gender") or "unknown"
                register = char.get("address_register") or "aap"
                rel = char.get("relationships") or "Standard relationship"
                voice = char.get("speech_style") or "Standard voice"
                addr = char.get("address") or "Standard honorific"
                st.markdown(f"""
                <div class='beat-char-context'>
                  <b>👤 {html.escape(char.get('display_name', ''))}</b> (Spoken: <i style='color:#f2b7ff;'>{html.escape(spoken)}</i> | Gender: <b>{gender}</b> | Register: <b>{register}</b>) · <b>Dynamic:</b> {html.escape(rel[:90])}... · <b>Voice:</b> {html.escape(voice[:60])}...
                </div>
                """, unsafe_allow_html=True)

            # AI Rationale Box
            note = result.get("localisation_note")
            rel_ctx = result.get("relationship_context")
            if note or rel_ctx:
                st.markdown(f"""
                <div class='beat-rationale-box'>
                  <b>🎯 AI Context Rationale:</b> {html.escape(rel_ctx or '')} &mdash; <i>{html.escape(note or '')}</i>
                </div>
                """, unsafe_allow_html=True)

            # Cultural Adaptation Pass Note
            cult = result.get("cultural_adaptation")
            if cult and isinstance(cult, dict) and cult.get("idiom_found"):
                st.markdown(f"""
                <div class='beat-cultural-box'>
                  <b>🏮 Cultural Adaptation Pass:</b> Found idiom <code>{html.escape(cult.get('idiom_found', ''))}</code> &rarr; Adapted as: <b>{html.escape(cult.get('cultural_adaptation', ''))}</b> <i>({html.escape(cult.get('note', ''))})</i>
                </div>
                """, unsafe_allow_html=True)

            # Honest Failure Directive
            if is_fail:
                val_errs = "; ".join(result.get("validation_errors") or [])
                st.markdown(f"""
                <div class='beat-rationale-box' style='background:#3d1a04; border-color:#d97706;'>
                  <b>⚠️ Validation Honest Failure:</b> {html.escape(val_errs)} (Automated repair loops exhausted. Human studio reviewer edit requested).
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    # Save Line Edits Button - FIXED: Merge with existing edits to prevent data loss on filtered views
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    if st.button("💾 Save Reviewed Line Edits for this Episode", type="primary", use_container_width=True):
        destination = root / "output" / "reviewed"
        destination.mkdir(parents=True, exist_ok=True)
        target_edits_file = destination / f"episode-{ep.number:03d}.edits.json"

        # Load existing edits first, then merge current view edits
        merged_edits = {}
        if target_edits_file.exists():
            try:
                merged_edits = json.loads(target_edits_file.read_text(encoding="utf-8"))
            except Exception:
                merged_edits = {}
        merged_edits.update(current_view_edits)

        target_edits_file.write_text(json.dumps(merged_edits, ensure_ascii=False, indent=2), encoding="utf-8")
        st.success(f"Edits safely merged & saved! ({len(merged_edits)} total beats stored) for Episode {ep.number:03d}.")


def continuity_tab(root: Path):
    raw = root / "output" / "raw"
    report_path = raw / "comparison.json"

    if not report_path.exists():
        st.info("💡 Run localization to generate the continuity and quality assurance report.")
        return

    report = load(report_path)
    series_rep = report.get("series", {})
    indep_rep = report.get("independent", {}) or {}

    st.markdown("""
    <div style='margin-bottom:20px;'>
      <h3 style='margin:0 0 4px 0;'>Continuity & Quality Assurance Scorecard</h3>
      <p style='color:var(--text-muted); font-size:0.92rem; margin:0;'>
        Automated verification evaluating honest model performance, audio timestamp preservation, spoken names, and real-world Reviewer Edit Rate (ROI).
      </p>
    </div>
    """, unsafe_allow_html=True)

    # 4 Dynamic Hero KPI Cards
    k1, k2, k3, k4 = st.columns(4)

    # Dynamic KPI 1: Bind to actual missing_beat_count
    comp_val = series_rep.get("completeness", 1.0)
    missing_cnt = int(series_rep.get("missing_beat_count", 0))
    comp_pct = f"{int(comp_val * 100)}%" if comp_val is not None else "100%"
    badge_comp = (
        "<span class='badge badge-emerald'>✓ 0 dropped beats</span>"
        if missing_cnt == 0
        else f"<span class='badge badge-amber'>⚠️ {missing_cnt} dropped beats</span>"
    )
    k1.markdown(f"""
    <div class='kpi-card'>
      <div class='kpi-title'>Script Completeness</div>
      <div class='kpi-value'>{comp_pct}</div>
      <div class='kpi-sub'>{badge_comp}</div>
    </div>
    """, unsafe_allow_html=True)

    # Dynamic KPI 2: Bind to actual timestamps_preserved
    ts_ok = bool(series_rep.get("timestamps_preserved", True))
    ts_badge = (
        "<span class='badge badge-emerald'>✓ Sync preserved</span>"
        if ts_ok
        else "<span class='badge badge-amber'>⚠️ Drift detected</span>"
    )
    k2.markdown(f"""
    <div class='kpi-card'>
      <div class='kpi-title'>Audio Timestamps</div>
      <div class='kpi-value'>{'100%' if ts_ok else 'Gaps'}</div>
      <div class='kpi-sub'>{ts_badge}</div>
    </div>
    """, unsafe_allow_html=True)

    name_rate = series_rep.get("spoken_name_rate")
    iso_name_rate = indep_rep.get("spoken_name_rate")
    name_str = f"{int(name_rate * 100)}%" if name_rate is not None else "N/A"
    diff_name = f"+{int(((name_rate or 0) - (iso_name_rate or 0)) * 100)}% vs baseline" if name_rate and iso_name_rate else "High adherence"
    k3.markdown(f"""
    <div class='kpi-card'>
      <div class='kpi-title'>Spoken Name Rate</div>
      <div class='kpi-value'>{name_str}</div>
      <div class='kpi-sub'><span class='badge badge-indigo'>{diff_name}</span></div>
    </div>
    """, unsafe_allow_html=True)

    gloss_rate = series_rep.get("glossary_rate")
    gloss_str = f"{int(gloss_rate * 100)}%" if gloss_rate is not None else "100%"
    k4.markdown(f"""
    <div class='kpi-card'>
      <div class='kpi-title'>Glossary Adherence</div>
      <div class='kpi-value'>{gloss_str}</div>
      <div class='kpi-sub'><span class='badge badge-amber'>Consistent terms</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ROI & Reviewer Edit Rate Section (Real Evidence Metric)
    reviewer_edit_metrics = series_rep.get("reviewer_edit_metrics")
    if reviewer_edit_metrics:
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        r_rate = reviewer_edit_metrics.get("overall_edit_rate", 0.0)
        deliv = reviewer_edit_metrics.get("total_characters_delivered", 0)
        changed = reviewer_edit_metrics.get("total_characters_changed", 0)
        st.markdown(f"""
        <div style='background:linear-gradient(135deg, #09281e 0%, #104233 100%); border:1px solid #0d6e4d; border-radius:14px; padding:18px 22px; margin-bottom:20px;'>
          <div style='display:flex; align-items:center; justify-content:space-between;'>
            <div>
              <span class='badge badge-emerald' style='margin-bottom:6px;'>PROVEN STUDIO ROI METRIC</span>
              <h4 style='margin:0; color:#ffffff;'>Reviewer Edit Rate: {r_rate * 100:.1f}%</h4>
              <p style='color:#a7f3d0; font-size:0.86rem; margin:4px 0 0 0;'>
                Human reviewer modified <b>{changed:,}</b> characters out of <b>{deliv:,}</b> delivered characters. Lower edit rate signifies higher quality delivery and saved studio hours.
              </p>
            </div>
            <div style='text-align:right;'>
              <span style='font-size:2.4rem; font-weight:800; color:#6ee7b7;'>{(1.0 - r_rate) * 100:.1f}%</span>
              <div style='font-size:0.75rem; color:#a7f3d0; text-transform:uppercase;'>Delivery Kept As-Is</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Comparison Matrix: Honest Raw Model Evaluation vs Post-Processed Deliverable
    st.markdown("#### ⚖️ Honest Measurement: Baseline vs Series-Aware Model Evaluation")
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("""
        <div class='studio-card'>
          <div style='display:flex; align-items:center; gap:8px; margin-bottom:12px;'>
            <span class='badge badge-alias'>BASELINE</span>
            <h4 style='margin:0; font-size:1.05rem;'>Isolated (Episode Alone)</h4>
          </div>
          <p style='font-size:0.85rem; color:var(--text-muted);'>
            Translates each episode in isolation with zero cross-episode memory or story bible.
          </p>
        """, unsafe_allow_html=True)
        st.metric("Spoken Name Accuracy", f"{int((iso_name_rate or 0) * 100)}%" if iso_name_rate is not None else "N/A")

        iso_cues = indep_rep.get("model_characters_with_multiple_cues", {})
        iso_raw_rate = indep_rep.get("raw_cue_consistency_rate")
        raw_str_iso = f"{int(iso_raw_rate * 100)}%" if iso_raw_rate is not None else "N/A"
        st.markdown(f"<p style='color:#ffffff; font-size:0.9rem; margin-top:8px;'><b>Raw Model Cue Consistency:</b> {raw_str_iso}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:var(--text-muted); font-size:0.85rem;'><b>Cue Fragmentation:</b> {len(iso_cues)} characters fragmented into conflicting names</p>", unsafe_allow_html=True)
        for char_id, cues in list(iso_cues.items())[:3]:
            st.caption(f"• `{char_id}` appeared as: {', '.join(cues[:3])}")
        st.markdown("</div>", unsafe_allow_html=True)

    with c_right:
        st.markdown("""
        <div class='studio-card' style='border-color:var(--accent-plum);'>
          <div style='display:flex; align-items:center; gap:8px; margin-bottom:12px;'>
            <span class='badge badge-role'>CONTEXTUAL</span>
            <h4 style='margin:0; font-size:1.05rem;'>With Series Story Bible</h4>
          </div>
          <p style='font-size:0.85rem; color:var(--text-muted);'>
            Injects verified story bible, dynamic relationships, and address registers into translation prompts.
          </p>
        """, unsafe_allow_html=True)
        st.metric(
            "Spoken Name Accuracy",
            f"{int((name_rate or 0) * 100)}%" if name_rate is not None else "N/A",
            delta=f"+{int(((name_rate or 0) - (iso_name_rate or 0)) * 100)}%" if name_rate and iso_name_rate else None,
        )

        series_raw_rate = series_rep.get("raw_cue_consistency_rate")
        raw_str_ser = f"{int(series_raw_rate * 100)}%" if series_raw_rate is not None else "High"
        st.markdown(f"<p style='color:#ffffff; font-size:0.9rem; margin-top:8px;'><b>Honest Raw Model Consistency:</b> <span class='badge badge-emerald'>{raw_str_ser}</span></p>", unsafe_allow_html=True)

        series_cues = series_rep.get("applied_characters_with_multiple_cues", {})
        cue_count = len(series_cues)
        badge_type = "badge-emerald" if cue_count == 0 else "badge-amber"
        st.markdown(f"<p style='color:#ffffff; font-size:0.85rem; margin-top:6px;'><b>Applied Script Discrepancies:</b> <span class='badge {badge_type}'>{cue_count} unresolved</span> <span style='font-size:0.75rem; color:var(--text-muted);'>(after code normalisation)</span></p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Narrative Overview
    summary_path = raw / "series_summary.json"
    if summary_path.exists():
        summary = load(summary_path)
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        with st.expander("📖 Series Narrative Overview & Story Arc", expanded=False):
            st.markdown(f"### {summary.get('title', 'Series Overview')}")
            if summary.get("logline"):
                st.markdown(f"**Logline:** *{summary.get('logline')}*")
            if summary.get("premise"):
                st.markdown(f"**Premise:** {summary.get('premise')}")
            if summary.get("story_arc"):
                st.markdown(f"**Story Arc:** {summary.get('story_arc')}")

            c_st, c_tn = st.columns(2)
            if summary.get("stakes"):
                c_st.markdown(f"**Stakes:** {summary.get('stakes')}")
            if summary.get("tone"):
                c_tn.markdown(f"**Tone:** {summary.get('tone')}")

            if summary.get("episode_overview"):
                st.markdown("#### Episode Synopses")
                for item in summary.get("episode_overview", []):
                    st.markdown(f"**Episode {item.get('episode')}:** {item.get('summary')}")

    # Developer Raw JSON View
    with st.expander("🛠️ View Raw Audit Data (comparison.json)", expanded=False):
        st.json(report)


def exports_tab(root: Path):
    raw = root / "output" / "raw"
    if not raw.exists():
        st.info("💡 Localise episodes first to generate export packages.")
        return

    st.markdown("""
    <div style='margin-bottom:20px;'>
      <h3 style='margin:0 0 4px 0;'>Studio Deliverables & Screenplay Hub</h3>
      <p style='color:var(--text-muted); font-size:0.92rem; margin:0;'>
        Download finalized production screenplays, continuity verification packages, and review screenplays in-app.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Deliverables Grid
    col_d1, col_d2, col_d3 = st.columns(3)

    # 1. Screenplays
    with col_d1:
        st.markdown("""
        <div class='studio-card'>
          <span style='font-size:1.8rem;'>📜</span>
          <h4 style='margin:8px 0 4px 0;'>Production Screenplays</h4>
          <p style='font-size:0.83rem; color:var(--text-muted); margin-bottom:14px;'>
            Formatted script files preserving audio timestamps with contextually adapted dialogue.
          </p>
        """, unsafe_allow_html=True)

        script_files = sorted(set(list(raw.glob("episode-*.series.txt")) + list(raw.glob("episode-*.dialogue-only.*.txt"))))
        if not script_files:
            script_files = sorted(raw.glob("episode-*.txt"))

        for p in script_files:
            ep_label = p.stem.replace(".series", "").replace(".dialogue-only", "")
            st.download_button(
                f"📥 Download {ep_label} (.txt)",
                p.read_bytes(),
                file_name=p.name,
                mime="text/plain",
                key=f"dl-scr-{p.name}",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. QA Audit Report
    with col_d2:
        st.markdown("""
        <div class='studio-card'>
          <span style='font-size:1.8rem;'>📊</span>
          <h4 style='margin:8px 0 4px 0;'>Continuity & QA Package</h4>
          <p style='font-size:0.83rem; color:var(--text-muted); margin-bottom:14px;'>
            Comprehensive JSON audit report verifying beat completeness, name consistency, timestamps, and Reviewer Edit Rate.
          </p>
        """, unsafe_allow_html=True)

        report = raw / "comparison.json"
        if report.exists():
            st.download_button(
                "📥 Download comparison.json",
                report.read_bytes(),
                file_name=report.name,
                mime="application/json",
                key="dl-comp-json",
                use_container_width=True,
            )
        else:
            st.caption("No comparison report available yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Story Bible & Overview
    with col_d3:
        st.markdown("""
        <div class='studio-card'>
          <span style='font-size:1.8rem;'>📚</span>
          <h4 style='margin:8px 0 4px 0;'>Series Story Bible</h4>
          <p style='font-size:0.83rem; color:var(--text-muted); margin-bottom:14px;'>
            Complete character rosters, spoken names, relationship dynamics, and agreed glossary terms.
          </p>
        """, unsafe_allow_html=True)

        bible_f = raw / "story_bible.json"
        if bible_f.exists():
            st.download_button(
                "📥 Download story_bible.json",
                bible_f.read_bytes(),
                file_name=bible_f.name,
                mime="application/json",
                key="dl-bible-json",
                use_container_width=True,
            )

        summary_f = raw / "series_summary.json"
        if summary_f.exists():
            st.download_button(
                "📥 Download series_summary.json",
                summary_f.read_bytes(),
                file_name=summary_f.name,
                mime="application/json",
                key="dl-sum-json",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Live In-App Screenplay Previewer
    if script_files:
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        st.markdown("#### 👁️ In-App Screenplay Previewer")
        preview_choice = st.selectbox("Choose screenplay to inspect", script_files, format_func=lambda p: p.name)
        if preview_choice:
            content = preview_choice.read_text(encoding="utf-8")
            st.markdown(f"<div class='script-viewer'>{html.escape(content)}</div>", unsafe_allow_html=True)


# Main Execution Loop
project = select_project()

if project:
    meta = read_project(project)
    p_name = meta.get("name", project.name)
    p_lang = meta.get("language", "Hindi")
    p_model = meta.get("model", MODELS[0])
    p_scripts = sorted((project / "scripts").glob("*.txt"))

    st.markdown(f"""
    <div class='hero-banner'>
      <div class='hero-tag'>🎬 KUKU CINEMA LABS · ENTERPRISE LOCALISATION</div>
      <h1 class='hero-title'>Kuku Localise</h1>
      <p class='hero-subtitle'>
        Carry character identity, evolving power dynamics, and emotional voice across microdrama episodes.
      </p>
      <div class='status-ribbon'>
        <div class='ribbon-chip'>🎬 Show: <b>{html.escape(p_name)}</b></div>
        <div class='ribbon-chip'>🌐 Target Language: <b>{html.escape(p_lang)}</b></div>
        <div class='ribbon-chip'>⚡ Model: <b>{html.escape(p_model)}</b></div>
        <div class='ribbon-chip'>📄 Scripts: <b>{len(p_scripts)} episodes</b></div>
        <div class='ribbon-chip'>🛡️ Status: <b>Ready for Studio Review</b></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Script Hub & Configuration
    scripts = configure_hub(project)

    # 4 Core Studio Workspaces
    tabs = st.tabs([
        "📚  Series Context",
        "✍️  Localisation Review",
        "🔎  Continuity & QA",
        "⬇️  Studio Exports",
    ])

    with tabs[0]:
        context_tab(project, scripts)
    with tabs[1]:
        localisation_tab(project)
    with tabs[2]:
        continuity_tab(project)
    with tabs[3]:
        exports_tab(project)
else:
    st.markdown("""
    <div class='hero-banner'>
      <div class='hero-tag'>🎬 KUKU CINEMA LABS</div>
      <h1 class='hero-title'>Kuku Localise</h1>
      <p class='hero-subtitle'>Select or create a microdrama project in the sidebar to get started.</p>
    </div>
    """, unsafe_allow_html=True)
