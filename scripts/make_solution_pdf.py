from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


root = Path(__file__).parents[1]
output = root / "docs" / "solution.pdf"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="KukuTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=HexColor("#4B1D6B"), spaceAfter=10))
styles.add(ParagraphStyle(name="KukuHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=HexColor("#4B1D6B"), spaceBefore=11, spaceAfter=4))
styles.add(ParagraphStyle(name="KukuBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.6, leading=13.2, spaceAfter=7))
story = [
    Paragraph("Kuku Localise", styles["KukuTitle"]),
    Paragraph("Series-aware microdrama localisation", styles["KukuHeading"]),
    Paragraph("A checkable prototype for translating a serial screenplay without losing character identity, relationships, or recurring terms between episodes.", styles["KukuBody"]),
    Paragraph("Problem and prototype", styles["KukuHeading"]),
    Paragraph("Localising one episode at a time drops context that serial drama depends on: a character can have several cue labels, relationships change forms of address, and recurring objects can acquire multiple translations. Kuku Localise takes a folder of screenplay text files, builds one compact series index and Story Bible, then compares episode-only translations with translations made using that Bible.", styles["KukuBody"]),
    Paragraph("The narrow output is deliberately checkable: selected episodes become editable, timestamp-preserving screenplays plus a structural consistency report. It is not a full studio workflow and does not approve a translation automatically.", styles["KukuBody"]),
    Paragraph("How it works", styles["KukuHeading"]),
    Paragraph("The parser reads metadata, scenes, cue labels, acting notes, timestamps, and dialogue/action/sound/music beats. It assigns stable beat IDs such as e01-s01-b001; a malformed file appears in an ingest report and does not halt the show. Code then compacts loglines, continuity notes, cue counts, parentheticals, samples, and possible aliases into a series index.", styles["KukuBody"]),
    Paragraph("Gemini turns that index into a Story Bible with character aliases and display names, relationship and address guidance, glossary decisions, a plot spine, and adaptation policy. Series mode receives the current episode's relevant Bible slice and prior logline; independent mode receives only that episode. The renderer, not the model, preserves structure and timestamps.", styles["KukuBody"]),
    Paragraph("Cost, quality, and limits", styles["KukuHeading"]),
    Paragraph("A fresh run makes one Bible request plus two translation requests per checked episode, with an occasional repair request for missing beat IDs. Cached responses make iterative review inexpensive. At one show weekly, cost stays bounded by the selected episodes; scale requires paid quota, batching, and monitoring rather than a different prompt.", styles["KukuBody"]),
    Paragraph("Rules compare completeness, timestamps, glossary use, referenced names, and cue variants. In the private Hindi run on episodes 1, 2, and 10 (50 source episodes indexed), both modes preserved all expected beats and timestamps. The model still emitted two Juliana cue variants, but series rendering reduced the approved output to one canonical display name. Referenced-name score was 0.667: episode 2 used a Gerald spelling that differed from the Bible target. Naturalness remains a human decision; the score is a check, not approval.", styles["KukuBody"]),
    Paragraph("Confidential input packs and raw translations are excluded from version control. Reviewers store edits separately by beat ID, preserving the unedited package for audit.", styles["KukuBody"]),
]
doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=19*mm, leftMargin=19*mm, topMargin=17*mm, bottomMargin=17*mm)
doc.build(story)
print(output)
