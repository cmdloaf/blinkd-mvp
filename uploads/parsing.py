import re


def clean_llm_output(text):
    """Remove markdown artifacts and normalize whitespace for display."""
    if not text:
        return ""
    # Triple asterisks first (nested bold+italic)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    # Bold markers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Italic markers (single asterisks not part of bold)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)\*(?!\*)', r'\1', text)
    # Strip full "Referenced Pattern ID: ..." or "Pattern ID: ..." fragments (label + IDs)
    # Must run BEFORE bare ID stripping so the IDs anchor the match
    text = re.sub(
        r'[\(\[]?\s*(?:Referenced\s+)?Pattern\s+IDs?\s*:\s*'
        r'(?:(?:kolenda|handbook|norman)_\w+(?:\s*,\s*)?)+\s*[\)\]]?',
        '',
        text,
        flags=re.IGNORECASE,
    )
    # Strip Global KB pattern IDs in any format: [bracketed], `backtick`, or bare
    text = re.sub(r'`(?:kolenda|handbook|norman)_\w+`', '', text)
    text = re.sub(r'\[(?:kolenda|handbook|norman)_\w+\]', '', text)
    text = re.sub(r'(?:kolenda|handbook|norman)_\w+', '', text)
    # Clean up leftover list/punctuation artifacts after stripping IDs
    text = re.sub(r'(?:,\s*)+\.', '.', text)      # ", , ." → "."
    text = re.sub(r'(?:,\s*){2,}', ', ', text)    # ", , ," → ","
    text = re.sub(r'^\s*[,.:]\s*', '', text)       # Leading punctuation
    text = re.sub(r',\s*$', '', text)              # Trailing comma
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    # Collapse 3+ newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def parse_executive_summary(product_understanding_text):
    """Extract a concise executive summary from the product understanding section.

    Returns a dict with clarity_status, summary, and key_concerns.
    Returns None if input is empty.
    """
    if not product_understanding_text:
        return None

    text = clean_llm_output(product_understanding_text)
    text_lower = text.lower()

    # Detect clarity status via keywords
    if any(kw in text_lower for kw in ("immediately clear", "very clear", "well understood", "clearly communicat")):
        clarity_status = "clear"
    elif any(kw in text_lower for kw in ("unclear", "confusing", "not clear", "difficult to understand", "does not understand")):
        clarity_status = "unclear"
    else:
        clarity_status = "mixed"

    # Fixed one-liner keyed on clarity status — avoids duplicating the bullet content below.
    _CLARITY_SUMMARY = {
        "clear":   "The product's purpose is immediately clear to this persona.",
        "unclear": "The product's purpose presents clarity challenges for this persona.",
        "mixed":   "The product's purpose is partially clear, with some early confusion signals.",
    }
    summary = _CLARITY_SUMMARY[clarity_status]

    # Extract key concerns from bullet points
    concerns = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    bullet_matches = re.findall(r'[-*•]\s*(.+)', text)
    if bullet_matches:
        concerns = [clean_llm_output(m.strip()) for m in bullet_matches[:3]]
    elif len(sentences) > 2:
        # Fall back to subsequent sentences
        concerns = [s.strip() for s in sentences[2:5] if s.strip()]

    # Strip AI-generated label prefixes embedded in concern text
    _CONCERN_PREFIXES = re.compile(
        r'^(?:clarity\s+status|early\s+confusion\s+signals?|confusion\s+signals?|signal)\s*:\s*',
        re.IGNORECASE,
    )
    concerns = [_CONCERN_PREFIXES.sub('', c).strip() for c in concerns]

    return {
        "clarity_status": clarity_status,
        "summary": summary,
        "key_concerns": concerns,
    }


