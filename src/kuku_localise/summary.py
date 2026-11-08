from __future__ import annotations

import json

from kuku_localise.llm import GeminiClient


SUMMARY_SYSTEM = """You are a development editor summarising a microdrama series from a screenplay index.
Do not invent events or characters. Return JSON with: title, logline, premise, story_arc, key_characters, stakes, tone, episode_overview.
key_characters is an array of {name, role}. episode_overview is an array of {episode, summary} covering the supplied episodes.
Write clear English intended for a producer; keep each field concise."""


def build_series_summary(client: GeminiClient, index: dict, bible: dict) -> dict:
    payload = {"series_index": index, "story_bible": {"series_title": bible.get("series_title"), "characters": bible.get("characters"), "plot_spine": bible.get("plot_spine")}}
    result = client.complete_json(SUMMARY_SYSTEM, json.dumps(payload, ensure_ascii=False, indent=2))
    return {
        "title": str(result.get("title") or bible.get("series_title") or "Untitled series"),
        "logline": str(result.get("logline") or ""),
        "premise": str(result.get("premise") or ""),
        "story_arc": str(result.get("story_arc") or ""),
        "key_characters": [item for item in result.get("key_characters") or [] if isinstance(item, dict)],
        "stakes": str(result.get("stakes") or ""),
        "tone": str(result.get("tone") or ""),
        "episode_overview": [item for item in result.get("episode_overview") or [] if isinstance(item, dict)],
    }
