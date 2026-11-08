# Kuku Localise: Series-Aware Microdrama Localisation

## Problem and Architecture

Localising one episode at a time drops context that a serial drama depends on: a character may appear as both a titled name and a short name, relationships affect forms of address (*aap / tum / tu*), and recurring cultural terminology acquires fragmented translations. Kuku Localise accepts a folder of screenplay `.txt` files, builds one compact series index and Story Bible, and produces production deliverables adhering to strict audiovisual constraints.

### Core Principle
> *Give the LLM only judgment work; keep measurable constraints in plain code.*

The system executes a 6-step pipeline:
1. **Enhanced Parsing (Code)**: Extracts scenes, dialogue cues (recursively stripping trailing parentheticals and audio modifiers like `O.S.` and `V.O.`), timestamps, and exact beat durations.
2. **Expanded Story Bible (LLM + Human Review)**: Captures gender (critical for Hindi verb conjugation), address registers (*aap / tum / tu*), relationship hierarchies, and surfaces low-confidence alias merges for human verification.
3. **Context-Rich Translation Pipeline (LLM)**: Feeds character profiles, recent conversational history, and audio time budgets into the prompt.
4. **Strict Code-Based Validation (Code)**: Evaluates characters-per-second (CPS) against calibrated Hindi speech rate budgets (<= 18 CPS), Unicode-level address register consistency, and vertical screen subtitle line fit.
5. **Automated Repair Loop (LLM)**: Feeds back failing lines with specific error directives (e.g. shorten by 30%), capped at 2 retries, tagging lingering violations as Honest Failures.
6. **Cultural Adaptation Pass (LLM)**: Identifies Western/US idioms and generates culturally adapted equivalents with explanatory rationale.

---

## Metric Honesty & Real Evidence Metrics (ROI)

### Structural Metrics vs. Real Evidence
Earlier versions reported structural compliance (missing beats, timestamp retention, and code-applied cue unification). However, code-enforced normalization masked raw model hallucinations (forcing a "0 unresolved" applied cues score).

### Honest Cue Consistency
The system now measures `model_display_name`—the model's honest, raw cue selection—comparing raw consistency between Series Mode and Independent Mode *before* code applies the canonical Bible label.

### Reviewer Edit Rate: The True Studio ROI
Studio ROI is measured by the **Reviewer Edit Rate**:

$$\text{Reviewer Edit Rate} = \frac{\text{Characters Changed by Human Reviewer}}{\text{Characters Delivered by AI Model}}$$

When reviewers edit lines in the workspace:
- Edit distance is computed using Levenshtein distance on delivered vs edited text per beat.
- **Reviewer Effort Saved (%)** demonstrates the exact reduction in human labor achieved by injecting series context over baseline translation.

---

## Model Swappability

The engine decouples model execution via `BaseLLMClient`:
- `BaseLLMClient`: Abstract interface specifying `complete_json(system, user)` and usage tracking.
- `GeminiClient`: Powered by the modern Google GenAI SDK with automatic fallback to reliable models (`gemini-2.5-flash`).
- `MockLLMClient`: Deterministic offline client for tests and CI.
- `get_client()`: Central factory function driven by `LLM_PROVIDER` and `KUKU_MODEL` in `.env`.

---

## Scaling & Architecture

- **Single Bible Generation**: The Story Bible is generated once per show from the screenplay index and reused across all episodes.
- **Content Hash Caching**: LLM responses are cached under `outputs/cache/` keyed by a SHA-256 hash of `(provider, model, system, user)`.
- **Production `--no-baseline` Flag**: Skips the independent baseline run for production batches, cutting API calls and token costs by 50%.
- **Token Accounting & Cost Tracking**: Aggregated in `outputs/cache/usage.json`, reporting API calls, prompt/candidate tokens, and estimated USD costs per episode and show.
- **Parallel Processing**: Episodes can be processed concurrently, bounded only by the provider's API rate limits.
