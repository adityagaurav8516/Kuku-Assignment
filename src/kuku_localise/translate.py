from __future__ import annotations

import json

from kuku_localise.bible import bible_slice, character_for_cue
from kuku_localise.llm import BaseLLMClient
from kuku_localise.models import Episode
from kuku_localise.parse import is_translatable
from kuku_localise.validation import validate_beat

INDEPENDENT_SYSTEM = """You are a mechanical, context-blind, literal word-for-word translation engine.
Your sole task is to produce a strict, verbatim, word-by-word literal translation of the English source text.
You have NO access to character dossiers, NO knowledge of social hierarchies, NO continuity notes, and NO story bible.

CRITICAL INSTRUCTIONS FOR BASELINE TRANSLATION:
1. STRICT WORD-FOR-WORD LITERALISM:
   - Translate words directly, mechanically, and literally in the exact structure they appear in English, like a simple dictionary substitution.
   - Do NOT adapt idioms, do NOT rewrite for dramatic flow, do NOT use cinematic phrasing, and do NOT transcreate subtext.
   - Examples of required word-for-word literal translation (English -> Hindi):
     * "You came back for the ring, Lady Juliana?" -> "क्या आप अंगूठी के लिए वापस आईं, लेडी जुलियाना?" (Direct literal translation of words)
     * "I came back for the truth." -> "मैं सच के लिए वापस आई।" (Verbatim literal mapping)
     * "Do not call me that. You chose this silence." -> "मुझे वह मत बुलाओ। आपने यह चुप्पी चुनी।" (Stiff literal mapping)
     * "Tomorrow the whole manor will know." -> "कल पूरा मैनर जान जाएगा।" (Direct word substitution, transliterating 'manor' as 'मैनर')
2. ZERO CHARACTER OR RELATIONSHIP CONTEXT:
   - Use flat, generic polite textbook pronouns ('आप') for everyone equally, regardless of who is speaking to whom.
   - Do not convey emotions, dramatic subtext, or character personality. Keep it completely flat, robotic, and literal.

Return one JSON object with this shape:
{"headings": [{"scene": 1, "heading": "..."}], "beats": [{"id": "...", "text": "...", "parenthetical": "...", "display_name": "...", "speaker": "", "listener_or_target": "", "relationship_context": "", "localisation_note": "", "adaptation_applied": false}]}
Do not include timestamps in the text.
"""

