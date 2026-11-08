# Kuku Localise · Studio Workspace

**Kuku Localise** is an enterprise-grade localisation engine designed specifically for fast-paced vertical microdramas. It bridges the critical context gap in serialized content by carrying character identity, evolving power dynamics, address registers (*aap / tum / tu*), and cultural adaptations across episodes.

---

## Core Principle: Pipeline Architecture

> **Guiding Axiom:** *Give the LLM only judgment work; keep measurable constraints in plain code.*

The system executes a strict 6-step pipeline that separates creative adaptation from mathematical compliance:

1. **Step 1: Enhanced Parsing (Code)**  
   Extracts scene numbers, start/end timestamps, clean character cues (recursively stripping nested parentheticals and modifiers like `O.S.` and `V.O.`), and calculates exact audio `duration` in seconds for every beat.

2. **Step 2: Expanded Show Bible Variables (LLM + Human Review)**  
   Constructs a cross-episode Story Bible extracting:
   - **Gender** (critical for Hindi verb agreements: करता/करती, गया/गई)
   - **Address Register** (`aap` formal, `tum` familiar peer, `tu` intimate/contemptuous)
   - **Relationship Dynamics** (power hierarchies, rivalries, family ties)
   - **Low-Confidence Merge Surfacing**: Cues with generic descriptors (`OFF-SCREEN VOICE`, `STRANGER`) or zero token overlap are flagged in the UI for mandatory reviewer verification instead of being merged silently.

3. **Step 3: Context-Rich Translation Pipeline (LLM)**  
   Injects the specific character profile, recent dialogue history (previous 2–3 beats), scene context, and calibrated audio time budget into the model prompt.

4. **Step 4: Strict Code-Based Validation (Code)**  
   Enforces non-negotiable audiovisual constraints purely in Python:
   - **Timing Validation**: Evaluates speech rate against a calibrated Hindi budget (max ~18.0 characters per second).
   - **Consistency Validation**: Unicode-aware regex verification enforcing the character's designated address register (`aap` vs `tum` vs `tu`).
   - **Subtitle Fit Validation**: Restricts line lengths to vertical screen dimensions (max 44 characters per line, max 2 lines per subtitle beat).

5. **Step 5: Automated Repair Loop (LLM)**  
   If a beat fails Step 4 validation, the system feeds it back with an exact corrective directive (e.g. *"Too long by 28%, shorten to <= 36 chars without losing meaning"*). Retries are capped at 2 attempts. If still failing, it is tagged as an **Honest Failure** in the UI for human intervention.

6. **Step 6: Cultural Adaptation Pass (LLM)**  
   A dedicated secondary pass scans dialogue for Western/US idioms and colloquialisms (e.g. *"raincheck"*, *"ballpark"*), attaching explicit cultural rationale and localised equivalents.

---

## Honesty of Measurement & Real Evidence Metrics (ROI)

### Why Structural Metrics Aren't Enough
Previous versions evaluated translations using purely structural checks (`comparison.json`: beat counts, audio timestamp preservation, and code-applied cue unification). However, code-enforced normalization masked the raw model's hallucinations (resulting in a rigged "0 unresolved" applied score).

### Honest Model Evaluation
The engine now evaluates `model_display_name`—the model's honest, raw cue selection—comparing raw consistency between Series Mode and Independent Mode *before* code applies the canonical Bible label.

### True Studio ROI: Reviewer Edit Rate
The true measure of localisation quality and studio cost savings is the **Reviewer Edit Rate**:

$$\text{Reviewer Edit Rate} = \frac{\text{Characters Changed by Human Reviewer}}{\text{Characters Delivered by AI Model}}$$

When a studio reviewer edits lines in the Localisation Review tab:
- **Series Edit Rate** vs **Baseline Edit Rate** is computed per beat and per episode using Levenshtein distance.
- **Reviewer Effort Saved (%)**: Proves the exact percentage of keystrokes and editing time saved by series context over naive isolated translation.

---

## Model Swappability

The engine is decoupled from any single LLM provider through an abstract base client interface:

- `BaseLLMClient`: Abstract base class specifying `complete_json(system, user)` and call/token tracking properties.
- `GeminiClient`: Built on the modern Google GenAI SDK with automatic fallback (e.g., trying `gemini-2.5-flash` if experimental models return 404).
- `MockLLMClient`: Deterministic offline client for unit tests and CI without API keys.
- `get_client(provider, model, cache_dir)`: Central factory driven by `.env` (`LLM_PROVIDER`, `KUKU_MODEL`).

---

## Scaling & Architecture

1. **One-Time Bible Generation**: The Story Bible is built once per show from the screenplay index and reused across all episodes.
2. **Deterministic Content Caching**: LLM responses are cached under `outputs/cache/` keyed by a SHA-256 hash of `(provider, model, system, user)`. Iterative reviews and UI reruns cost zero tokens.
3. **Production `--no-baseline` Flag**: For production workloads, pass `--no-baseline` to skip the independent comparison run, **cutting API calls and token costs by 50%**.
4. **Token Accounting & Cost Tracking**: Aggregated in `outputs/cache/usage.json`, reporting API calls, prompt tokens, candidate tokens, and estimated USD costs per episode and show.
5. **Parallel Scalability**: Episodes can be processed concurrently, bounded only by the provider's API rate limits.

---

## Quickstart & CLI Usage

### 1. Installation
```powershell
python -m pip install -e ".[dev]"
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and configure your API key:
```env
GEMINI_API_KEY=your_key_here
KUKU_MODEL=gemini-2.5-flash
LLM_PROVIDER=gemini
```

### 3. CLI Commands
Run comparison on sample show:
```powershell
python -m kuku_localise.cli run --scripts examples/sample-show --lang hi
```

Run in production mode (skip baseline to cut cost by 50%):
```powershell
python -m kuku_localise.cli run --scripts examples/sample-show --lang hi --no-baseline
```

Process all episodes in a show:
```powershell
python -m kuku_localise.cli run --scripts path/to/episodes --lang hi --episodes all --no-baseline
```

Run unit tests:
```powershell
pytest
```

### 4. Interactive Studio UI
Launch the Cinema Studio workspace:
```powershell
streamlit run app.py
```
