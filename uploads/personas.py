"""
Persona constants and prompt templates for Blinkd UX analysis.

Persona data is loaded from knowledge/personas/*.json via services.kb_loader.
This module re-exports loader functions and provides prompt templates
used by LLM clients.
"""
from services.kb_loader import (
    build_system_prompt,
    get_persona_by_slug,
    get_persona_choices,
    load_all_personas,
)

OUTPUT_FORMAT_INSTRUCTIONS = """
You MUST structure your response in exactly these 4 sections:

## SECTION 1 — PRODUCT UNDERSTANDING
- Clarity status: Is it immediately clear what this product does?
- Early confusion signals: What might confuse this persona on first encounter?

## SECTION 2 — PERSONA SIMULATION
For each screenshot/step in the flow, provide:
- **Step #**: (step number)
- **Inner monologue**: What this persona is thinking (in their voice)
- **Expectation**: What they expect to happen next
- **Hesitation**: Any pause or doubt (or "None")
- **Confusion reason**: What's unclear (or "None")
- **Emotional state**: How they feel at this point
- **Verdict**: Continue / Hesitate / Drop

## SECTION 3 — FRICTION SUMMARY
List the top issues found:
- **Description**: What the issue is
- **Severity**: Low / Medium / High
- **Root cause**: Why this is a problem
- **Affected persona reasoning**: Why this persona specifically struggles here

## SECTION 4 — RECOMMENDATIONS
For each recommendation:
1. **Observed Problem**: What was found
2. **Why It Happens**: Persona-specific reasoning
3. **Violated UX Pattern**: Which UX principle is broken
4. **Actionable Fix**: A realistic fix (within Django + HTML/CSS architecture)
5. **Expected Impact**: What improves if fixed
6. **Priority**: Low / Med / High
"""

# Backwards-compatible dict: slug -> persona data (loaded from JSON files)
PERSONAS = load_all_personas()

# Choices for forms and model field
PERSONA_CHOICES = get_persona_choices()


def get_system_prompt(persona_slug):
    """Build a full system prompt for a preset persona."""
    persona = get_persona_by_slug(persona_slug)
    if not persona:
        return None
    return build_system_prompt(persona, OUTPUT_FORMAT_INSTRUCTIONS)


CUSTOM_STRUCTURING_PROMPT = """Given the following user description of a persona, create a structured persona profile with these exact fields:

- Demographics (age, role, income, devices used)
- Psychographics (values, attitudes, preferences)
- Behavioral traits (how they interact with products)
- Digital literacy (comfort level with technology — Very Low / Low / Medium / High)
- Risk tolerance (willingness to try unfamiliar things — Very Low / Low / Medium / High)
- Tool familiarity (what apps/tools they use regularly)
- Motivations (what drives them to use this product)
- Emotional triggers (what frustrates or delights them)
- Internal monologue style (how they think, with 3-5 example quotes)

User's description:
{description}

Return ONLY the structured persona profile, no additional commentary."""

BASE_SIMULATION_PROMPT = """You are a UX simulation engine. You are simulating a user persona with the following profile evaluating a product flow.

PERSONA PROFILE:
{structured_persona}

SIMULATION RULES:
- All reactions must tie directly to persona traits. No generic responses.
- Reflect the persona's digital literacy level in how they interpret UI elements.
- Reflect their risk tolerance in how they react to ambiguity and commitment.
- Reflect their patience level in how they respond to workflow length.
- If the persona would realistically drop off, say so and explain why.

Evaluate the product flow shown in the screenshots step by step, staying in character.
{output_format}"""
