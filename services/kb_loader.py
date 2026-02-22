"""
Modular knowledge base loader for Blinkd.

Loads persona JSON files from knowledge/personas/ and provides lookup functions.
Loads Global KB TXT files from knowledge/global_ux/ (bad-UX-only, multi-pattern files).
Adding a new persona or UX pattern requires only dropping a new file into the
appropriate directory — no Python code changes needed.
"""
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PERSONAS_DIR = BASE_DIR / "knowledge" / "personas"
GLOBAL_UX_DIR = BASE_DIR / "knowledge" / "global_ux"

REQUIRED_PERSONA_FIELDS = [
    "slug",
    "demographics",
    "psychographics",
    "digital_literacy",
    "motivations",
    "emotional_triggers",
    "internal_monologue_style",
]


# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

def _validate_persona(data, filepath):
    """Validate that a persona dict contains all required fields."""
    missing = [f for f in REQUIRED_PERSONA_FIELDS if f not in data]
    if missing:
        raise ValueError(
            f"Persona file {filepath.name} is missing required fields: {', '.join(missing)}"
        )


def load_all_personas():
    """Load and validate all persona JSON files from knowledge/personas/.

    Returns a dict mapping slug -> persona data.
    Each call re-reads from disk (no global mutable cache).
    """
    personas = {}
    if not PERSONAS_DIR.is_dir():
        return personas

    for filepath in sorted(PERSONAS_DIR.iterdir()):
        if filepath.suffix != ".json":
            continue
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Failed to load persona file {filepath.name}: {exc}")

        _validate_persona(data, filepath)

        slug = data["slug"]
        if slug in personas:
            raise ValueError(
                f"Duplicate persona slug '{slug}' found in {filepath.name}"
            )
        personas[slug] = data

    return personas


def get_persona_by_slug(slug):
    """Return a single persona dict by slug, or None if not found."""
    personas = load_all_personas()
    return personas.get(slug)


def get_persona_choices():
    """Return a list of (slug, display_name) tuples for form choices, plus the custom option."""
    personas = load_all_personas()
    choices = [(slug, p.get("name", slug)) for slug, p in personas.items()]
    choices.append(("custom", "Custom Persona"))
    return choices


# ---------------------------------------------------------------------------
# Global KB loading (bad-UX-only, multi-pattern files)
# ---------------------------------------------------------------------------

def _parse_fields(text):
    """Parse a text block into a dict of field_name -> value.

    Detects field headers as lines where the text before the first colon
    contains only letters, spaces, and parentheses (e.g. "ID:", "Category:",
    "Description:"). Collects multiline values including bullet lists
    under each header.
    """
    fields = {}
    current_key = None
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped and ":" in stripped:
            potential_key = stripped.split(":", 1)[0].strip()
            potential_value = stripped.split(":", 1)[1].strip()
            if (
                potential_key
                and potential_key[0].isalpha()
                and all(c.isalpha() or c in " ()" for c in potential_key)
            ):
                if current_key is not None:
                    fields[current_key] = "\n".join(current_lines).strip()
                current_key = potential_key.lower()
                current_lines = [potential_value] if potential_value else []
                continue
        if current_key is not None:
            current_lines.append(line.rstrip())

    if current_key is not None:
        fields[current_key] = "\n".join(current_lines).strip()

    return fields


def _parse_multi_pattern_file(filepath):
    """Parse a multi-pattern Global KB .txt file.

    Files have a preamble (TITLE, SOURCE, INFERENCE RULE) followed by
    pattern blocks separated by '---'. Each pattern block has ID, Category,
    Description, Symptoms, Impact.

    Returns a list of pattern dicts.
    """
    text = filepath.read_text(encoding="utf-8")
    blocks = re.split(r'\n-{3,}\s*\n', text)

    patterns = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        fields = _parse_fields(block)
        # Skip preamble blocks (they have TITLE/SOURCE but no ID)
        if "id" not in fields:
            continue
        patterns.append({
            "id": fields.get("id", ""),
            "category": fields.get("category", ""),
            "description": fields.get("description", ""),
            "symptoms": fields.get("symptoms", ""),
            "impact": fields.get("impact", ""),
        })

    return patterns


def load_global_ux_patterns():
    """Load all bad-UX pattern files from knowledge/global_ux/.

    Returns {"patterns": [...]}, where each pattern contains:
    id, category, description, symptoms, impact.
    """
    patterns = []
    if not GLOBAL_UX_DIR.is_dir():
        return {"patterns": patterns}

    for filepath in sorted(GLOBAL_UX_DIR.iterdir()):
        if filepath.suffix != ".txt":
            continue
        file_patterns = _parse_multi_pattern_file(filepath)
        if not file_patterns:
            logger.warning(f"{filepath.name} has no valid patterns, skipping")
            continue
        patterns.extend(file_patterns)

    return {"patterns": patterns}


