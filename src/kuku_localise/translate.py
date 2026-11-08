from __future__ import annotations

import json

from kuku_localise.bible import bible_slice, character_for_cue
from kuku_localise.llm import GeminiClient
from kuku_localise.models import Episode
from kuku_localise.parse import is_translatable

TRANSLATE_SYSTEM = """You localise microdrama screenplay beats into the requested language.
Return one JSON object with this shape:
{"headings": [{"scene": 1, "heading": "..."}], "beats": [{"id": "...", "text": "...", "parenthetical": "...", "display_name": "...", "speaker": "...", "listener_or_target": "...", "relationship_context": "...", "localisation_note": "..."}]}
Include every beat id you were given, exactly once.
text is the translation of that beat only. Do not merge beats, drop a line, or add events.
parenthetical is a short acting note in the target language, or an empty string when the source note is empty.
display_name is the cue label for a dialogue beat. Use an empty string for action, sound, and music.
For each dialogue beat, give a concise relationship_context and explain the localisation choice in localisation_note. Identify a listener_or_target only when the line makes one clear; otherwise use an empty string. These are model-generated editorial notes, not verified facts. For non-dialogue beats, these context fields should be empty.
Preserve who is speaking, the facts, and the emotional force. Do not soften an insult or explain a joke.
Do not include timestamps in the text. Code copies the timestamps.
"""


def _payload(episode: Episode) -> tuple[list[dict], list[dict]]:
    headings = [
        {"scene": scene.number, "heading": scene.heading}
        for scene in episode.scenes
        if scene.heading
    ]
    beats = [
        {
            "id": beat.id,
            "kind": beat.kind,
            "cue": beat.cue,
            "parenthetical": beat.parenthetical,
            "text": beat.text,
        }
        for beat in episode.beats()
        if is_translatable(beat.kind) and beat.text.strip()
    ]
    return headings, beats


def _normalise(data: dict) -> tuple[dict[int, str], dict[str, dict]]:
    headings = {}
    for item in data.get("headings") or []:
        if isinstance(item, dict) and item.get("scene") is not None:
            headings[int(item["scene"])] = str(item.get("heading") or "").strip()
    beats = {}
    for item in data.get("beats") or []:
        if isinstance(item, dict) and item.get("id"):
            beats[str(item["id"])] = {
                "text": str(item.get("text") or "").strip(),
                "parenthetical": str(item.get("parenthetical") or "").strip(),
                "display_name": str(item.get("display_name") or "").strip(),
                "speaker": str(item.get("speaker") or "").strip(),
                "listener_or_target": str(item.get("listener_or_target") or "").strip(),
                "relationship_context": str(item.get("relationship_context") or "").strip(),
                "localisation_note": str(item.get("localisation_note") or "").strip(),
            }
    return headings, beats


def _ask(client: GeminiClient, user: str, expected_ids: list[str]) -> tuple[dict[int, str], dict[str, dict]]:
    data = client.complete_json(TRANSLATE_SYSTEM, user)
    headings, beats = _normalise(data)
    missing = [beat_id for beat_id in expected_ids if not beats.get(beat_id, {}).get("text")]
    if not missing:
        return headings, beats
    repair_user = (
        user
        + "\n\nThe previous answer missed these beat ids or left the text empty: "
        + ", ".join(missing)
        + ". Return JSON for every missing id listed here, and no others."
    )
    repaired = client.complete_json(TRANSLATE_SYSTEM, repair_user)
    _, repaired_beats = _normalise(repaired)
    beats.update({key: value for key, value in repaired_beats.items() if value.get("text")})
    return headings, beats


def apply_display_names(bible: dict, episode: Episode, beats: dict[str, dict]) -> dict[str, dict]:
    applied = {}
    for beat in episode.beats():
        record = dict(beats.get(beat.id) or {})
        if not record:
            continue
        record["model_display_name"] = record.get("display_name") or ""
        if beat.kind == "dialogue":
            character = character_for_cue(bible, beat.cue)
            if character and character.get("display_name"):
                record["display_name"] = character["display_name"]
        applied[beat.id] = record
    return applied


def translate_episode(
    client: GeminiClient,
    episode: Episode,
    bible: dict,
    target_language: str,
    mode: str,
    previous_logline: str,
) -> dict:
    headings, beats = _payload(episode)
    shared = {
        "target_language": target_language,
        "episode_number": episode.number,
        "logline": episode.logline,
        "continuity": episode.continuity,
        "headings": headings,
        "beats": beats,
    }
    if mode == "series":
        cues = [beat["cue"] for beat in beats if beat["kind"] == "dialogue"]
        user = (
            "Mode: series. Use the story bible. For every dialogue line, apply character voice, relationships, address, continuity, and glossary. "
            "For each dialogue beat, set display_name to that character's display_name. "
            "Use spoken_name when a line names a person, and use each glossary target for its source term. "
            "Follow address guidance. Add short relationship_context and localisation_note that describe the main contextual choice. Mark these as editorial rationale, not factual certainty.\n\n"
            + json.dumps(
                {
                    **shared,
                    "previous_episode_logline": previous_logline,
                    "story_bible": bible_slice(bible, cues, episode.number),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif mode == "independent":
        user = (
            "Mode: independent. You have no other episodes, no glossary, and no story bible. "
            "Localise this episode on its own. Set display_name from the cue in front of you.\n\n"
            + json.dumps(shared, ensure_ascii=False, indent=2)
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")
    expected = [beat["id"] for beat in beats]
    heading_map, beat_map = _ask(client, user, expected)
    model_beats = {key: dict(value) for key, value in beat_map.items()}
    deliverable = apply_display_names(bible, episode, beat_map) if mode == "series" else beat_map
    return {
        "episode": episode.number,
        "mode": mode,
        "headings": {str(number): heading for number, heading in heading_map.items()},
        "beats": deliverable,
        "model_beats": model_beats,
    }
