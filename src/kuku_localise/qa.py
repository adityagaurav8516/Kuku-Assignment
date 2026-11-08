from __future__ import annotations

import re

from kuku_localise.bible import character_for_cue
from kuku_localise.export import render_episode
from kuku_localise.models import Episode
from kuku_localise.parse import is_translatable
from kuku_localise.validation import compute_edit_rate, compute_levenshtein


def _rate(hits: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(hits / total, 3)


def _cue_variants(episode: Episode, translation: dict, bible: dict) -> dict[str, list[str]]:
    """Evaluate raw model outputs (model_display_name) to honestly measure model consistency."""
    grouped: dict[str, set[str]] = {}
    model_beats = translation.get("model_beats") or translation.get("beats") or {}
    for beat in episode.beats():
        if beat.kind != "dialogue":
            continue
        record = model_beats.get(beat.id) or {}
        # Prioritize honest raw model output
        raw_name = (record.get("model_display_name") or record.get("display_name") or beat.cue).strip()
        character = character_for_cue(bible, beat.cue)
        key = character["id"] if character else beat.cue
        grouped.setdefault(key, set()).add(raw_name)
    return {key: sorted(values) for key, values in sorted(grouped.items())}


def _applied_variants(episode: Episode, translation: dict, bible: dict) -> dict[str, list[str]]:
    """Evaluate post-processed applied cues for production delivery comparison."""
    grouped: dict[str, set[str]] = {}
    beats = translation.get("beats") or {}
    for beat in episode.beats():
        if beat.kind != "dialogue":
            continue
        record = beats.get(beat.id) or {}
        rendered = (record.get("display_name") or beat.cue).strip()
        character = character_for_cue(bible, beat.cue)
        key = character["id"] if character else beat.cue
        grouped.setdefault(key, set()).add(rendered)
    return {key: sorted(values) for key, values in sorted(grouped.items())}


def score_translation(
    episode: Episode,
    translation: dict,
    bible: dict,
    edits: dict | None = None,
) -> dict:
    beats = translation.get("beats") or {}
    model_beats = translation.get("model_beats") or beats
    expected = [beat for beat in episode.beats() if is_translatable(beat.kind) and beat.text.strip()]
    missing = [beat.id for beat in expected if not (beats.get(beat.id) or {}).get("text")]
    rendered = render_episode(episode, translation, edits=edits)
    time_lines = re.findall(r"(?m)^Start:\s+\(", rendered)
    source_time_lines = sum(1 for beat in episode.beats() if beat.start or beat.end)

    # Glossary accuracy
    glossary_hits = 0
    glossary_total = 0
    glossary_misses = []
    for term in bible.get("glossary") or []:
        source = term.get("source") or ""
        target = term.get("target") or ""
        if len(source) < 3 or not target or term.get("decision") == "keep":
            continue
        pattern = re.compile(re.escape(source), re.IGNORECASE)
        for beat in expected:
            if not pattern.search(beat.text):
                continue
            glossary_total += 1
            translated = (beats.get(beat.id) or {}).get("text") or ""
            if target.casefold() in translated.casefold():
                glossary_hits += 1
            elif len(glossary_misses) < 8:
                glossary_misses.append(
                    {
                        "episode": episode.number,
                        "beat_id": beat.id,
                        "source": beat.text,
                        "translation": translated,
                        "expected": target,
                        "term": source,
                    }
                )

    # Spoken name accuracy
    name_hits = 0
    name_total = 0
    name_misses = []
    for beat in expected:
        if beat.kind != "dialogue":
            continue
        character = character_for_cue(bible, beat.cue)
        spoken = (character or {}).get("spoken_name") or ""
        if not character or not spoken:
            continue
        mentioned = False
        for other in bible.get("characters") or []:
            if other["id"] == character["id"]:
                continue
            for form in other.get("surface_forms") or []:
                if form and re.search(rf"\b{re.escape(form)}\b", beat.text, re.IGNORECASE):
                    mentioned = True
                    spoken = other.get("spoken_name") or spoken
                    break
            if mentioned:
                break
        if not mentioned:
            for form in character.get("surface_forms") or []:
                if form and re.search(rf"\b{re.escape(form)}\b", beat.text, re.IGNORECASE):
                    mentioned = True
                    spoken = character.get("spoken_name") or spoken
                    break
        if not mentioned:
            continue
        name_total += 1
        translated = (beats.get(beat.id) or {}).get("text") or ""
        if spoken.casefold() in translated.casefold():
            name_hits += 1
        elif len(name_misses) < 8:
            name_misses.append(
                {
                    "episode": episode.number,
                    "beat_id": beat.id,
                    "source": beat.text,
                    "translation": translated,
                    "expected": spoken,
                }
            )

    # Cue variants: separate RAW MODEL performance from post-processed APPLIED cues
    model_variants = _cue_variants(episode, translation, bible)
    applied_variants = _applied_variants(episode, translation, bible)

    # Honest Raw Model Cue Consistency:
    # Measure how often the model itself chose the bible's canonical display_name
    dialogue_beats = [b for b in episode.beats() if b.kind == "dialogue"]
    model_canon_hits = 0
    for b in dialogue_beats:
        char = character_for_cue(bible, b.cue)
        canon_name = (char.get("display_name") if char else b.cue) or b.cue
        m_rec = model_beats.get(b.id) or {}
        raw_choice = (m_rec.get("model_display_name") or m_rec.get("display_name") or "").strip()
        if raw_choice.casefold() == canon_name.casefold():
            model_canon_hits += 1
    raw_cue_consistency_rate = _rate(model_canon_hits, len(dialogue_beats))

    # Real Evidence Metric: Reviewer Edit Rate
    # Formula: (characters changed / characters delivered)
    reviewer_edit_data: dict | None = None
    if edits:
        total_delivered_chars = 0
        total_changed_chars = 0
        per_beat_edits = {}
        for b in dialogue_beats:
            if b.id in edits:
                delivered_txt = (beats.get(b.id) or {}).get("text") or ""
                reviewed_txt = edits[b.id]
                dist = compute_levenshtein(delivered_txt, reviewed_txt)
                beat_rate = compute_edit_rate(delivered_txt, reviewed_txt)
                total_delivered_chars += len(delivered_txt)
                total_changed_chars += dist
                per_beat_edits[b.id] = {
                    "delivered": delivered_txt,
                    "reviewed": reviewed_txt,
                    "characters_changed": dist,
                    "characters_delivered": len(delivered_txt),
                    "edit_rate": beat_rate,
                }
        overall_edit_rate = round(total_changed_chars / max(1, total_delivered_chars), 4) if total_delivered_chars > 0 else 0.0
        reviewer_edit_data = {
            "total_characters_delivered": total_delivered_chars,
            "total_characters_changed": total_changed_chars,
            "overall_edit_rate": overall_edit_rate,
            "beats_edited_count": len(per_beat_edits),
            "per_beat_edits": per_beat_edits,
        }

    # Code-based validation & Honest Failures count
    honest_failures = [
        bid for bid, r in beats.items() if r.get("status") == "honest_failure" or r.get("validation_failed")
    ]

    return {
        "episode": episode.number,
        "mode": translation.get("mode"),
        "expected_beats": len(expected),
        "missing_beats": missing,
        "completeness": _rate(len(expected) - len(missing), len(expected)),
        "timestamp_lines_in_export": len(time_lines),
        "timestamp_lines_expected": source_time_lines,
        "timestamps_preserved": len(time_lines) == source_time_lines,
        "glossary_hits": glossary_hits,
        "glossary_opportunities": glossary_total,
        "glossary_rate": _rate(glossary_hits, glossary_total),
        "glossary_misses": glossary_misses,
        "spoken_name_hits": name_hits,
        "spoken_name_opportunities": name_total,
        "spoken_name_rate": _rate(name_hits, name_total),
        "spoken_name_misses": name_misses,
        "raw_cue_consistency_rate": raw_cue_consistency_rate,
        "model_cue_variants": model_variants,
        "applied_cue_variants": applied_variants,
        "model_characters_with_multiple_cues": {
            key: values for key, values in model_variants.items() if len(values) > 1
        },
        "applied_characters_with_multiple_cues": {
            key: values for key, values in applied_variants.items() if len(values) > 1
        },
        "honest_failures": honest_failures,
        "honest_failure_count": len(honest_failures),
        "reviewer_edit_metrics": reviewer_edit_data,
    }


def combine_scores(scores: list[dict]) -> dict:
    def total(key: str) -> int:
        return sum(int(item.get(key) or 0) for item in scores)

    expected = total("expected_beats")
    missing = sum(len(item.get("missing_beats") or []) for item in scores)
    glossary_hits = total("glossary_hits")
    glossary_total = total("glossary_opportunities")
    name_hits = total("spoken_name_hits")
    name_total = total("spoken_name_opportunities")
    honest_fails = total("honest_failure_count")

    multi_model: dict[str, list[str]] = {}
    multi_applied: dict[str, list[str]] = {}
    for item in scores:
        for key, values in (item.get("model_characters_with_multiple_cues") or {}).items():
            multi_model.setdefault(key, [])
            for value in values:
                if value not in multi_model[key]:
                    multi_model[key].append(value)
        for key, values in (item.get("applied_characters_with_multiple_cues") or {}).items():
            multi_applied.setdefault(key, [])
            for value in values:
                if value not in multi_applied[key]:
                    multi_applied[key].append(value)

    # Aggregate reviewer edit rates if available
    edit_metrics_list = [s.get("reviewer_edit_metrics") for s in scores if s.get("reviewer_edit_metrics")]
    combined_edit_metrics = None
    if edit_metrics_list:
        sum_delivered = sum(m["total_characters_delivered"] for m in edit_metrics_list)
        sum_changed = sum(m["total_characters_changed"] for m in edit_metrics_list)
        combined_edit_metrics = {
            "total_characters_delivered": sum_delivered,
            "total_characters_changed": sum_changed,
            "overall_edit_rate": round(sum_changed / max(1, sum_delivered), 4) if sum_delivered > 0 else 0.0,
            "episodes_with_edits": len(edit_metrics_list),
        }

    raw_rates = [s["raw_cue_consistency_rate"] for s in scores if s.get("raw_cue_consistency_rate") is not None]
    avg_raw_cue_rate = round(sum(raw_rates) / len(raw_rates), 3) if raw_rates else None

    return {
        "completeness": _rate(expected - missing, expected),
        "missing_beat_count": missing,
        "expected_beats": expected,
        "timestamps_preserved": all(item.get("timestamps_preserved") for item in scores) if scores else True,
        "glossary_rate": _rate(glossary_hits, glossary_total),
        "glossary_hits": glossary_hits,
        "glossary_opportunities": glossary_total,
        "spoken_name_rate": _rate(name_hits, name_total),
        "spoken_name_hits": name_hits,
        "spoken_name_opportunities": name_total,
        "raw_cue_consistency_rate": avg_raw_cue_rate,
        "model_characters_with_multiple_cues": multi_model,
        "applied_characters_with_multiple_cues": multi_applied,
        "honest_failure_count": honest_fails,
        "reviewer_edit_metrics": combined_edit_metrics,
    }