SERIES_SYSTEM = """You are an elite microdrama dialogue director and master transcreator for cinema and dubbing.
Your mission is to localise this serialized microdrama script into gripping, natural, actor-ready dialogue that matches the scene's emotional stakes, subtext, and strict audio timing.

Return one JSON object with this shape:
{"headings": [{"scene": 1, "heading": "..."}], "beats": [{"id": "...", "text": "...", "parenthetical": "...", "display_name": "...", "speaker": "...", "listener_or_target": "...", "relationship_context": "...", "localisation_note": "...", "adaptation_applied": true}]}

CRITICAL LOCALISATION PRINCIPLES:

1. STORY ACCURACY OVER WORD-FOR-WORD TRANSLATION (TRANSCREATION):
   - NEVER translate English grammar literally into the target language! Literal translations sound amateurish and broken.
   - Translate the *character's intention, subtext, and emotional objective* in the scene.
   - Examples of Story-Accurate Transcreation (English -> Hindi):
     * BAD (Literal): "You came back for the ring?" -> "क्या आप अंगूठी के लिए वापस आईं?" (Clunky, textbook)
     * GOOD (Cinematic): "अंगूठी लेने आई हो?" or "तो... अंगूठी वापस चाहिए?" (Sharp, natural, tense)
     * BAD (Literal): "I came back for the truth." -> "मैं सच के लिए वापस आई।" (Unnatural Hindi)
     * GOOD (Cinematic): "मुझे सिर्फ सच चाहिए।" or "मैं सच जानने आई हूँ।" (Punchy, emotional)
     * BAD (Literal): "Do not call me that. You chose this silence." -> "मुझे वह मत कहो। तुमने यह चुप्पी चुनी।" (Stiff)
     * GOOD (Cinematic): "मुझे उस नाम से मत बुलाओ। यह खामोशी तुम्हारी अपनी पसंद थी।" (Natural dramatic dialogue)
     * BAD (Literal): "Tomorrow the whole manor will know." -> "कल पूरे मैनर को पता चल जाएगा।" (Google Translate style)
     * GOOD (Cinematic): "कल सुबह तक हवेली में सबको सच पता चल जाएगा।" (Cinematic, atmospheric)

2. STRICT AUDIO DURATION & TIMING FIT (DUBBING-READY):
   - Voice actors must speak each line within the 'duration_seconds' and 'max_character_budget' provided.
   - In Hindi, ~15-18 characters equal approximately 1 second of natural speech.
   - If a literal translation has too many syllables, DO NOT let it overflow the time window!
   - Condense, rephrase, and sculpt the line down to its sharpest dramatic core so it fits within 'max_character_budget' while keeping 100% of the emotional punch.

3. POWER DYNAMICS & SOCIAL HIERARCHY:
   - Strictly honor each character's address_register (aap / tum / tu) and social status from the Story Bible.
   - Superiors/matriarchs speak with commanding authority and sharp diction; subordinates/servants speak with deferential honorifics ('आप', 'हुज़ूर', 'मालिक'); bitter rivals speak with biting, loaded subtext.
   - Never use flat generic politeness when the scene demands tension or disdain.

4. GENDER & GRAMMAR CONJUGATION:
   - Strictly align verb inflections and pronouns with the character's designated gender (Hindi: करता है/गया vs करती है/गई).

5. CONTINUITY SUBTEXT & BACKSTORY:
   - Use the prior episode logline and continuity notes to infuse unsaid history, past betrayals, and tension into the scene.
Do not include timestamps in the text.
"""

REPAIR_SYSTEM = """You are a senior dubbing script doctor repairing localised dialogue beats that failed audio timing, character limits, or address consistency.
Return one JSON object with this shape:
{"beats": [{"id": "...", "text": "...", "parenthetical": "...", "display_name": "...", "localisation_note": "..."}]}

REPAIR DIRECTIVES:
- If a line failed timing because it is too long for the audio duration:
  DO NOT simply truncate words! Re-craft the line into punchy, concise, natural dialogue that conveys the exact same dramatic meaning in fewer syllables so it fits within the required character budget.
- If an address register failed:
  Adjust pronouns and verb endings to strictly match the required register (e.g. formal 'aap' vs familiar 'tum' vs contemptuous 'tu') while preserving natural flow.
"""

CULTURAL_ADAPTATION_SYSTEM = """You are a senior cultural localisation editor for microdramas.
Inspect the dialogue beats and identify any Western/US idioms, colloquialisms, pop-culture references, or metaphors that need cultural localisation.
Return one JSON object with this shape:
{"adaptations": [{"id": "...", "idiom_found": "...", "original_meaning": "...", "cultural_adaptation": "...", "note": "..."}]}
Only return entries for beats that contain notable idioms or cultural adaptations. If none, return empty list.
"""


def _payload(episode: Episode) -> tuple[list[dict], list[dict]]:
    headings = [
        {"scene": scene.number, "heading": scene.heading}
        for scene in episode.scenes
        if scene.heading
    ]
    beats = []
    history: list[str] = []
    for scene in episode.scenes:
        for beat in scene.beats:
            if not is_translatable(beat.kind) or not beat.text.strip():
                continue
            # Calculate calibrated character budget for dubbing timing (~16 chars per second)
            max_char_budget = max(20, int(beat.duration * 16.0)) if beat.duration > 0.5 else None
            entry = {
                "id": beat.id,
                "scene": scene.number,
                "scene_heading": scene.heading or f"Scene {scene.number}",
                "kind": beat.kind,
                "cue": beat.cue,
                "parenthetical": beat.parenthetical,
                "duration_seconds": beat.duration,
                "max_character_budget": max_char_budget,
                "text": beat.text,
            }
            if beat.kind == "dialogue":
                entry["recent_dialogue_context"] = history[-2:] if history else []
                history.append(f"{beat.cue}: {beat.text}")
            beats.append(entry)
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
                "model_display_name": str(item.get("display_name") or "").strip(),
                "speaker": str(item.get("speaker") or "").strip(),
                "listener_or_target": str(item.get("listener_or_target") or "").strip(),
                "relationship_context": str(item.get("relationship_context") or "").strip(),
                "localisation_note": str(item.get("localisation_note") or "").strip(),
                "adaptation_applied": bool(item.get("adaptation_applied", False)),
            }
    return headings, beats


