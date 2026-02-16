import re


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
    return match.group(1).strip() if match else ""


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
