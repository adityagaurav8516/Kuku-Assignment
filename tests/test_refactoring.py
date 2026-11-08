from pathlib import Path

from kuku_localise.bible import detect_flagged_merges
from kuku_localise.llm import MockLLMClient, estimate_cost_usd, get_client
from kuku_localise.models import Beat, Episode, Scene
from kuku_localise.qa import score_translation
from kuku_localise.validation import (
    compute_edit_rate,
    compute_levenshtein,
    validate_beat,
    validate_register,
    validate_subtitle_fit,
    validate_timing,
)


def test_validation_timing_cps():
    # 30 chars in 1.0 second = 30 CPS (> 18.0)
    ok, err = validate_timing("यह एक बहुत ही लंबा वाक्य है जो समय में नहीं आएगा", duration=1.0)
    assert not ok
    assert "Timing failed" in err

    # 10 chars in 2.0 seconds = 5 CPS (<= 18.0)
    ok, err = validate_timing("नमस्ते सर", duration=2.0)
    assert ok
    assert err is None


def test_validation_address_register():
    # When formal 'aap' is required, informal 'tu/tum' must fail
    ok, err = validate_register("तू यहाँ क्या कर रहा है?", expected_register="aap", target_lang="Hindi")
    assert not ok
    assert "Address consistency failed" in err

    # Formal 'aap' passes
    ok, err = validate_register("आप यहाँ क्या कर रहे हैं?", expected_register="aap", target_lang="Hindi")
    assert ok
    assert err is None

    # When 'tu' is expected, 'aap' must fail
    ok, err = validate_register("आप जाइए", expected_register="tu", target_lang="Hindi")
    assert not ok
    assert "Address consistency failed" in err


def test_validation_subtitle_fit():
    # Long line > 44 chars
    long_line = "यह वाक्य बहुत ही ज्यादा लंबा है और फोन की स्क्रीन से बाहर निकल जाएगा निश्चित रूप से।"
    ok, err = validate_subtitle_fit(long_line)
    assert not ok
    assert "Subtitle fit failed" in err

    # Normal line passes
    ok, err = validate_subtitle_fit("नमस्ते मीरा, तुम कैसी हो?")
    assert ok


def test_reviewer_edit_rate_and_levenshtein():
    delivered = "नमस्ते"
    edited = "नमस्ते जी"
    dist = compute_levenshtein(delivered, edited)
    assert dist == 3
    rate = compute_edit_rate(delivered, edited)
    assert rate == round(3 / 6, 4)


def test_detect_flagged_merges():
    index = {"possible_alias_groups": [["LADY JULIANA", "JULIANA"]]}
    characters = [
        {
            "id": "matriarch",
            "display_name": "Matriarch",
            "surface_forms": ["Matriarch", "OFF-SCREEN VOICE"],
        },
        {
            "id": "lady-juliana",
            "display_name": "LADY JULIANA",
            "surface_forms": ["LADY JULIANA", "JULIANA"],
        },
    ]
    flagged = detect_flagged_merges(index, characters)
    assert len(flagged) == 1
    assert flagged[0]["display_name"] == "Matriarch"
    assert flagged[0]["surface_form"] == "OFF-SCREEN VOICE"
    assert characters[0]["needs_review"] is True
    assert characters[1]["needs_review"] is False


def test_swappable_llm_client_and_usage(tmp_path: Path):
    client = get_client(provider="mock", cache_dir=tmp_path)
    assert isinstance(client, MockLLMClient)
    assert client.provider == "mock"

    res = client.complete_json("system", "user")
    assert "beats" in res
    assert client.calls == 1

    usage_file = tmp_path / "usage.json"
    assert usage_file.exists()


def test_cost_estimation():
    # 100k input, 20k output on flash
    cost = estimate_cost_usd("gemini-2.5-flash", 100_000, 20_000)
    # (100k/1M)*0.075 + (20k/1M)*0.30 = 0.0075 + 0.006 = 0.0135
    assert cost == 0.0135


def test_honesty_of_measurement_in_qa():
    # Create an episode with 2 dialogue beats
    ep = Episode(
        number=1,
        logline="Test",
        continuity="None",
        source_file="ep1.txt",
        scenes=[
            Scene(
                number=1,
                heading="EXT. CASTLE - DAY",
                start="00:00",
                end="00:10",
                beats=[
                    Beat(id="e01-s01-b001", kind="dialogue", cue="LADY JULIANA", parenthetical="", start="00:00", end="00:03", text="Enter.", duration=3.0),
                    Beat(id="e01-s01-b002", kind="dialogue", cue="JULIANA", parenthetical="", start="00:04", end="00:07", text="Leave.", duration=3.0),
                ],
            )
        ],
    )
    bible = {
        "characters": [
            {
                "id": "juliana",
                "display_name": "LADY JULIANA",
                "spoken_name": "Juliana",
                "surface_forms": ["LADY JULIANA", "JULIANA"],
            }
        ]
    }
    # Raw model emitted two different cues: "LADY JULIANA" and "JULIANA"
    # Even if deliverable beats has applied canonical name, raw_cue_consistency_rate evaluates model_display_name
    translation = {
        "mode": "series",
        "beats": {
            "e01-s01-b001": {"text": "अंदर आओ।", "display_name": "LADY JULIANA", "model_display_name": "LADY JULIANA"},
            "e01-s01-b002": {"text": "जाओ।", "display_name": "LADY JULIANA", "model_display_name": "JULIANA"},
        },
        "model_beats": {
            "e01-s01-b001": {"text": "अंदर आओ।", "display_name": "LADY JULIANA", "model_display_name": "LADY JULIANA"},
            "e01-s01-b002": {"text": "जाओ।", "display_name": "JULIANA", "model_display_name": "JULIANA"},
        },
    }
    edits = {
        "e01-s01-b001": "कृपया अंदर आओ।",  # Reviewer edited
    }
    score = score_translation(ep, translation, bible, edits=edits)

    # Raw model cue variants must reveal the fragmentation
    assert "juliana" in score["model_characters_with_multiple_cues"]
    assert score["model_characters_with_multiple_cues"]["juliana"] == ["JULIANA", "LADY JULIANA"]
    # But applied deliverable is normalized
    assert "juliana" not in score["applied_characters_with_multiple_cues"]

    # Reviewer edit metrics
    assert score["reviewer_edit_metrics"] is not None
    assert score["reviewer_edit_metrics"]["total_characters_delivered"] == len("अंदर आओ।")
    assert score["reviewer_edit_metrics"]["overall_edit_rate"] > 0
