from __future__ import annotations

import re

from kuku_localise.models import Episode
from kuku_localise.parse import is_translatable

KIND_CUE = {
    "camera": "CAMERA",
    "action": "ACTION",
    "sound": "SOUND FX",
    "music": "MUSIC",
    "direction": "DIRECTION",
}


def render_episode(episode: Episode, translation: dict | None = None, edits: dict | None = None) -> str:
    translation = translation or {}
    beats = translation.get("beats") or {}
    headings = translation.get("headings") or {}
    edits = edits or {}
    lines = [
        f"EPISODE NUMBER: Episode {episode.number}",
        f"EPISODE LOGLINE: {episode.logline}",
        f"CONTINUITY NOTES: {episode.continuity}",
        "",
        "--- SCRIPT START ---",
        "",
    ]
    for scene in episode.scenes:
        lines.append(f"SCENE {scene.number:02d}")
        heading = headings.get(str(scene.number)) or scene.heading
        if heading:
            lines.append(f"Scene heading: {heading}")
        if scene.start:
            lines.append(f"Scene start: {scene.start}")
        if scene.end:
            lines.append(f"Scene end: {scene.end}")
        lines.append("")
        for beat in scene.beats:
            record = beats.get(beat.id) or {}
            if beat.id in edits:
                text = edits[beat.id]
            elif record.get("text"):
                text = record["text"]
            elif is_translatable(beat.kind):
                text = "[MISSING]" if beat.text else ""
            else:
                text = beat.text
            if beat.id in beats:
                parenthetical = record.get("parenthetical") or ""
            else:
                parenthetical = beat.parenthetical
            if beat.kind == "dialogue":
                cue = record.get("display_name") or beat.cue
            else:
                cue = KIND_CUE.get(beat.kind, beat.cue or beat.kind.upper())
            if parenthetical:
                lines.append(f"**{cue} ({parenthetical}):**")
            else:
                lines.append(f"**{cue}:**")
            if beat.start or beat.end:
                lines.append(f"Start: ({beat.start}) | End: ({beat.end})")
            if text:
                lines.append(text)
            lines.append("")
    lines.append("--- SCRIPT END ---")
    lines.append("")
    return "\n".join(lines)


_CUE = re.compile(r"^\s*\*\*.+?:\*\*\s*$")
_TIME = re.compile(r"^\s*Start:\s*\(")


def render_dialogue_only(source_text: str, episode: Episode, translation: dict) -> str:
    """Keep the uploaded screenplay byte-for-line structure, replacing dialogue bodies only."""
    newline = "\r\n" if "\r\n" in source_text else "\n"
    lines = source_text.splitlines()
    source_beats = episode.beats()
    translated = translation.get("beats") or {}
    cursor = 0
    output: list[str] = []
    index = 0
    while index < len(lines):
        output.append(lines[index])
        if not _CUE.match(lines[index]) or cursor >= len(source_beats):
            index += 1
            continue
        beat = source_beats[cursor]
        # The next parsed dialogue cue owns the next timing/body section. If the
        # source diverges, leave it untouched rather than risking a wrong edit.
        lookahead = index + 1
        while lookahead < len(lines) and not _TIME.match(lines[lookahead]) and not _CUE.match(lines[lookahead]):
            output.append(lines[lookahead])
            lookahead += 1
        if lookahead >= len(lines) or not _TIME.match(lines[lookahead]):
            index += 1
            continue
        output.append(lines[lookahead])
        replacement = (translated.get(beat.id) or {}).get("text") if beat.kind == "dialogue" else ""
        body_start = lookahead + 1
        body_end = body_start
        while body_end < len(lines) and lines[body_end].strip() and not _CUE.match(lines[body_end]):
            body_end += 1
        if replacement:
            output.extend(replacement.splitlines())
        else:
            output.extend(lines[body_start:body_end])
        cursor += 1
        index = body_end
    return newline.join(output) + (newline if source_text.endswith(("\n", "\r")) else "")
