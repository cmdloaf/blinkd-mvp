"""
Persona constants and prompt templates for Blinkd UX analysis.

Persona data is loaded from knowledge/personas/*.json via services.kb_loader.
Global KB is loaded from knowledge/global_ux/ bad-UX-only multi-pattern TXT files.
This module re-exports loader functions and provides prompt templates
used by LLM clients.
"""
from services.kb_loader import (
    build_system_prompt,
    format_global_kb_for_prompt,
    get_persona_by_slug,
    get_persona_choices,
    load_all_personas,
)

OUTPUT_FORMAT_INSTRUCTIONS = """
You MUST structure your response in exactly these 5 sections:

## SECTION 1 — PRODUCT UNDERSTANDING
- Clarity status: Is it immediately clear what this product does?
- Early confusion signals: What might confuse this persona on first encounter?

## SECTION 2 — GOAL ACHIEVABILITY
Evaluate whether the persona can achieve the PRIMARY USER GOAL through this product flow:
- **Stated User Goal**: Restate the primary user goal
- **Achievable?**: Yes / Partial / No
- **Breakdown Step**: The step number where goal achievement breaks down (or "N/A" if fully achievable)
- **Drop-off Risk**: Low / Medium / High — likelihood the persona abandons before achieving the goal
- **Root Cause of Goal Failure**: Why the goal cannot be fully achieved (reference a Pattern ID from the Global KB if applicable, or "N/A")
- **Direct Blockers**: List specific UI/flow elements that prevent goal completion (or "None identified")

If no user goal was provided, state: "Insufficient information to evaluate goal achievability."

## SECTION 3 — PERSONA SIMULATION
For each screenshot/step in the flow, provide:
- **Step #**: (step number)
- **Inner monologue**: What this persona is thinking (in their voice)
- **Expectation**: What they expect to happen next
- **Hesitation**: Any pause or doubt (or "None")
- **Confusion reason**: What's unclear (or "None")
- **Emotional state**: How they feel at this point
- **Verdict**: Continue / Hesitate / Drop

## SECTION 4 — FRICTION SUMMARY
List the top issues found. Each issue MUST map to a Pattern ID from the Global Knowledge Base:
- **Description**: What the issue is
- **Pattern ID**: The ID from the Global KB (e.g., kolenda_choice_overload)
- **Severity**: Low / Medium / High
- **Root cause**: Why this is a problem, referencing the bad UX pattern from the KB
- **Affected persona reasoning**: Why this persona specifically struggles here

SEVERITY REWEIGHTING: Friction that directly blocks goal completion MUST be rated **High** severity regardless of other factors. Cosmetic friction that does not affect goal completion should be rated **Low** unless it compounds with other issues.

## SECTION 5 — RECOMMENDATIONS
For each recommendation, you MUST reference a Pattern ID from the Global Knowledge Base and infer a good UX improvement from the detected bad pattern:
1. **Observed Problem**: What was found
2. **Pattern ID**: The KB pattern this maps to
3. **Why It Happens**: Persona-specific reasoning
4. **Violated Pattern**: The bad UX pattern detected from the KB (do NOT use patterns outside the KB)
5. **Actionable Fix**: A realistic fix (within Django + HTML/CSS architecture), inferred from the bad UX pattern — should reduce cognitive load, improve clarity, and align with persona expectations
6. **Expected Impact**: What improves if fixed
7. **Priority**: Low / Med / High
8. **Goal Impact**: "Removes goal blocker" / "Improves goal completion" / "Clarifies goal pathway" / "No direct goal impact"

Recommendations that remove goal blockers or improve goal completion MUST be ranked higher than cosmetic improvements.
"""

# Backwards-compatible dict: slug -> persona data (loaded from JSON files)
PERSONAS = load_all_personas()

# Choices for forms and model field
PERSONA_CHOICES = get_persona_choices()


def get_system_prompt(persona_slug):
    """Build a full system prompt for a preset persona, including Global KB."""
    persona = get_persona_by_slug(persona_slug)
    if not persona:
        return None
    global_kb_block = format_global_kb_for_prompt()
    return build_system_prompt(persona, OUTPUT_FORMAT_INSTRUCTIONS, global_kb_block)


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

GOAL_ACHIEVABILITY_CHECK = """
GOAL ACHIEVABILITY CHECK (MANDATORY):
You MUST evaluate whether the persona can achieve the PRIMARY USER GOAL stated in the user message.
- Assess goal progression at each step of the flow.
- Identify the exact step where goal achievement breaks down, if applicable.
- Friction that directly blocks goal completion MUST be classified as High severity.
- Recommendations that remove goal blockers MUST be prioritized above cosmetic fixes.
- If no goal is provided, state: "Insufficient information to evaluate goal achievability."
- All blockers must reference Pattern IDs from the Global KB where applicable.
"""

BASE_SIMULATION_PROMPT = """You are a UX simulation engine. You are simulating a user persona with the following profile evaluating a product flow.

PERSONA PROFILE:
{structured_persona}

SIMULATION RULES:
- All reactions must tie directly to persona traits. No generic responses.
- Reflect the persona's digital literacy level in how they interpret UI elements.
- Reflect their risk tolerance in how they react to ambiguity and commitment.
- Reflect their patience level in how they respond to workflow length.
- If the persona would realistically drop off, say so and explain why.

{global_kb}

{goal_check}

Evaluate the product flow shown in the screenshots step by step, staying in character.
{output_format}"""
