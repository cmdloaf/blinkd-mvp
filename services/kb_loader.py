"""
Modular knowledge base loader for Blinkd.

Loads persona JSON files from knowledge/personas/ and provides lookup functions.
Loads Global KB TXT files from knowledge/global/bad_ux/ and knowledge/global/good_ux/.
Adding a new persona or UX pattern requires only dropping a new file into the
appropriate directory — no Python code changes needed.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PERSONAS_DIR = BASE_DIR / "knowledge" / "personas"
GLOBAL_DIR = BASE_DIR / "knowledge" / "global"
BAD_UX_DIR = GLOBAL_DIR / "bad_ux"
GOOD_UX_DIR = GLOBAL_DIR / "good_ux"

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
# Global KB loading
# ---------------------------------------------------------------------------

def _parse_kb_file(filepath):
    """Parse a structured Global KB .txt file into a dict of field_name -> value.

    Detects field headers as lines where the text before the first colon
    contains only letters, spaces, and parentheses (e.g. "ID:", "Category:",
    "Opposite (Good UX Principle):"). Collects multiline values including
    bullet lists under each header.
    """
    text = filepath.read_text(encoding="utf-8")
    fields = {}
    current_key = None
    current_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped and ":" in stripped:
            potential_key = stripped.split(":", 1)[0].strip()
            potential_value = stripped.split(":", 1)[1].strip()
            # A valid key starts with a letter and contains only letters, spaces, parens
            if (
                potential_key
                and potential_key[0].isalpha()
                and all(c.isalpha() or c in " ()" for c in potential_key)
            ):
                # Save previous field
                if current_key is not None:
                    fields[current_key] = "\n".join(current_lines).strip()
                current_key = potential_key.lower()
                current_lines = [potential_value] if potential_value else []
                continue
        # Append to current field
        if current_key is not None:
            current_lines.append(line.rstrip())

    # Save last field
    if current_key is not None:
        fields[current_key] = "\n".join(current_lines).strip()

    return fields


def load_bad_ux_patterns():
    """Load all bad UX pattern files from knowledge/global/bad_ux/."""
    patterns = []
    if not BAD_UX_DIR.is_dir():
        return patterns
    for filepath in sorted(BAD_UX_DIR.iterdir()):
        if filepath.suffix != ".txt":
            continue
        data = _parse_kb_file(filepath)
        if "id" not in data:
            print(f"[KB] Warning: {filepath.name} missing 'ID' field, skipping.")
            continue
        patterns.append(data)
    return patterns


def load_good_ux_patterns():
    """Load all good UX pattern files from knowledge/global/good_ux/."""
    patterns = []
    if not GOOD_UX_DIR.is_dir():
        return patterns
    for filepath in sorted(GOOD_UX_DIR.iterdir()):
        if filepath.suffix != ".txt":
            continue
        data = _parse_kb_file(filepath)
        if "id" not in data:
            print(f"[KB] Warning: {filepath.name} missing 'ID' field, skipping.")
            continue
        patterns.append(data)
    return patterns


def load_global_kb():
    """Load the full Global Knowledge Base.

    Returns {"bad_ux": [...], "good_ux": [...]}.
    """
    return {
        "bad_ux": load_bad_ux_patterns(),
        "good_ux": load_good_ux_patterns(),
    }


def format_global_kb_for_prompt():
    """Format the Global KB as a text block for injection into system prompts.

    Includes restriction instructions that constrain the AI to only use
    patterns from this knowledge base when identifying friction and making
    recommendations.
    """
    kb = load_global_kb()
    sections = []

    sections.append("=== GLOBAL UX KNOWLEDGE BASE ===")
    sections.append("")
    sections.append("You MUST use ONLY the patterns below when identifying friction and making recommendations.")
    sections.append("Every friction point MUST reference a Bad UX Pattern ID from this knowledge base.")
    sections.append("Every recommendation MUST reference both the Bad UX Pattern ID and the corresponding Good UX Principle ID.")
    sections.append("Do NOT introduce UX frameworks, heuristics, or principles from outside this knowledge base.")
    sections.append("If no matching pattern exists in this knowledge base, state: 'No matching UX principle found in GLOBAL_KB.'")
    sections.append("")

    sections.append("--- BAD UX PATTERNS ---")
    for pattern in kb["bad_ux"]:
        sections.append(f"\n[{pattern.get('id', 'UNKNOWN')}]")
        sections.append(f"Category: {pattern.get('category', 'N/A')}")
        sections.append(f"Description: {pattern.get('description', 'N/A')}")
        if "symptoms" in pattern:
            sections.append(f"Symptoms: {pattern['symptoms']}")
        if "impact" in pattern:
            sections.append(f"Impact: {pattern['impact']}")
        if "opposite (good ux principle)" in pattern:
            sections.append(f"Good UX Counterpart: {pattern['opposite (good ux principle)']}")

    sections.append("\n--- GOOD UX PRINCIPLES ---")
    for pattern in kb["good_ux"]:
        sections.append(f"\n[{pattern.get('id', 'UNKNOWN')}]")
        sections.append(f"Category: {pattern.get('category', 'N/A')}")
        sections.append(f"Description: {pattern.get('description', 'N/A')}")
        if "prevents" in pattern:
            sections.append(f"Prevents: {pattern['prevents']}")
        if "outcome" in pattern:
            sections.append(f"Outcome: {pattern['outcome']}")

    sections.append("\n=== END GLOBAL UX KNOWLEDGE BASE ===")
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# System prompt building
# ---------------------------------------------------------------------------

def build_system_prompt(persona, output_format_instructions, global_kb_block=""):
    """Build a full system prompt from a persona dict and the output format instructions.

    Reconstructs the same prompt structure that was previously hardcoded in personas.py.
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
Evaluate the product flow shown in the screenshots step by step, staying in character.
{output_format_instructions}"""
