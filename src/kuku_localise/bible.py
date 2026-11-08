from __future__ import annotations

import json
import re

from kuku_localise.index import significant_tokens
from kuku_localise.llm import BaseLLMClient

GENERIC_DESCRIPTORS = {
    "voice",
    "voices",
    "stranger",
    "man",
    "woman",
    "guy",
    "girl",
    "boy",
    "guard",
    "nurse",
    "doctor",
    "officer",
    "cop",
    "waiter",
    "waitress",
    "driver",
    "courier",
    "messenger",
    "announcer",
    "phone",
    "caller",
    "maid",
    "servant",
    "assistant",
    "crowd",
    "chorus",
    "shadow",
    "figure",
}

BIBLE_SYSTEM = """You build a Story Bible used to localise one microdrama series.
The index was extracted by code from the screenplays. Do not invent plot events that the index does not support.
Merge cue strings that name the same person. Keep different people separate.
possible_alias_groups only means those cues share a name token. Merge a group when the samples and loglines show they are one person.
Do NOT blindly merge generic cues like "OFF-SCREEN VOICE", "STRANGER", or "CALLER" unless the dialogue clearly attributes them to that person. If ambiguous, keep them separate or note the merge uncertainty.

Return one JSON object with these keys:
series_title, target_language, adaptation_policy, characters, glossary, plot_spine.

Each character has:
- id: kebab-case identifier (e.g. "lady-juliana", "mira")
- display_name: canonical cue label to print in the localised script
- spoken_name: the name other characters say aloud in the target language dialogue
- surface_forms: list of all source cue variations merged into this character
- gender: "male", "female", "non-binary", or "unknown" (CRITICAL for target languages like Hindi with gendered verb agreement like करता/करती, गया/गई)
- address_register: primary register used by/toward this character: "aap" (formal/respectful), "tum" (familiar/peer), or "tu" (intimate/contemptuous)
- role: narrative role (e.g. "Protagonist, disgraced heiress")
- relationships: dynamic relationships with other characters (e.g. "Employer to Mira; bitter rival to Lord Gerald; estranged daughter of Duke")
- speech_style: tone and diction (e.g. "Sharp, aristocratic, controlled, never raises voice")
- address: specific honorifics and forms of address used for and by this character
- ambiguous_merges: list of merged surface forms that are generic descriptors or inferences, with rationale

glossary items have: source, decision ("keep" or "adapt"), target, note. Include recurring terms and cultural concepts.
plot_spine items have: episode (int), summary. One item for each episode in the index.
Write adaptation_policy, role, relationships, speech_style, address, and notes in English for reviewer inspection.
"""


def detect_flagged_merges(index: dict, characters: list[dict]) -> list[dict]:
    """Detect low-confidence merges or generic descriptor attributions for human review."""
    flagged: list[dict] = []
    alias_groups = index.get("possible_alias_groups") or []

    for char in characters:
        display = char.get("display_name", "")
        display_tokens = significant_tokens(display)
        char_flagged: list[dict] = []

        for form in char.get("surface_forms", []):
            if form == display:
                continue
            form_tokens = significant_tokens(form)
            overlap = display_tokens & form_tokens

            # Check if surface form is a generic descriptor
            form_words = {w.lower() for w in re.findall(r"[A-Za-z]+", form)}
            is_generic = bool(form_words & GENERIC_DESCRIPTORS)

            # Check if this pair was never in index's possible_alias_groups
            in_group = any(display in group and form in group for group in alias_groups)

            reasons = []
            if is_generic and not overlap:
                reasons.append(f"Generic descriptor cue '{form}' merged into '{display}' with no shared name tokens")
            elif not overlap and not in_group:
                reasons.append(f"Surface form '{form}' has zero token overlap with canonical name '{display}'")

            if reasons:
                item = {
                    "character_id": char.get("id"),
                    "display_name": display,
                    "surface_form": form,
                    "reasons": reasons,
                    "confidence": "low",
                }
                char_flagged.append(item)
                flagged.append(item)

        char["low_confidence_merges"] = char_flagged
        char["needs_review"] = bool(char_flagged)

    return flagged


def build_bible(client: BaseLLMClient, index: dict, series_name: str, target_language: str) -> dict:
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

        # Extract expanded variables: gender, address_register, relationships
        gender = str(raw.get("gender") or "unknown").strip().lower()
        if gender not in {"male", "female", "non-binary", "unknown"}:
            gender = "unknown"

        register = str(raw.get("address_register") or "aap").strip().lower()
        if "tu" in register and "tum" not in register and "aap" not in register:
            register = "tu"
        elif "tum" in register:
            register = "tum"
        else:
            register = "aap"

        characters.append(
            {
                "id": character_id,
                "display_name": str(raw.get("display_name") or (forms[0] if forms else character_id)).strip(),
                "spoken_name": str(raw.get("spoken_name") or raw.get("display_name") or "").strip(),
                "surface_forms": forms,
                "gender": gender,
                "address_register": register,
                "role": str(raw.get("role") or "").strip(),
                "relationships": str(raw.get("relationships") or "").strip(),
                "speech_style": str(raw.get("speech_style") or "").strip(),
                "address": str(raw.get("address") or "").strip(),
                "ambiguous_merges": raw.get("ambiguous_merges") or [],
            }
        )

    # Flag low confidence merges for human review in the Bible UI
    flagged = detect_flagged_merges(index, characters)

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
        "flagged_merges": flagged,
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
