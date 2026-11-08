from __future__ import annotations

import re
from collections import Counter

from kuku_localise.models import Episode
from kuku_localise.parse import is_translatable

HONORIFICS = {
    "lady",
    "lord",
    "sir",
    "dame",
    "mr",
    "mrs",
    "miss",
    "ms",
    "dr",
    "doctor",
    "the",
}


def significant_tokens(cue: str) -> set[str]:
    name = re.sub(r"\s*\([^)]*\)\s*$", "", cue)
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]+", name)
    return {token.lower() for token in tokens if token.lower() not in HONORIFICS and len(token) > 2}


def alias_groups(cues: list[str]) -> list[list[str]]:
    parent = {cue: cue for cue in cues}

    def find(cue: str) -> str:
        while parent[cue] != cue:
            parent[cue] = parent[parent[cue]]
            cue = parent[cue]
        return cue

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    token_owner: dict[str, str] = {}
    for cue in cues:
        for token in significant_tokens(cue):
            if token in token_owner:
                union(cue, token_owner[token])
            else:
                token_owner[token] = cue
    grouped: dict[str, list[str]] = {}
    for cue in cues:
        grouped.setdefault(find(cue), []).append(cue)
    return [sorted(members) for members in grouped.values() if len(members) > 1]


def choose_episodes(numbers: list[int], requested: list[int] | None = None) -> list[int]:
    available = sorted(set(numbers))
    if requested:
        missing = [number for number in requested if number not in available]
        if missing:
            raise ValueError(f"Episodes not in this folder: {missing}")
        return requested
    if not available:
        return []
    chosen: list[int] = []
    for number in (1, 2):
        if number in available:
            chosen.append(number)
    for number in available:
        if len(chosen) >= 2:
            break
        if number not in chosen:
            chosen.append(number)
    later = 10 if 10 in available else available[-1]
    if later not in chosen:
        chosen.append(later)
    return chosen


def build_index(episodes: list[Episode], target_language: str) -> dict:
    speakers: dict[str, dict] = {}
    for episode in episodes:
        for beat in episode.beats():
            if beat.kind != "dialogue":
                continue
            slot = speakers.setdefault(
                beat.cue,
                {"cue": beat.cue, "line_count": 0, "parentheticals": Counter(), "samples": []},
            )
            slot["line_count"] += 1
            if beat.parenthetical:
                slot["parentheticals"][beat.parenthetical] += 1
            if len(slot["samples"]) < 3 and beat.text:
                slot["samples"].append(beat.text[:160])
    speaker_rows = []
    for slot in sorted(speakers.values(), key=lambda item: (-item["line_count"], item["cue"])):
        speaker_rows.append(
            {
                "cue": slot["cue"],
                "line_count": slot["line_count"],
                "parentheticals": [note for note, _count in slot["parentheticals"].most_common(6)],
                "samples": slot["samples"],
            }
        )
    return {
        "target_language": target_language,
        "episode_count": len(episodes),
        "episodes": [
            {
                "number": episode.number,
                "logline": episode.logline,
                "continuity": episode.continuity,
                "translatable_beats": sum(1 for beat in episode.beats() if is_translatable(beat.kind)),
            }
            for episode in episodes
        ],
        "speakers": speaker_rows[:80],
        "possible_alias_groups": alias_groups(list(speakers))[:40],
    }
