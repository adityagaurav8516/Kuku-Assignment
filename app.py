from __future__ import annotations

import argparse
import json
from pathlib import Path

import streamlit as st

from kuku_localise.cli import run
from kuku_localise.export import render_episode
from kuku_localise.models import Episode
from kuku_localise.projects import create_project, list_projects, read_project, save_scripts, update_project

PROJECTS_DIR = Path("projects")
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro", "Custom model ID"]
LANGUAGES = ["Hindi", "Tamil", "Telugu", "Spanish", "English", "Custom language"]


def data(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def label(root: Path) -> str:
    return read_project(root).get("name") or root.name


def select_project() -> Path | None:
    st.sidebar.header("Microdrama projects")
    projects = list_projects(PROJECTS_DIR)
    with st.sidebar.expander("Create a project", expanded=not projects):
        name = st.text_input("Project name", placeholder="My new microdrama")
        if st.button("Create project", use_container_width=True):
            try:
                root = create_project(PROJECTS_DIR, name)
                st.session_state.project = str(root)
                st.rerun()
            except (ValueError, FileExistsError) as error:
                st.error(str(error))
    if not projects:
        st.info("Create a project to upload screenplay files.")
        return None
    current = st.session_state.get("project")
    index = next((i for i, item in enumerate(projects) if str(item) == current), 0)
    root = st.sidebar.selectbox("Open project", projects, index=index, format_func=label)
    st.session_state.project = str(root)
    return root


def configure(root: Path) -> None:
    metadata = read_project(root)
    st.subheader(label(root))
    st.caption("A project keeps its uploaded scripts, model settings, raw translations, and reviewed exports separate on this computer.")
    settings, upload = st.columns(2)
    with settings:
        language_current = metadata.get("language", "Hindi")
        language_choice = st.selectbox("Target language", LANGUAGES, index=LANGUAGES.index(language_current) if language_current in LANGUAGES else len(LANGUAGES) - 1)
        language = st.text_input("Language name", value=language_current) if language_choice == "Custom language" else language_choice
        model_current = metadata.get("model", MODELS[0])
        model_choice = st.selectbox("Translation model", MODELS, index=MODELS.index(model_current) if model_current in MODELS else len(MODELS) - 1)
        model = st.text_input("Gemini model ID", value=model_current) if model_choice == "Custom model ID" else model_choice
        if st.button("Save settings"):
            update_project(root, language=language.strip(), model=model.strip())
            st.success("Project settings saved.")
    with upload:
        files = st.file_uploader("Upload screenplay .txt files", type=["txt"], accept_multiple_files=True)
        if st.button("Add scripts", disabled=not files):
            st.success(f"Added {save_scripts(root, files or [])} screenplay file(s).")
    scripts = sorted((root / "scripts").glob("*.txt"))
    st.caption(f"{len(scripts)} uploaded screenplay file(s)")
    if scripts:
        with st.expander("Uploaded scripts"):
            st.write([script.name for script in scripts])


def translate(root: Path) -> None:
    metadata = read_project(root)
    scripts = root / "scripts"
    st.subheader("Translate and compare")
    selected = st.text_input("Episodes to compare", value="1,2,10", help="Comma-separated. Leave blank for the default selection.")
    if st.button("Build Story Bible and translate", type="primary", disabled=not list(scripts.glob("*.txt"))):
        args = argparse.Namespace(scripts=str(scripts), lang=metadata["language"], episodes=selected or None, output=str(root / "output"), model=metadata["model"])
        try:
            with st.spinner("Building the Story Bible and translating..."):
                run(args)
            st.success("Translation package is ready.")
        except Exception as error:
            st.error(f"Translation failed: {error}")


def review(root: Path) -> None:
    raw = root / "output" / "raw"
    if not raw.exists():
        return
    st.subheader("Results and review")
    comparison = raw / "comparison.json"
    if comparison.exists():
        report = data(comparison)
        a, b = st.columns(2)
        a.metric("Independent completeness", report["independent"].get("completeness"))
        b.metric("Series completeness", report["series"].get("completeness"))
        st.download_button("Download comparison report", comparison.read_bytes(), file_name="comparison.json", mime="application/json")
        with st.expander("Full consistency report"):
            st.json(report)
    series_files = sorted(raw.glob("episode-*.series.json"))
    episodes_file = raw / "episodes.json"
    if not series_files or not episodes_file.exists():
        return
    series_path = st.selectbox("Review episode", series_files, format_func=lambda path: path.stem.replace(".series", ""))
    series = data(series_path)
    independent_path = series_path.with_name(series_path.name.replace(".series.json", ".independent.json"))
    independent = data(independent_path) if independent_path.exists() else {"beats": {}}
    episode = next((Episode.from_dict(row) for row in data(episodes_file).get("episodes", []) if int(row["number"]) == int(series["episode"])), None)
    if episode is None:
        st.error("Missing parsed source data for this translation.")
        return
    output = raw / f"episode-{episode.number:03d}.series.txt"
    st.download_button("Download series translation", output.read_bytes(), file_name=output.name, mime="text/plain")
    edits: dict[str, str] = {}
    source = {beat.id: beat for beat in episode.beats()}
    for beat_id, record in series.get("beats", {}).items():
        original, alone, contextual = st.columns(3)
        original.text_area(f"Source {beat_id}", source.get(beat_id).text if beat_id in source else "", disabled=True, height=76)
        alone.text_area(f"Independent {beat_id}", (independent.get("beats", {}).get(beat_id) or {}).get("text", ""), disabled=True, height=76)
        edits[beat_id] = contextual.text_area(f"Series {beat_id}", record.get("text", ""), height=76)
    if st.button("Save approved screenplay"):
        reviewed = root / "output" / "reviewed"
        reviewed.mkdir(parents=True, exist_ok=True)
        approved = render_episode(episode, series, edits)
        approved_path = reviewed / f"episode-{episode.number:03d}.approved.txt"
        approved_path.write_text(approved, encoding="utf-8")
        st.success("Approved screenplay saved.")
        st.download_button("Download approved screenplay", approved, file_name=approved_path.name, mime="text/plain")


st.set_page_config(page_title="Kuku Localise", layout="wide")
st.title("Kuku Localise")
project = select_project()
if project:
    configure(project)
    st.divider()
    translate(project)
    review(project)
