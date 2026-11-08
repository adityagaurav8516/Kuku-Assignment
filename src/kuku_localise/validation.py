from __future__ import annotations

import re

from kuku_localise.models import Beat

MAX_CPS_HINDI = 18.0  # Calibrated maximum characters per second for natural Hindi speech
MAX_SUBTITLE_LINE_CHARS = 44
MAX_SUBTITLE_LINES = 2

# Devanagari Unicode boundaries to reliably match word boundaries in Indic scripts
DEV_LEFT = r"(?<![\u0900-\u097F])"
DEV_RIGHT = r"(?![\u0900-\u097F])"

AAP_REGEX = re.compile(DEV_LEFT + r"(आप|आपको|आपका|आपकी|आपके)" + DEV_RIGHT, re.IGNORECASE)
TUM_REGEX = re.compile(DEV_LEFT + r"(तुम|तुम्हें|तुम्हारे|तुम्हारा|तुम्हारी)" + DEV_RIGHT, re.IGNORECASE)
TU_REGEX = re.compile(DEV_LEFT + r"(तू|तुझे|तुझको|तेरा|तेरी|तेरे)" + DEV_RIGHT, re.IGNORECASE)


def validate_timing(text: str, duration: float, max_cps: float = MAX_CPS_HINDI) -> tuple[bool, str | None]:
    """Check if dialogue fits within audio duration based on speech rate budget."""
    if duration <= 0.6 or not text.strip():
        return True, None
    cps = len(text.strip()) / duration
    if cps > max_cps:
        excess_pct = int(((cps - max_cps) / cps) * 100)
        return (
            False,
            f"Timing failed: Too long by ~{excess_pct}% ({len(text.strip())} chars in {duration:.1f}s = {cps:.1f} CPS, max budget {max_cps:.1f} CPS). Shorten to <= {int(duration * max_cps)} chars.",
        )
    return True, None


def validate_register(text: str, expected_register: str, target_lang: str = "Hindi") -> tuple[bool, str | None]:
    """Verify that dialogue adheres to required formal/informal address register (aap/tum/tu)."""
    if "hi" not in target_lang.lower() and "hindi" not in target_lang.lower():
        return True, None

    reg = (expected_register or "").strip().lower()
    if reg == "aap":
        m_tu = TU_REGEX.search(text)
        if m_tu:
            return False, f"Address consistency failed: Used forbidden informal pronoun '{m_tu.group(0)}'. Expected formal 'aap' (आप/आपका/कीजिए)."
        m_tum = TUM_REGEX.search(text)
        if m_tum:
            return False, f"Address consistency failed: Used familiar pronoun '{m_tum.group(0)}'. Expected formal 'aap' (आप/आपका/कीजिए)."
    elif reg == "tu":
        m_aap = AAP_REGEX.search(text)
        if m_aap:
            return False, f"Address consistency failed: Used formal pronoun '{m_aap.group(0)}'. Expected intimate/contemptuous 'tu' (तू/तेरा)."
    elif reg == "tum":
        m_tu = TU_REGEX.search(text)
        if m_tu:
            return False, f"Address consistency failed: Used harsh pronoun '{m_tu.group(0)}'. Expected familiar peer 'tum' (तुम/तुम्हारा)."

    return True, None


def validate_subtitle_fit(
    text: str,
    max_line_chars: int = MAX_SUBTITLE_LINE_CHARS,
    max_lines: int = MAX_SUBTITLE_LINES,
) -> tuple[bool, str | None]:
    """Ensure dialogue conforms to vertical mobile screen subtitle limits."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > max_lines:
        return False, f"Subtitle fit failed: Has {len(lines)} lines; max allowed for mobile screen is {max_lines}."
    for line in lines:
        if len(line) > max_line_chars:
            return False, f"Subtitle fit failed: Line exceeds {max_line_chars} chars ({len(line)} chars). Break line or condense text."
    return True, None


def validate_beat(
    beat: Beat,
    record: dict,
    character: dict | None = None,
    target_lang: str = "Hindi",
) -> list[str]:
    """Run all Step 4 code-based validations on a localized dialogue beat."""
    text = (record.get("text") or "").strip()
    if not text or beat.kind != "dialogue":
        return []

    errors: list[str] = []

    # 1. Timing Validation
    ok_time, err_time = validate_timing(text, beat.duration)
    if not ok_time and err_time:
        errors.append(err_time)

    # 2. Consistency Validation (tum/aap/tu register)
    expected_reg = (character.get("address_register") if character else "") or ""
    ok_reg, err_reg = validate_register(text, expected_reg, target_lang)
    if not ok_reg and err_reg:
        errors.append(err_reg)

    # 3. Subtitle Fit Validation
    ok_sub, err_sub = validate_subtitle_fit(text)
    if not ok_sub and err_sub:
        errors.append(err_sub)

    return errors


def compute_levenshtein(s1: str, s2: str) -> int:
    """Calculate character-level Levenshtein edit distance."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1] * (len(s2) + 1)
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row[j + 1] = min(curr_row[j] + 1, prev_row[j + 1] + 1, prev_row[j] + cost)
        prev_row = curr_row
    return prev_row[len(s2)]


def compute_edit_rate(delivered: str, edited: str) -> float:
    """Compute reviewer edit rate: (characters changed / characters delivered)."""
    delivered_clean = delivered.strip()
    edited_clean = edited.strip()
    if not delivered_clean:
        return 0.0 if not edited_clean else 1.0
    dist = compute_levenshtein(delivered_clean, edited_clean)
    return round(dist / max(1, len(delivered_clean)), 4)