def parse_goal_achievability(text):
    """Parse the goal achievability section into a structured dict.

    Returns a dict with: stated_goal, achievable, achievable_class,
    breakdown_step, dropoff_risk, dropoff_risk_class, root_cause,
    direct_blockers.  Returns None if input is empty.
    """
    if not text:
        return None

    # Handle insufficient info fallback early
    if "insufficient information" in text.lower():
        return {
            "stated_goal": "",
            "achievable": "Insufficient Data",
            "achievable_class": "goal-partial",
            "breakdown_step": "",
            "dropoff_risk": "",
            "dropoff_risk_class": "risk-med",
            "root_cause": "",
            "direct_blockers": "",
        }

    # Do NOT call clean_llm_output() here — _extract_field needs ** markers
    result = {
        "stated_goal": _extract_field(text, "Stated User Goal"),
        "achievable": "",
        "achievable_class": "",
        "breakdown_step": _extract_field(text, "Breakdown Step"),
        "dropoff_risk": "",
        "dropoff_risk_class": "",
        "root_cause": _extract_field(text, "Root Cause of Goal Failure"),
        "direct_blockers": _extract_field(text, "Direct Blockers"),
    }

    # Parse achievable status — try labeled field first, then scan full text
    achievable_raw = _extract_field(text, "Achievable?").lower().strip()
    if not achievable_raw:
        achievable_raw = _extract_field(text, "Achievable").lower().strip()

    if "partial" in achievable_raw:
        result["achievable"] = "Partial"
        result["achievable_class"] = "goal-partial"
    elif "no" in achievable_raw:
        result["achievable"] = "No"
        result["achievable_class"] = "goal-no"
    elif "yes" in achievable_raw:
        result["achievable"] = "Yes"
        result["achievable_class"] = "goal-yes"
    else:
        # No labeled field found — return None (no goal evaluation available)
        return None

    # Parse drop-off risk
    risk_raw = _extract_field(text, "Drop-off Risk").lower().strip()
    if not risk_raw:
        risk_raw = _extract_field(text, "Dropoff Risk").lower().strip()

    if "high" in risk_raw:
        result["dropoff_risk"] = "High"
        result["dropoff_risk_class"] = "risk-high"
    elif "med" in risk_raw:
        result["dropoff_risk"] = "Medium"
        result["dropoff_risk_class"] = "risk-med"
    elif "low" in risk_raw:
        result["dropoff_risk"] = "Low"
        result["dropoff_risk_class"] = "risk-low"
    else:
        result["dropoff_risk"] = ""
        result["dropoff_risk_class"] = ""

    return result


def parse_analysis_sections(raw_text):
    """Split raw LLM response into named sections.

    Supports both the 5-section format (with goal achievability) and the
    legacy 4-section format.  Returns a dict with keys including
    product_understanding, persona_simulation, friction_summary,
    recommendations, and optionally goal_achievability.
    Returns None if the expected section headers are not found.
    """
    # Split on "## SECTION <digit> — <TITLE>" (handles —, --, –)
    parts = re.split(r'##\s*SECTION\s+\d+\s*[-—–]+\s*', raw_text)

    if len(parts) >= 6:
        # New 5-section format (with goal achievability)
        keys = [
            "product_understanding",
            "goal_achievability",
            "persona_simulation",
            "friction_summary",
            "recommendations",
        ]
    elif len(parts) >= 5:
        # Legacy 4-section format
        keys = [
            "product_understanding",
            "persona_simulation",
            "friction_summary",
            "recommendations",
        ]
    else:
        return None

    sections = {}
    for i, key in enumerate(keys):
        text = parts[i + 1]
        # Strip the title line (e.g. "PRODUCT UNDERSTANDING\n")
        text = re.sub(r'^[A-Z\s]+\n', '', text, count=1).strip()
        sections[key] = text

    return sections


def _extract_field(block, field_name):
    """Extract text after **Field Name**: up to the next **label** or end.

    Handles multiple AI output formats:
    - ``**Field**: value``  (inline)
    - ``1. **Field**: value``  (numbered)
    - ``*   **Field**: value``  (bullet-indented)
    - ``- **Field**: value``  (dash bullet)
    """
    pattern = rf'\*\*{re.escape(field_name)}\*\*:?\s*(.*?)(?=\n\s*\d+\.\s+\*\*|\n\s*[-*•]\s+\*\*|\n\s*\*\*\w|\Z)'
    match = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
    return clean_llm_output(match.group(1)) if match else ""


def _first_sentence(text, max_words=20):
    """Return the first sentence of *text*, capped at *max_words* words."""
    if not text:
        return ""
    # Split on sentence-ending punctuation
    match = re.match(r'(.+?[.!?])\s', text)
    sentence = match.group(1) if match else text
    words = sentence.split()
    if len(words) > max_words:
        return ' '.join(words[:max_words]) + '...'
    return sentence


def _clean_pattern_id(raw):
    """Strip brackets, backticks, and whitespace from pattern IDs."""
    return re.sub(r'[\[\]`]', '', raw).strip() if raw else ""


