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

SEVERITY REWEIGHTING:
- **High**: Directly blocks goal completion, prevents the persona from achieving the primary goal, or causes drop-off. MUST be rated High regardless of other factors.
- **Medium**: Slows or degrades goal completion without fully blocking it — confusing steps the persona can work through, inefficiencies that increase time-on-task, or issues that erode confidence without causing abandonment.
- **Low**: Cosmetic friction with no meaningful goal impact — minor wording, non-blocking inconsistencies, or polish items. Upgrade to Medium if multiple Low issues compound in the same step.

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


CUSTOM_STRUCTURING_PROMPT = """Given the following user description of a persona, return a JSON object that strictly conforms to this schema. Do not include any text outside the JSON object. Do not use markdown code fences.

{{
  "name": "<A short descriptive name for this persona, e.g. 'The Cautious Freelancer'>",
  "demographics": {{
    "age_range": "<age range as string, e.g. '28-40'>",
    "role": "<job title or life role>",
    "income": "<income bracket: low / moderate / high>",
    "devices": "<primary devices used>"
  }},
  "psychographics": {{
    "values": "<core values as a short phrase>",
    "approach": "<general approach or attitude>",
    "risk_tolerance": "<Very Low / Low / Medium / High>",
    "patience": "<Very Low / Low / Medium / High>",
    "efficiency_bias": "<Very Low / Low / Medium / High>"
  }},
  "behavioral_traits": "<2-4 sentence description of how they interact with digital products>",
  "digital_literacy": "<Very Low / Low / Medium / High>",
  "tool_familiarity": ["<tool 1>", "<tool 2>", "<tool 3>"],
  "motivations": ["<motivation 1>", "<motivation 2>", "<motivation 3>"],
  "emotional_triggers": ["<trigger 1>", "<trigger 2>", "<trigger 3>"],
  "internal_monologue_style": "<Description of thinking style with 3-5 example inner-voice quotes>",
  "simulation_rules": [
    "<Persona-specific behavioral rule, e.g. 'This persona has low patience — extra steps cause drop-off'>",
    "<Rule 2>",
    "<Rule 3>",
    "All emotional reactions must tie directly to persona traits. No generic responses."
  ]
}}

User's description:
{description}

Return ONLY the JSON object. No commentary, no markdown, no code fences."""
