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

    # Extract summary: first 1-2 sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    summary = ' '.join(sentences[:2]) if sentences else text[:200]

    # Extract key concerns from bullet points
    concerns = []
    bullet_matches = re.findall(r'[-*•]\s*(.+)', text)
    if bullet_matches:
        concerns = [clean_llm_output(m.strip()) for m in bullet_matches[:3]]
    elif len(sentences) > 2:
        # Fall back to subsequent sentences
        concerns = [s.strip() for s in sentences[2:5] if s.strip()]

    return {
        "clarity_status": clarity_status,
        "summary": summary,
        "key_concerns": concerns,
    }


def parse_analysis_sections(raw_text):
    """Split raw Gemini response into the 4 named sections.

    Returns a dict with keys: product_understanding, persona_simulation,
    friction_summary, recommendations.  Returns None if the expected
    section headers are not found.
    """
    # Split on "## SECTION <digit> — <TITLE>" (handles —, --, –)
    parts = re.split(r'##\s*SECTION\s+\d+\s*[-—–]+\s*', raw_text)

    if len(parts) < 5:
        return None

    keys = [
        "product_understanding",
        "persona_simulation",
        "friction_summary",
        "recommendations",
    ]
    sections = {}
    for i, key in enumerate(keys):
        text = parts[i + 1]
        # Strip the title line (e.g. "PRODUCT UNDERSTANDING\n")
        text = re.sub(r'^[A-Z\s]+\n', '', text, count=1).strip()
        sections[key] = text

    return sections


def _extract_field(block, field_name):
    """Extract text after **Field Name**: up to the next **label** or end."""
    pattern = rf'\*\*{re.escape(field_name)}\*\*:?\s*(.*?)(?=\n\s*\d+\.\s*\*\*|\n\s*\*\*[A-Z]|\Z)'
    match = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
    return clean_llm_output(match.group(1)) if match else ""


def parse_recommendations(text):
    """Parse the recommendations section into a list of dicts."""
    if not text:
        return None

    # Split on numbered items at the start of a line
    blocks = re.split(r'\n(?=\d+\.\s*\*\*)', text)
    # The first chunk might also start with "1."
    if blocks and re.match(r'\d+\.\s*\*\*', blocks[0]):
        pass  # already good
    elif len(blocks) > 1:
        blocks = blocks[1:]

    recs = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        rec = {
            "number": len(recs) + 1,
            "observed_problem": _extract_field(block, "Observed Problem"),
            "pattern_id": _extract_field(block, "Pattern ID"),
            "why_it_happens": _extract_field(block, "Why It Happens"),
            "violated_pattern": _extract_field(block, "Violated UX Pattern"),
            "actionable_fix": _extract_field(block, "Actionable Fix"),
            "expected_impact": _extract_field(block, "Expected Impact"),
            "priority": "",
        }

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
    # Split on lines that start with a bullet + bold Description
    blocks = re.split(r'\n(?=[-*]\s*\*\*Description\*\*)', text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        item = {
            "description": _extract_field(block, "Description"),
            "pattern_id": _extract_field(block, "Pattern ID"),
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
    # Split on **Step #** or **Step <number>** patterns
    blocks = re.split(r'\n(?=[-*]\s*\*\*Step\s)', text)
    # Also handle case where first block starts with the step
    if blocks and re.match(r'[-*]?\s*\*\*Step\s', blocks[0]):
        pass
    elif len(blocks) > 1:
        blocks = blocks[1:]

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        step_match = re.search(r'\*\*Step\s*#?\s*\*\*:?\s*(.*?)(?=\n|$)', block)
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
