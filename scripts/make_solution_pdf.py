from pathlib import Path
from fpdf import FPDF

root = Path(__file__).parents[1]
output = root / "docs" / "solution.pdf"

pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Title
pdf.set_font("Helvetica", "B", 18)
pdf.set_text_color(75, 29, 107)
pdf.cell(0, 10, "Kuku Localise: Series-Aware Microdrama Localisation", ln=True)

# Subtitle
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(120, 40, 150)
pdf.cell(0, 7, "Action Plan Refactoring & Architecture Report", ln=True)
pdf.ln(3)

sections = [
    (
        "1. Honesty of Measurement",
        "Evaluates model_display_name (the raw model output) to honestly measure cue consistency before code-enforced canonical normalisation. Dynamic KPI badges in the studio continuity scorecard are directly bound to missing_beat_count and timestamps_preserved data."
    ),
    (
        "2. Pipeline Architecture & Principle Enforcement",
        "Axiom: Give the LLM only judgment work; keep measurable constraints in plain code.\n"
        "- Step 1: Enhanced parser extracts clean cue names, strips nested parentheticals and audio modifiers (O.S., V.O.), and calculates beat duration in seconds.\n"
        "- Step 2: Expanded Story Bible extracts gender (crucial for Hindi verb agreement), formal/informal address registers (aap/tum/tu), and surfaces low-confidence alias merges for human review.\n"
        "- Step 3: Context-rich translation prompt injects recent dialogue history, scene context, and time budgets.\n"
        "- Step 4: Strict code validation evaluates characters-per-second (CPS <= 18.0), Unicode address register compliance, and vertical screen subtitle limits.\n"
        "- Step 5: Automated repair loop retries failing beats with explicit error directives (capped at 2 retries), tagging persistent violations as Honest Failures for human intervention.\n"
        "- Step 6: Secondary cultural adaptation pass identifies Western/US idioms and attaches localized equivalents."
    ),
    (
        "3. Real Evidence Metrics (Studio ROI)",
        "Replaces purely structural checks with the Reviewer Edit Rate: (characters changed / characters delivered). Computes Levenshtein edit distance per beat and reports Reviewer Effort Saved (%) comparing series contextual translations against isolated baselines."
    ),
    (
        "4. Model Swappability",
        "Decoupled from Gemini via BaseLLMClient abstract interface. Powered by get_client(provider, model) factory supporting GeminiClient, MockLLMClient, and configurable fallbacks (gemini-2.5-flash)."
    ),
    (
        "5. Scale and Cost",
        "Provides --no-baseline flag to cut production API calls and costs by 50%. Aggregates API calls, prompt/candidate tokens, and estimated USD costs in usage.json. The Story Bible is generated once per show, and responses are deterministically cached."
    ),
]

for heading, body in sections:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(75, 29, 107)
    pdf.cell(0, 6, heading, ln=True)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 5, body)
    pdf.ln(3)

pdf.output(str(output))
print(f"Generated PDF at: {output}")
