from pathlib import Path

from kuku_localise.index import choose_episodes
from kuku_localise.parse import parse_episode_text, parse_folder
from kuku_localise.export import render_dialogue_only


def test_parser_assigns_stable_beat_ids_and_keeps_timestamps():
    text = (Path(__file__).parent / "fixtures" / "episode-07.txt").read_text(encoding="utf-8")
    episode = parse_episode_text(text, "episode-07.txt")
    assert episode is not None
    assert episode.number == 7
    assert [beat.id for beat in episode.beats()] == ["e07-s01-b001", "e07-s01-b002"]
    assert episode.beats()[0].parenthetical == "breathless"
    assert episode.beats()[0].duration == 3.0
    assert episode.beats()[1].kind == "action"
    assert episode.beats()[1].end == "00:07"
    assert episode.beats()[1].duration == 3.0


def test_parser_strips_nested_parentheticals_and_extracts_modifiers_and_duration():
    source = chr(10).join([
        "SCENE 1",
        "**LADY JULIANA (Off-screen) (Dismissive):**",
        "Start: (00:03) | End: (00:07)",
        "Tell him I am not home.",
        "",
        "**MIRA (O.S.) (CONT'D):**",
        "Start: (00:08) | End: (00:10)",
        "Yes, my lady.",
        "",
    ])
    episode = parse_episode_text(source, "episode-01.txt")
    assert episode is not None
    beats = episode.beats()
    assert len(beats) == 2

    beat1 = beats[0]
    assert beat1.cue == "LADY JULIANA"
    assert beat1.parenthetical == "Dismissive"
    assert beat1.modifiers == ["Off-screen"]
    assert beat1.duration == 4.0

    beat2 = beats[1]
    assert beat2.cue == "MIRA"
    assert beat2.parenthetical == ""
    assert beat2.modifiers == ["O.S.", "CONT'D"]
    assert beat2.duration == 2.0


def test_sample_show_parses_and_default_selection_is_stable():
    root = Path(__file__).parents[1] / "examples" / "sample-show"
    episodes, skipped = parse_folder(root)
    assert skipped == []
    assert [episode.number for episode in episodes] == [1, 2]
    assert choose_episodes([1, 2]) == [1, 2]


def test_dialogue_only_export_preserves_directions_and_timestamps():
    source = chr(10).join(["SCENE 1", "**ACTION:**", "Start: (00:00) | End: (00:02)", "She enters.", "", "**MIRA:**", "Start: (00:03) | End: (00:05)", "Hello.", ""])
    episode = parse_episode_text(source, "episode-01.txt")
    assert episode is not None
    dialogue_id = episode.beats()[1].id
    rendered = render_dialogue_only(source, episode, {"beats": {dialogue_id: {"text": "नमस्ते।"}}})
    assert "She enters." in rendered
    assert "Start: (00:03) | End: (00:05)" in rendered
    assert "नमस्ते।" in rendered
    assert "Hello." not in rendered
