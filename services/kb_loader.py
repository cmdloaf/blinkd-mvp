"""
Modular knowledge base loader for Blinkd.

Loads persona JSON files from knowledge/personas/ and provides lookup functions.
Loads Global KB TXT files from knowledge/global_ux/ (paired UX doctrine files).
Adding a new persona or UX pattern requires only dropping a new file into the
appropriate directory — no Python code changes needed.
"""
import json
from pathlib import Path

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
# Global KB loading (paired UX doctrine)
# ---------------------------------------------------------------------------

def _parse_kb_file(filepath):
    """Parse a structured Global KB .txt file into a dict of field_name -> value.

    Detects field headers as lines where the text before the first colon
    contains only letters, spaces, and parentheses (e.g. "ID:", "Category:",
    "Bad UX Pattern:"). Collects multiline values including bullet lists
    under each header.
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


def load_global_ux_patterns():
    """Load all paired UX doctrine files from knowledge/global_ux/.

    Returns {"patterns": [...]}, where each pattern contains:
    id, category, bad_pattern, symptoms, impact, good_principle, correction.
    """
    patterns = []
    if not GLOBAL_UX_DIR.is_dir():
        return {"patterns": patterns}

    for filepath in sorted(GLOBAL_UX_DIR.iterdir()):
        if filepath.suffix != ".txt":
            continue
        data = _parse_kb_file(filepath)
        if "id" not in data:
            print(f"[KB] Warning: {filepath.name} missing 'ID' field, skipping.")
            continue
        patterns.append({
            "id": data.get("id", ""),
            "category": data.get("category", ""),
            "bad_pattern": data.get("bad ux pattern", ""),
            "symptoms": data.get("symptoms", ""),
            "impact": data.get("user impact", ""),
            "good_principle": data.get("good ux principle", ""),
            "correction": data.get("actionable correction", ""),
        })

    return {"patterns": patterns}


def format_global_kb_for_prompt():
    """Format the Global KB as a compact text block for injection into system prompts.

    Strips redundancy and produces a single unified section. Each pattern
    contains both the bad UX diagnosis and the good UX correction.
    """
    kb = load_global_ux_patterns()
    lines = [
        "=== GLOBAL UX KNOWLEDGE BASE ===",
        "You MUST use ONLY the patterns below when identifying friction and making recommendations.",
        "Each friction point MUST reference a Pattern ID from this knowledge base.",
        "Each recommendation MUST use the pattern's Actionable Correction as the basis for the fix.",
        "Do NOT introduce UX frameworks, heuristics, or principles from outside this knowledge base.",
        "If no matching pattern exists, state: 'No matching UX doctrine found in GLOBAL_KB.'",
    ]

    for p in kb["patterns"]:
        lines.append(f"\n[{p['id']}] ({p['category']})")
        if p["bad_pattern"]:
            lines.append(f"Problem: {p['bad_pattern']}")
        if p["symptoms"]:
            lines.append(f"Symptoms: {p['symptoms']}")
        if p["impact"]:
            lines.append(f"Impact: {p['impact']}")
        if p["good_principle"]:
            lines.append(f"Principle: {p['good_principle']}")
        if p["correction"]:
            lines.append(f"Correction: {p['correction']}")

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