def parse_recommendations(text):
    """Parse the recommendations section into a list of dicts."""
    if not text:
        return None

    # Split on numbered items at the start of a line (handle varied spacing)
    blocks = re.split(r'\n(?=\d+\.\s+\*\*)', text)
    # The first chunk might also start with "1."
    if blocks and re.match(r'\d+\.\s+\*\*', blocks[0]):
        pass  # already good
    elif len(blocks) > 1:
        blocks = blocks[1:]

    recs = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        observed_problem = _extract_field(block, "Observed Problem")
        actionable_fix = _extract_field(block, "Actionable Fix")
        pattern_id_raw = _extract_field(block, "Pattern ID")

        rec = {
            "number": len(recs) + 1,
            "title": _first_sentence(actionable_fix),
            "summary": _first_sentence(observed_problem, max_words=30),
            "observed_problem": observed_problem,
            "pattern_id": _clean_pattern_id(pattern_id_raw),
            "why_it_happens": _extract_field(block, "Why It Happens"),
            "violated_pattern": _extract_field(block, "Violated UX Pattern"),
            "actionable_fix": actionable_fix,
            "expected_impact": _extract_field(block, "Expected Impact"),
            "goal_impact": _extract_field(block, "Goal Impact"),
            "priority": "",
        }

        # Also try "Violated Pattern" (without "UX") as variant
        if not rec["violated_pattern"]:
            rec["violated_pattern"] = _extract_field(block, "Violated Pattern")

        # Extract and normalize priority
        priority_raw = _extract_field(block, "Priority")
        priority_lower = priority_raw.lower().strip()
        if "high" in priority_lower:
            rec["priority"] = "high"
        elif "med" in priority_lower:
            rec["priority"] = "med"
        elif "low" in priority_lower:
            rec["priority"] = "low"
        else:
            rec["priority"] = "med"  # default

        recs.append(rec)

    return recs if recs else None


def parse_friction_items(text):
    """Parse the friction summary section into a list of dicts."""
    if not text:
        return None

    items = []
    # Split on lines that start with bullet or number + bold Description
    blocks = re.split(r'\n(?=[-*]\s*\*\*Description\*\*|\d+\.\s+\*\*Description\*\*)', text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        pattern_id_raw = _extract_field(block, "Pattern ID")
        item = {
            "description": _extract_field(block, "Description"),
            "pattern_id": _clean_pattern_id(pattern_id_raw),
            "severity": "",
            "root_cause": _extract_field(block, "Root cause"),
            "persona_reasoning": _extract_field(block, "Affected persona reasoning"),
        }

        severity_raw = _extract_field(block, "Severity").lower().strip()
        if "high" in severity_raw:
            item["severity"] = "high"
        elif "med" in severity_raw:
            item["severity"] = "med"
        elif "low" in severity_raw:
            item["severity"] = "low"
        else:
            item["severity"] = "med"

        if item["description"]:
            items.append(item)

    return items if items else None


def parse_simulation_steps(text):
    """Parse the persona simulation section into a list of step dicts."""
    if not text:
        return None

    steps = []
    # Split on **Step #** or **Step <number>** patterns (bullet optional, word boundary)
    blocks = re.split(r'\n(?=\s*[-*•]?\s*\*\*Step\b)', text)
    # Also handle case where first block starts with the step
    if blocks and re.match(r'\s*[-*•]?\s*\*\*Step\b', blocks[0]):
        pass
    elif len(blocks) > 1:
        blocks = blocks[1:]

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        step_match = re.search(r'\*\*Step\s*#?(\d+)[^*]*\*\*:?\s*(.*?)(?=\n|$)', block)
        step_num = step_match.group(1).strip() if step_match else str(len(steps) + 1)

        step = {
            "step": step_num,
            "inner_monologue": _extract_field(block, "Inner monologue"),
            "expectation": _extract_field(block, "Expectation"),
            "hesitation": _extract_field(block, "Hesitation"),
            "confusion": _extract_field(block, "Confusion reason"),
            "emotional_state": _extract_field(block, "Emotional state"),
            "verdict": "",
            "verdict_class": "",
        }

        verdict_raw = _extract_field(block, "Verdict").lower().strip()
        if "drop" in verdict_raw:
            step["verdict"] = "Drop"
            step["verdict_class"] = "verdict-drop"
        elif "hesitate" in verdict_raw:
            step["verdict"] = "Hesitate"
            step["verdict_class"] = "verdict-hesitate"
        else:
            step["verdict"] = "Continue"
            step["verdict_class"] = "verdict-continue"

        steps.append(step)

    return steps if steps else None