def _ask(
    client: BaseLLMClient,
    system_instruction: str,
    user: str,
    expected_ids: list[str],
) -> tuple[dict[int, str], dict[str, dict]]:
    data = client.complete_json(system_instruction, user)
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
    repaired = client.complete_json(system_instruction, repair_user)
    _, repaired_beats = _normalise(repaired)
    beats.update({key: value for key, value in repaired_beats.items() if value.get("text")})
    return headings, beats


def apply_display_names(bible: dict, episode: Episode, beats: dict[str, dict]) -> dict[str, dict]:
    applied = {}
    for beat in episode.beats():
        record = dict(beats.get(beat.id) or {})
        if not record:
            continue
        # Preserve honest raw model cue output before post-processing override
        record["model_display_name"] = record.get("display_name") or record.get("model_display_name") or ""
        if beat.kind == "dialogue":
            character = character_for_cue(bible, beat.cue)
            if character and character.get("display_name"):
                record["display_name"] = character["display_name"]
        applied[beat.id] = record
    return applied


def _validate_and_repair(
    client: BaseLLMClient,
    beats: dict[str, dict],
    episode: Episode,
    bible: dict,
    target_lang: str,
    max_retries: int = 2,
) -> dict[str, dict]:
    """Automated Repair Loop: validate with plain code and retry failing beats up to 2 times."""
    beat_lookup = {b.id: b for b in episode.beats()}

    for retry in range(max_retries):
        failures: list[dict] = []
        for bid, record in beats.items():
            beat = beat_lookup.get(bid)
            if not beat or beat.kind != "dialogue":
                continue
            char = character_for_cue(bible, beat.cue)
            errors = validate_beat(beat, record, char, target_lang)
            if errors:
                failures.append(
                    {
                        "id": bid,
                        "cue": beat.cue,
                        "source_text": beat.text,
                        "duration_seconds": beat.duration,
                        "target_character_budget": max(20, int(beat.duration * 16.0)) if beat.duration > 0.5 else 40,
                        "current_translation": record.get("text", ""),
                        "current_char_count": len((record.get("text") or "").strip()),
                        "validation_errors": errors,
                    }
                )
        if not failures:
            break

        repair_prompt = (
            f"Target Language: {target_lang}\n"
            f"Repair Pass {retry + 1} of {max_retries}: The following dialogue beats failed audio timing or register validation rules.\n"
            "Re-sculpt and shorten the lines to fit within the audio budget while preserving cinematic punch and emotional subtext:\n\n"
            + json.dumps(failures, ensure_ascii=False, indent=2)
        )
        try:
            repaired_data = client.complete_json(REPAIR_SYSTEM, repair_prompt)
            _, rep_beats = _normalise(repaired_data)
            for bid, rep_rec in rep_beats.items():
                if bid in beats and rep_rec.get("text"):
                    beats[bid]["text"] = rep_rec["text"]
                    if rep_rec.get("localisation_note"):
                        beats[bid]["localisation_note"] = rep_rec["localisation_note"]
        except Exception:
            break

    # Tag all beats with verified status or Honest Failure
    for bid, record in beats.items():
        beat = beat_lookup.get(bid)
        if not beat or beat.kind != "dialogue":
            continue
        char = character_for_cue(bible, beat.cue)
        final_errors = validate_beat(beat, record, char, target_lang)
        if final_errors:
            record["validation_failed"] = True
            record["validation_errors"] = final_errors
            record["status"] = "honest_failure"
        else:
            record["validation_failed"] = False
            record["validation_errors"] = []
            record["status"] = "verified"

    return beats