def format_global_kb_for_prompt():
    """Format the Global KB as a compact text block for injection into system prompts.

    Each pattern contains only the bad UX diagnosis. The LLM infers good UX
    improvements from the detected bad patterns.
    """
    kb = load_global_ux_patterns()
    lines = [
        "=== GLOBAL UX KNOWLEDGE BASE ===",
        "You MUST use ONLY the patterns below when identifying friction and making recommendations.",
        "Each friction point MUST reference a Pattern ID from this knowledge base.",
        "When you detect a bad UX pattern, infer a GOOD UX improvement that:",
        "- reduces cognitive load",
        "- improves clarity toward the stated user goal",
        "- aligns with the selected persona's expectations",
        "- remains actionable within the product's architecture",
        "Do NOT introduce UX frameworks, heuristics, or principles from outside this knowledge base.",
        "If no matching pattern exists, state: 'No matching UX doctrine found in GLOBAL_KB.'",
    ]

    for p in kb["patterns"]:
        lines.append(f"\n[{p['id']}] ({p['category']})")
        if p["description"]:
            lines.append(f"Problem: {p['description']}")
        if p["symptoms"]:
            lines.append(f"Symptoms: {p['symptoms']}")
        if p["impact"]:
            lines.append(f"Impact: {p['impact']}")

    lines.append("\n=== END GLOBAL UX KNOWLEDGE BASE ===")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt building
# ---------------------------------------------------------------------------

def build_system_prompt(persona, output_format_instructions, global_kb_block=""):
    """Build a full system prompt from a persona dict and the output format instructions.

    If global_kb_block is provided, it is inserted between simulation rules and the
    evaluation instruction.
    """
    # Build demographics string
    demo = persona.get("demographics", {})
    demo_parts = []
    if demo.get("age_range"):
        demo_parts.append(f"Age {demo['age_range']}")
    if demo.get("role"):
        demo_parts.append(demo["role"])
    if demo.get("income"):
        demo_parts.append(f"{demo['income']} income")
    if demo.get("devices"):
        demo_parts.append(demo["devices"])
    demographics_line = ", ".join(demo_parts)

    # Build psychographics string
    psych = persona.get("psychographics", {})
    psych_parts = []
    for key, value in psych.items():
        label = key.replace("_", " ").capitalize()
        psych_parts.append(f"{label}: {value}")
    psychographics_line = ". ".join(psych_parts) + "." if psych_parts else ""

    # Tool familiarity
    tools = persona.get("tool_familiarity", [])
    tools_line = ", ".join(tools) if tools else "None specified"

    # Motivations
    motivations = persona.get("motivations", [])
    motivations_line = ". ".join(motivations) + "." if motivations else ""

    # Emotional triggers
    triggers = persona.get("emotional_triggers", [])
    triggers_line = ". ".join(t.capitalize() if not t[0].isupper() else t for t in triggers) + "." if triggers else ""

    # Simulation rules
    rules = persona.get("simulation_rules", [])
    rules_block = "\n".join(f"- {rule}" for rule in rules)

    name = persona.get("name", persona["slug"])

    # Insert Global KB block if provided
    kb_section = f"\n{global_kb_block}\n" if global_kb_block else ""

    goal_check_block = """
GOAL ACHIEVABILITY CHECK (MANDATORY):
You MUST evaluate whether the persona can achieve the PRIMARY USER GOAL stated in the user message.
- Assess goal progression at each step of the flow.
- Identify the exact step where goal achievement breaks down, if applicable.
- Friction that directly blocks goal completion MUST be classified as High severity. Friction that slows but does not block goal completion should be Medium.
- Recommendations that remove goal blockers MUST be prioritized above cosmetic fixes.
- If no goal is provided, state: "Insufficient information to evaluate goal achievability."
- All blockers must reference Pattern IDs from the Global KB where applicable.
"""

    return f"""You are a UX simulation engine. You are simulating a user persona called "{name}" evaluating a product flow.

PERSONA PROFILE:
- Demographics: {demographics_line}
- Psychographics: {psychographics_line}
- Behavioral traits: {persona.get('behavioral_traits', '')}
- Digital literacy: {persona.get('digital_literacy', 'unknown')}
- Risk tolerance: {psych.get('risk_tolerance', 'unknown')}
- Tool familiarity: {tools_line}
- Motivations: {motivations_line}
- Emotional triggers: {triggers_line}
- Internal monologue style: {persona.get('internal_monologue_style', '')}

SIMULATION RULES:
{rules_block}
{kb_section}
{goal_check_block}
Evaluate the product flow shown in the screenshots step by step, staying in character.
{output_format_instructions}"""
