from __future__ import annotations

import argparse
import json
from pathlib import Path

from kuku_localise.bible import build_bible
from kuku_localise.export import render_dialogue_only, render_episode
from kuku_localise.index import build_index, choose_episodes
from kuku_localise.llm import get_client
from kuku_localise.parse import parse_folder
from kuku_localise.qa import combine_scores, score_translation
from kuku_localise.summary import build_series_summary
from kuku_localise.translate import translate_episode
from kuku_localise.validation import compute_edit_rate, compute_levenshtein


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    scripts = Path(args.scripts).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else Path("outputs").resolve()
    raw = output / "raw"
    cache_dir = output / "cache"
    reviewed_dir = output / "reviewed"
    no_baseline = getattr(args, "no_baseline", False)

    episodes, skipped = parse_folder(scripts)
    if not episodes:
        raise SystemExit("No usable screenplay files found. Expected .txt files with SCENE blocks.")

    available_numbers = [episode.number for episode in episodes]
    if args.episodes and str(args.episodes).strip().lower() in {"all", "*"}:
        selected_numbers = sorted(set(available_numbers))
    elif args.episodes:
        requested = [int(v.strip()) for v in str(args.episodes).split(",") if v.strip()]
        selected_numbers = choose_episodes(available_numbers, requested)
    else:
        selected_numbers = choose_episodes(available_numbers, None)

    selected = [episode for episode in episodes if episode.number in selected_numbers]
    index = build_index(episodes, args.lang)

    _write_json(
        raw / "ingest.json",
        {
            "source": str(scripts),
            "episodes_found": len(episodes),
            "skipped": skipped,
            "warnings": {str(e.number): e.warnings for e in episodes if e.warnings},
        },
    )
    _write_json(raw / "series_index.json", index)
    _write_json(raw / "episodes.json", {"episodes": [episode.to_dict() for episode in episodes]})

    # Swappable LLM client via factory function
    client = get_client(
        provider=getattr(args, "provider", None),
        model=getattr(args, "model", None),
        cache_dir=cache_dir,
    )

    bible_path = raw / "story_bible.json"
    bible = (
        json.loads(bible_path.read_text(encoding="utf-8"))
        if bible_path.exists()
        else build_bible(client, index, scripts.name, args.lang)
    )
    _write_json(bible_path, bible)
    _write_json(raw / "series_summary.json", build_series_summary(client, index, bible))

    independent_scores, series_scores, report_episodes = [], [], []
    by_number = {episode.number: episode for episode in episodes}

    for episode in selected:
        prior = by_number.get(episode.number - 1)
        previous_logline = prior.logline if prior else ""

        # Check for reviewer edits
        edits_path = reviewed_dir / f"episode-{episode.number:03d}.edits.json"
        reviewer_edits = json.loads(edits_path.read_text(encoding="utf-8")) if edits_path.exists() else None

        # 1. Series Translation (Contextual)
        series = translate_episode(client, episode, bible, args.lang, "series", previous_logline)
        series_path = raw / f"episode-{episode.number:03d}.series.json"
        _write_json(series_path, series)
        (raw / f"episode-{episode.number:03d}.series.txt").write_text(
            render_episode(episode, series, edits=reviewer_edits), encoding="utf-8"
        )
        source_text = (scripts / episode.source_file).read_text(encoding="utf-8")
        (raw / f"episode-{episode.number:03d}.dialogue-only.{args.lang}.txt").write_text(
            render_dialogue_only(source_text, episode, series), encoding="utf-8"
        )
        series_score = score_translation(episode, series, bible, edits=reviewer_edits)
        series_scores.append(series_score)

        # 2. Independent Translation (Baseline) - skipped if --no-baseline is active
        independent_score = None
        if not no_baseline:
            independent = translate_episode(client, episode, bible, args.lang, "independent", previous_logline)
            independent_path = raw / f"episode-{episode.number:03d}.independent.json"
            _write_json(independent_path, independent)
            (raw / f"episode-{episode.number:03d}.independent.txt").write_text(
                render_episode(episode, independent), encoding="utf-8"
            )
            independent_score = score_translation(episode, independent, bible, edits=reviewer_edits)
            independent_scores.append(independent_score)

        # Comparative ROI Calculation if reviewer edits exist
        roi_comparison = None
        if reviewer_edits and independent_score:
            s_edit = series_score.get("reviewer_edit_metrics") or {}
            i_edit = independent_score.get("reviewer_edit_metrics") or {}
            s_rate = s_edit.get("overall_edit_rate", 0.0)
            i_rate = i_edit.get("overall_edit_rate", 0.0)
            effort_saved_pct = round(((i_rate - s_rate) / max(0.001, i_rate)) * 100, 1) if i_rate > 0 else 0.0
            roi_comparison = {
                "series_edit_rate": s_rate,
                "independent_edit_rate": i_rate,
                "reviewer_effort_saved_percent": effort_saved_pct,
            }

        report_episodes.append(
            {
                "episode": episode.number,
                "series": series_score,
                "independent": independent_score,
                "roi_comparison": roi_comparison,
            }
        )

    # Read usage statistics
    usage_file = cache_dir / "usage.json"
    usage_info = json.loads(usage_file.read_text(encoding="utf-8")) if usage_file.exists() else {}

    report = {
        "language": args.lang,
        "episodes_checked": selected_numbers,
        "baseline_skipped": no_baseline,
        "series": combine_scores(series_scores),
        "independent": combine_scores(independent_scores) if not no_baseline else None,
        "episodes": report_episodes,
        "usage": usage_info,
        "note": "Structural checks evaluate consistency; Reviewer Edit Rate measures real-world editing reduction and studio ROI.",
    }
    _write_json(raw / "comparison.json", report)

    print(f"Localised and checked episodes: {', '.join(map(str, selected_numbers))}.")
    print(f"Output directory: {raw}")
    print(f"Baseline run skipped (--no-baseline): {no_baseline}")
    print(f"Model: {client.model} | API calls made this run: {client.calls} (Cache hits: {client.cached_hits})")
    if usage_info:
        print(f"Token accounting: {usage_info.get('total_tokens', 0):,} total tokens (~${usage_info.get('estimated_cost_usd', 0.0):.4f} USD estimated cost).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Series-aware microdrama localisation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("run", help="build a bible and compare independent vs series translations")
    command.add_argument("--scripts", required=True, help="folder containing .txt screenplay episodes")
    command.add_argument("--lang", required=True, help="target language name, for example hi, ta, or es")
    command.add_argument("--episodes", help="comma-separated episode numbers (or 'all'); default is 1, 2, and 10 or the last episode")
    command.add_argument("--output", help="output directory (default: ./outputs)")
    command.add_argument("--model", help="Model ID (default: KUKU_MODEL or built-in default)")
    command.add_argument("--provider", help="LLM Provider: gemini, mock (default: LLM_PROVIDER or gemini)")
    command.add_argument("--no-baseline", action="store_true", help="Skip baseline independent run to reduce API cost by 50%%")
    command.set_defaults(func=run)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
