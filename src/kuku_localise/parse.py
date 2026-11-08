from __future__ import annotations

import re
from pathlib import Path

from kuku_localise.models import Beat, Episode, Scene, parse_timestamp_seconds

DIRECTION = {
    "CAMERA": "camera",
    "ACTION": "action",
    "SOUND FX": "sound",
    "SOUND": "sound",
    "SFX": "sound",
    "MUSIC": "music",
    "TITLE": "direction",
    "TITLE CARD": "direction",
    "SUPER": "direction",
    "TRANSITION": "direction",
    "INSERT": "direction",
    "CUT": "direction",
    "FADE IN": "direction",
    "FADE OUT": "direction",
    "GRAPHICS": "direction",
    "CHYRON": "direction",
}

TRANSLATABLE = {"dialogue", "action", "sound", "music"}

BEAT_HEAD = re.compile(r"^\*\*(.+?):\*\*\s*$")
TIME_LINE = re.compile(
    r"^Start:\s*\(?([^)|]+?)\)?\s*\|\s*End:\s*\(?([^)|]+?)\)?\s*$",
    re.IGNORECASE,
)
SCENE_LINE = re.compile(r"^SCENE\s+(\d+)\s*$", re.IGNORECASE)
FIELD_LINE = re.compile(
    r"^(EPISODE NUMBER|EPISODE LOGLINE|CONTINUITY NOTES):\s*(.*)$",
    re.IGNORECASE,
)
HEADING_LINE = re.compile(r"^Scene heading:\s*(.*)$", re.IGNORECASE)
SCENE_START = re.compile(r"^Scene start:\s*(.*)$", re.IGNORECASE)
SCENE_END = re.compile(r"^Scene end:\s*(.*)$", re.IGNORECASE)
SCRIPT_MARK = re.compile(r"^-{3,}.*-{3,}\s*$")
FILENAME_EPISODE = re.compile(r"episode[-_\s]*(\d+)", re.IGNORECASE)

KNOWN_MODIFIERS = {
    "OFF-SCREEN",
    "OFF SCREEN",
    "OFFSCREEN",
    "O.S.",
    "O.S",
    "OS",
    "V.O.",
    "V.O",
    "VO",
    "VOICEOVER",
    "VOICE-OVER",
    "VOICE OVER",
    "OVER SCREEN",
    "CONT'D",
    "CONTD",
    "CONTINUED",
    "FILTERED",
    "ON PHONE",
    "INTO PHONE",
    "SUBTITLE",
    "PRE-LAP",
}


def is_translatable(kind: str) -> bool:
    return kind in TRANSLATABLE


def _split_cue(label: str) -> tuple[str, str, str, list[str]]:
    """Recursively strip trailing parentheticals, separating audio/camera modifiers from acting notes."""
    raw = label.strip()
    raw_parentheticals: list[str] = []

    # Strip all trailing parentheticals recursively/globally
    while True:
        match = re.search(r"\s*\(([^)]*)\)\s*$", raw)
        if match:
            raw_parentheticals.insert(0, match.group(1).strip())
            raw = raw[: match.start()].strip()
        else:
            break

    name = raw.strip()
    modifiers: list[str] = []
    notes: list[str] = []

    for paren in raw_parentheticals:
        cleaned_tag = paren.strip()
        norm_tag = re.sub(r"[^\w\s'-]", "", cleaned_tag).upper().strip()
        if cleaned_tag.upper() in KNOWN_MODIFIERS or norm_tag in KNOWN_MODIFIERS:
            modifiers.append(cleaned_tag)
        else:
            notes.append(cleaned_tag)

    kind = DIRECTION.get(name.upper(), "dialogue")
    parenthetical = ", ".join(notes)
    return kind, name, parenthetical, modifiers


def _episode_number_from_name(name: str) -> int | None:
    match = FILENAME_EPISODE.search(name)
    if match:
        return int(match.group(1))
    digits = re.search(r"(\d+)", name)
    return int(digits.group(1)) if digits else None