def cultural_adaptation_pass(
    client: BaseLLMClient,
    episode: Episode,
    beats: dict[str, dict],
    target_language: str,
) -> dict[str, dict]:
    """Secondary LLM pass identifying cultural idioms and attaching adaptation notes."""
    dialogue_samples = []
    beat_lookup = {b.id: b for b in episode.beats()}
    for bid, rec in beats.items():
        beat = beat_lookup.get(bid)
        if beat and beat.kind == "dialogue" and rec.get("text"):
            dialogue_samples.append({
                "id": bid,
                "cue": beat.cue,
                "source_english": beat.text,
                "target_translation": rec.get("text"),
            })

    if not dialogue_samples:
        return beats

    user_prompt = (
        f"Target language: {target_language}\n"
        "Identify idioms, pop culture references, or cultural expressions in these beats and evaluate their adaptation:\n\n"
        + json.dumps(dialogue_samples[:30], ensure_ascii=False, indent=2)
    )
    try:
        data = client.complete_json(CULTURAL_ADAPTATION_SYSTEM, user_prompt)
        for item in data.get("adaptations") or []:
            if isinstance(item, dict) and item.get("id") in beats:
                beats[item["id"]]["cultural_adaptation"] = {
                    "idiom_found": item.get("idiom_found", ""),
                    "original_meaning": item.get("original_meaning", ""),
                    "cultural_adaptation": item.get("cultural_adaptation", ""),
                    "note": item.get("note", ""),
                }
    except Exception:
        pass
    return beats


def translate_episode(
    client: BaseLLMClient,
    episode: Episode,
    bible: dict,
    target_language: str,
    mode: str,
    previous_logline: str,
    run_cultural_pass: bool = True,
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
        system_instruction = SERIES_SYSTEM
        cues = [beat["cue"] for beat in beats if beat["kind"] == "dialogue"]
        user = (
            "Mode: series (Context-Rich Dramatic Localisation & Dubbing Fit).\n"
            "Apply the provided Story Bible character voices, relationship hierarchies, and address registers strictly.\n"
            "DO NOT translate literally! Transcreate the emotional intent and dramatic subtext.\n"
            "Ensure every line strictly fits within its 'max_character_budget' and 'duration_seconds' so voice actors can deliver it naturally.\n"
            "For each dialogue beat, set display_name to that character's display_name from the bible.\n"
            "Use spoken_name when a line names a person, and use each glossary target for its source term.\n"
            "Follow address guidance (aap / tum / tu) based on character dynamics.\n"
            "Add short relationship_context and localisation_note describing the editorial choice.\n\n"
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
        system_instruction = INDEPENDENT_SYSTEM
        user = (
            "Mode: independent (Mechanical Word-for-Word Literal Translation).\n"
            "You have NO external context, NO relationships, and NO story bible.\n"
            "Translate each line strictly WORD-FOR-WORD and literally in the exact English sentence order.\n"
            "Use mechanical dictionary substitutions and flat generic polite textbook grammar ('आप') for all lines.\n"
            "Do NOT adapt idioms and do NOT write natural dramatic dialogue.\n"
            "Set display_name strictly from the cue in front of you.\n\n"
            + json.dumps(shared, ensure_ascii=False, indent=2)
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")

    expected = [beat["id"] for beat in beats]
    heading_map, beat_map = _ask(client, system_instruction, user, expected)

    # Step 4 & 5: Automated Repair Loop for series mode
    if mode == "series":
        beat_map = _validate_and_repair(client, beat_map, episode, bible, target_language, max_retries=2)
        if run_cultural_pass:
            beat_map = cultural_adaptation_pass(client, episode, beat_map, target_language)

    # Preserve honest raw model cues
    model_beats = {key: dict(value) for key, value in beat_map.items()}

    # Post-process display names for deliverable
    deliverable = apply_display_names(bible, episode, beat_map) if mode == "series" else beat_map

    return {
        "episode": episode.number,
        "mode": mode,
        "headings": {str(number): heading for number, heading in heading_map.items()},
        "beats": deliverable,
        "model_beats": model_beats,
    }
