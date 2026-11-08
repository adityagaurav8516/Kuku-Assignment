from __future__ import annotations

import argparse
import json
from pathlib import Path

from kuku_localise.bible import build_bible
from kuku_localise.export import render_episode
from kuku_localise.index import build_index, choose_episodes
from kuku_localise.llm import GeminiClient
from kuku_localise.parse import parse_folder
from kuku_localise.qa import combine_scores, score_translation
from kuku_localise.translate import translate_episode


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    scripts = Path(args.scripts).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else Path("outputs").resolve()
    raw = output / "raw"
    episodes, skipped = parse_folder(scripts)
    if not episodes:
        raise SystemExit("No usable screenplay files found. Expected .txt files with SCENE blocks.")
    requested = [int(value) for value in args.episodes.split(",") if value.strip()] if args.episodes else None
    selected_numbers = choose_episodes([episode.number for episode in episodes], requested)
    selected = [episode for episode in episodes if episode.number in selected_numbers]
    index = build_index(episodes, args.lang)
    _write_json(raw / "ingest.json", {"source": str(scripts), "episodes_found": len(episodes), "skipped": skipped, "warnings": {str(e.number): e.warnings for e in episodes if e.warnings}})
    _write_json(raw / "series_index.json", index)
    _write_json(raw / "episodes.json", {"episodes": [episode.to_dict() for episode in episodes]})

    client = GeminiClient(output / "cache", model=args.model)
    bible = build_bible(client, index, scripts.name, args.lang)
    _write_json(raw / "story_bible.json", bible)

    independent_scores, series_scores, report_episodes = [], [], []
    by_number = {episode.number: episode for episode in episodes}
    for episode in selected:
        prior = by_number.get(episode.number - 1)
        previous_logline = prior.logline if prior else ""
        independent = translate_episode(client, episode, bible, args.lang, "independent", previous_logline)
        series = translate_episode(client, episode, bible, args.lang, "series", previous_logline)
        independent_path = raw / f"episode-{episode.number:03d}.independent.json"
        series_path = raw / f"episode-{episode.number:03d}.series.json"
        _write_json(independent_path, independent)
        _write_json(series_path, series)
        (raw / f"episode-{episode.number:03d}.independent.txt").write_text(render_episode(episode, independent), encoding="utf-8")
        (raw / f"episode-{episode.number:03d}.series.txt").write_text(render_episode(episode, series), encoding="utf-8")
        independent_score = score_translation(episode, independent, bible)
        series_score = score_translation(episode, series, bible)
        independent_scores.append(independent_score)
        series_scores.append(series_score)
        report_episodes.append({"episode": episode.number, "independent": independent_score, "series": series_score})
    report = {
        "language": args.lang,
        "episodes_checked": selected_numbers,
        "independent": combine_scores(independent_scores),
        "series": combine_scores(series_scores),
        "episodes": report_episodes,
        "note": "These are structural consistency checks. They do not measure naturalness or cultural suitability; review the paired scripts before approval.",
    }
    _write_json(raw / "comparison.json", report)
    print(f"Built story bible and compared episodes {', '.join(map(str, selected_numbers))}.")
    print(f"Raw review package: {raw}")
    print(f"Gemini requests made this run: {client.calls} (cache hits are not counted).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Series-aware microdrama localisation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("run", help="build a bible and compare independent vs series translations")
    command.add_argument("--scripts", required=True, help="folder containing .txt screenplay episodes")
    command.add_argument("--lang", required=True, help="target language name, for example hi, ta, or es")
    command.add_argument("--episodes", help="comma-separated episode numbers; default is 1, 2, and 10 or the last episode")
    command.add_argument("--output", help="output directory (default: ./outputs)")
    command.add_argument("--model", help="Gemini model ID (default: KUKU_MODEL or built-in default)")
    command.set_defaults(func=run)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