def _episode_number_from_header(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def parse_episode_text(text: str, source_name: str) -> Episode | None:
    lines = text.lstrip("\ufeff").splitlines()
    fields = {"EPISODE NUMBER": "", "EPISODE LOGLINE": "", "CONTINUITY NOTES": ""}
    active_field: str | None = None
    scenes: list[Scene] = []
    scene: Scene | None = None
    beat: dict | None = None
    beat_index = 0
    warnings: list[str] = []

    def flush_beat() -> None:
        nonlocal beat, beat_index
        if beat is None or scene is None:
            beat = None
            return
        beat_index += 1
        body = "\n".join(line.strip() for line in beat["lines"] if line.strip()).strip()

        # Explicitly calculate duration in seconds
        start_sec = parse_timestamp_seconds(beat["start"])
        end_sec = parse_timestamp_seconds(beat["end"])
        duration = 0.0
        if start_sec is not None and end_sec is not None:
            duration = max(0.0, round(end_sec - start_sec, 2))

        scene.beats.append(
            Beat(
                id="",
                kind=beat["kind"],
                cue=beat["cue"],
                parenthetical=beat["parenthetical"],
                start=beat["start"],
                end=beat["end"],
                text=body,
                duration=duration,
                modifiers=beat.get("modifiers") or [],
            )
        )
        if not beat["start"] or not beat["end"]:
            warnings.append(f"Scene {scene.number} beat {beat_index} has no timestamp")
        beat = None

    for raw in lines:
        line = raw.strip()
        if scene is None:
            field_match = FIELD_LINE.match(line)
            if field_match:
                active_field = field_match.group(1).upper()
                fields[active_field] = field_match.group(2).strip()
                continue
            if line and active_field and not SCENE_LINE.match(line) and not SCRIPT_MARK.match(line):
                fields[active_field] = (fields[active_field] + " " + line).strip()
                continue
        scene_match = SCENE_LINE.match(line)
        if scene_match:
            flush_beat()
            scene = Scene(number=int(scene_match.group(1)), heading="", start="", end="")
            scenes.append(scene)
            beat_index = 0
            active_field = None
            continue
        if scene is None or not line or line.lower() == "actions and dialogue:":
            continue
        if SCRIPT_MARK.match(line):
            flush_beat()
            continue
        heading = HEADING_LINE.match(line)
        if heading and beat is None:
            scene.heading = heading.group(1).strip()
            continue
        start_match = SCENE_START.match(line)
        if start_match and beat is None:
            scene.start = start_match.group(1).strip()
            continue
        end_match = SCENE_END.match(line)
        if end_match and beat is None:
            scene.end = end_match.group(1).strip()
            continue
        head = BEAT_HEAD.match(line)
        if head:
            flush_beat()
            kind, cue, note, modifiers = _split_cue(head.group(1))
            beat = {
                "kind": kind,
                "cue": cue,
                "parenthetical": note,
                "modifiers": modifiers,
                "start": "",
                "end": "",
                "lines": [],
            }
            continue
        if beat is None:
            continue
        timing = TIME_LINE.match(line)
        if timing and not beat["start"]:
            beat["start"] = timing.group(1).strip()
            beat["end"] = timing.group(2).strip()
            continue
        beat["lines"].append(line)

    flush_beat()
    if not scenes:
        return None

    number = _episode_number_from_header(fields["EPISODE NUMBER"])
    if number is None:
        number = _episode_number_from_name(source_name)
    if number is None:
        number = 0
        warnings.append("Episode number missing; filename had no number either")

    episode = Episode(
        number=number,
        logline=fields["EPISODE LOGLINE"],
        continuity=fields["CONTINUITY NOTES"],
        source_file=source_name,
        scenes=scenes,
        warnings=warnings,
    )
    for scene_index, parsed_scene in enumerate(episode.scenes, start=1):
        for index, parsed_beat in enumerate(parsed_scene.beats, start=1):
            parsed_beat.id = f"e{episode.number:02d}-s{scene_index:02d}-b{index:03d}"
    return episode


def parse_folder(path: Path) -> tuple[list[Episode], list[dict]]:
    folder = Path(path)
    if not folder.is_dir():
        raise FileNotFoundError(f"Screenplay folder not found: {folder}")
    files = sorted(item for item in folder.iterdir() if item.is_file() and item.suffix.lower() == ".txt")
    episodes: list[Episode] = []
    skipped: list[dict] = []
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file.read_text(encoding="utf-8", errors="replace")
        episode = parse_episode_text(text, file.name)
        if episode is None:
            skipped.append({"file": file.name, "reason": "no SCENE blocks found"})
            continue
        episodes.append(episode)
    episodes.sort(key=lambda episode: (episode.number, episode.source_file.lower()))
    seen: dict[int, str] = {}
    for episode in episodes:
        if episode.number in seen:
            episode.warnings.append(
                f"Duplicate episode number {episode.number}; also used by {seen[episode.number]}"
            )
        else:
            seen[episode.number] = episode.source_file
    return episodes, skipped
