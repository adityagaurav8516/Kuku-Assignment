# Kuku Localise

Kuku Localise compares two ways of localising microdrama screenplays: translating each episode alone, and translating with a series Story Bible. It is deliberately narrow: the output is a review package for selected episodes, not a full studio workflow.

## Run it

Create a `.env` from `.env.example` and set `GEMINI_API_KEY`, then install the project:

```powershell
python -m pip install -e ".[dev]"
python -m kuku_localise.cli run --scripts examples/sample-show --lang hi
```

## Project workspace

For a browser workflow, launch `streamlit run app.py`. Create a project for each microdrama and upload its `.txt` episode files. In **Series context**, build and edit the Story Bible before running localisation. The **Localisation review** compares each source line with an isolated translation and a contextual translation, shows character relationship and voice guidance, and displays AI-generated notes explaining the adaptation. **Continuity** separates rule-based checks from those editorial notes. **Exports** provides the series overview, comparison report, and screenplay preserving the uploaded format with translated dialogue. Choose the target language and Gemini model in project settings. Project inputs and outputs are kept under the gitignored `projects/` directory.

For a private show, keep its input folder outside the repository and use the same command. The default check set is episodes 1, 2, and 10 when present, otherwise the last episode. Override it with `--episodes 1,2,10`; use `--output some-folder` to choose the artifact location.

`KUKU_MODEL` in `.env` replaces the Gemini model ID without a code change. The only model call site is `complete_json` in `src/kuku_localise/llm.py`.

## What a run produces

`outputs/raw/` contains the unedited Story Bible, series index, ingest report, JSON data, series and independent screenplay exports, and `comparison.json`. Keep private inputs and private raw outputs out of version control. `outputs/cache/` stores response cache entries and request usage.

## Limits and review

This uses Gemini's free-tier quota; a fresh run makes one Bible request plus two translation requests per selected episode (with a possible repair request). The automatic report checks beat completeness, timestamps, display-name variants, names, and glossary choices. It does not measure naturalness, cultural suitability, or acting quality. A human should compare both screenplays, edit a line, and approve the final export before use.

Google's free-tier data handling and model availability can change; confirm current terms and quota before using confidential scripts. Do not commit client screenplays or their translations.
