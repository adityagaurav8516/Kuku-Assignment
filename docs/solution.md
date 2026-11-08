# Kuku Localise: series-aware microdrama localisation

## Problem and prototype

Localising one episode at a time drops context that a serial drama depends on: a character may appear as both a titled name and a short name, relationships affect forms of address, and a recurring object may acquire multiple translations. Kuku Localise accepts a folder of screenplay `.txt` files, builds one compact series index and Story Bible, then compares translations made independently with translations made using that Bible.

The narrow deliverable is checkable: selected episodes return editable, timestamp-preserving screenplays and a structural consistency report. It is not a 50-episode studio or automatic approval system.

## How it works

The parser reads episode metadata, scene structure, cue labels, acting notes, timestamps, and dialogue/action/sound/music beats. It assigns stable beat IDs such as `e01-s01-b001`; a malformed file is listed in the ingest report and does not stop the folder.

Code creates a compact index (loglines, continuity notes, cue counts, parentheticals, samples, and possible aliases). Gemini turns that into a Story Bible: character aliases and display names, address guidance, glossary decisions, a plot spine, and adaptation policy. Series translations receive only the current episode’s relevant Bible slice and preceding logline; independent translations receive just the episode. The renderer, not the model, retains structure and timestamps.

## Cost, quality, and limits

A fresh run uses one Bible request plus two translation requests for each checked episode, with an occasional repair request for missing beat IDs. Responses are cached, which makes iterative review inexpensive. At one show weekly, cost is bounded by the selected episode count; a larger workload needs paid quota, batching, and operational monitoring rather than a different prompt.

Rules compare completeness, order/timestamps, glossary use, referenced names, and cue variants. In the private Hindi run on episodes 1, 2, and 10 (50 source episodes indexed), both modes preserved all expected beats and timestamps. The model still emitted two Juliana cue variants - `LADY JULIANA` and `LADY JULIANA (Off-screen)` - but series rendering reduced the approved output to one canonical display name. The automatic referenced-name score was 0.667 in both modes: in episode 2 the model wrote `जेराल्ड` where the Bible's target spelling was `गेराल्ड`. Naturalness remains a side-by-side human decision; the score is a check, not approval.

Confidential source packs and raw translated outputs are not committed. Reviewers edit an approved copy separately so the unedited raw package remains auditable.
