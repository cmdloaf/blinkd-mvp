"""
Modular knowledge base loader for Blinkd.

Loads persona JSON files from knowledge/personas/ and provides lookup functions.
Adding a new persona requires only dropping a new JSON file into that directory.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PERSONAS_DIR = BASE_DIR / "knowledge" / "personas"

REQUIRED_PERSONA_FIELDS = [
    "slug",
    "demographics",
    "psychographics",
    "digital_literacy",
    "motivations",
    "emotional_triggers",
    "internal_monologue_style",
]


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


def build_system_prompt(persona, output_format_instructions):
    """Build a full system prompt from a persona dict and the output format instructions.

    Reconstructs the same prompt structure that was previously hardcoded in personas.py.
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

Evaluate the product flow shown in the screenshots step by step, staying in character.
{output_format_instructions}"""
