from __future__ import annotations

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
