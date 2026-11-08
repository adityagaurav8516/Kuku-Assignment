from __future__ import annotations

import json

from kuku_localise.index import significant_tokens
from kuku_localise.llm import GeminiClient

BIBLE_SYSTEM = """You build a Story Bible used to localise one microdrama series.
The index was extracted by code from the screenplays. Do not invent plot events that the index does not support.
Merge cue strings that name the same person. Keep different people separate.
possible_alias_groups only means those cues share a name token. Merge a group when the samples and loglines show they are one person. A descriptive cue such as THE STRANGER can still be a named character if the loglines say so.
Return one JSON object with these keys:
series_title, target_language, adaptation_policy, characters, glossary, plot_spine.
Each character has: id, display_name, spoken_name, surface_forms, role, relationships, speech_style, address.
display_name is the cue label to print in the localised script.
spoken_name is the name other characters should say in the target language.
When a proper name should keep its original spelling, use that same spelling for display_name and spoken_name.
surface_forms must list every source cue you merged, copied exactly.
glossary items have: source, decision, target, note.
decision is "keep" or "adapt". Include only terms that recur or carry cultural weight.
plot_spine items have: episode, summary. Write one item for every episode number in the index.
Write adaptation_policy, role, relationships, speech_style, address, summary, and note in English so a reviewer can edit them.
spoken_name, display_name, and glossary target may use the target language.
adaptation_policy must say how forms of address should change with the relationship, and what the translation must not change: plot facts, who speaks, and the force of the last line.
"""


def build_bible(client: GeminiClient, index: dict, series_name: str, target_language: str) -> dict:
    user = (
        f"Series folder name: {series_name}\n"
        f"Target language: {target_language}\n\n"
        "SCREENPLAY INDEX:\n"
        + json.dumps(index, ensure_ascii=False, indent=2)
    )
    data = client.complete_json(BIBLE_SYSTEM, user)
    characters = []
    seen_ids: set[str] = set()
    for raw in data.get("characters") or []:
        if not isinstance(raw, dict):
            continue
        forms = [str(form).strip() for form in raw.get("surface_forms") or [] if str(form).strip()]
        if not forms and raw.get("display_name"):
            forms = [str(raw["display_name"]).strip()]
        character_id = str(raw.get("id") or "character").strip().lower().replace(" ", "-")
        if character_id in seen_ids:
            character_id = f"{character_id}-{len(seen_ids)}"
        seen_ids.add(character_id)
        characters.append(
            {
                "id": character_id,
                "display_name": str(raw.get("display_name") or (forms[0] if forms else character_id)).strip(),
                "spoken_name": str(raw.get("spoken_name") or raw.get("display_name") or "").strip(),
                "surface_forms": forms,
                "role": str(raw.get("role") or "").strip(),
                "relationships": str(raw.get("relationships") or "").strip(),
                "speech_style": str(raw.get("speech_style") or "").strip(),
                "address": str(raw.get("address") or "").strip(),
            }
        )
    glossary = []
    for raw in data.get("glossary") or []:
        if not isinstance(raw, dict) or not str(raw.get("source") or "").strip():
            continue
        decision = str(raw.get("decision") or "adapt").strip().lower()
        if decision not in {"keep", "adapt"}:
            decision = "adapt"
        glossary.append(
            {
                "source": str(raw["source"]).strip(),
                "decision": decision,
                "target": str(raw.get("target") or raw.get("source") or "").strip(),
                "note": str(raw.get("note") or "").strip(),
            }
        )
    spine = []
    for raw in data.get("plot_spine") or []:
        if isinstance(raw, dict) and raw.get("episode") is not None:
            spine.append({"episode": int(raw["episode"]), "summary": str(raw.get("summary") or "").strip()})
    return {
        "series_title": str(data.get("series_title") or series_name).strip(),
        "target_language": str(data.get("target_language") or target_language).strip(),
        "adaptation_policy": str(data.get("adaptation_policy") or "").strip(),
        "characters": characters,
        "glossary": glossary,
        "plot_spine": spine,
    }


def character_for_cue(bible: dict, cue: str) -> dict | None:
    target = cue.strip().casefold()
    for character in bible.get("characters") or []:
        forms = [character.get("display_name") or "", *(character.get("surface_forms") or [])]
        if any(str(form).strip().casefold() == target for form in forms if str(form).strip()):
            return character
    cue_tokens = significant_tokens(cue)
    best = None
    best_score = 0
    for character in bible.get("characters") or []:
        tokens: set[str] = set()
        for form in character.get("surface_forms") or []:
            tokens |= significant_tokens(str(form))
        score = len(cue_tokens & tokens)
        if score > best_score:
            best, best_score = character, score
    return best if best_score else None


def bible_slice(bible: dict, cues: list[str], episode_number: int) -> dict:
    matched = []
    seen: set[str] = set()
    for cue in cues:
        character = character_for_cue(bible, cue)
        if character and character["id"] not in seen:
            matched.append(character)
            seen.add(character["id"])
    nearby = [
        item
        for item in bible.get("plot_spine") or []
        if abs(int(item.get("episode", 0)) - episode_number) <= 1
    ]
    return {
        "target_language": bible.get("target_language"),
        "adaptation_policy": bible.get("adaptation_policy"),
        "characters": matched,
        "glossary": bible.get("glossary") or [],
        "nearby_plot": nearby,
    }
