import json
import re

from django.conf import settings

from google import genai
from google.genai import types

from .personas import (
    CUSTOM_STRUCTURING_PROMPT,
    OUTPUT_FORMAT_INSTRUCTIONS,
    build_system_prompt,
    format_global_kb_for_prompt,
    get_system_prompt,
)


def _get_client():
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _read_screenshot(screenshot):
    """Read a screenshot's image file and return a Gemini Part."""
    screenshot.image.open("rb")
    data = screenshot.image.read()
    screenshot.image.close()

    name = screenshot.image.name.lower()
    if name.endswith(".png"):
        mime = "image/png"
    elif name.endswith(".webp"):
        mime = "image/webp"
    elif name.endswith(".gif"):
        mime = "image/gif"
    else:
        mime = "image/jpeg"

    return types.Part.from_bytes(data=data, mime_type=mime)


def _parse_custom_persona_dict(raw_text, description):
    """Parse LLM JSON response into a validated persona dict for build_system_prompt()."""
    text = raw_text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {
            "slug": "custom_persona",
            "name": "Custom Persona",
            "demographics": {},
            "psychographics": {"risk_tolerance": "unknown"},
            "behavioral_traits": description,
            "digital_literacy": "unknown",
            "tool_familiarity": [],
            "motivations": [description],
            "emotional_triggers": [],
            "internal_monologue_style": "Not specified.",
            "simulation_rules": [
                "Simulate this persona based on the product background description provided.",
                "All emotional reactions must tie directly to persona traits. No generic responses.",
            ],
        }

    if not isinstance(data.get("demographics"), dict):
        data["demographics"] = {}
    if not isinstance(data.get("psychographics"), dict):
        data["psychographics"] = {}
    if "risk_tolerance" not in data["psychographics"]:
        data["psychographics"]["risk_tolerance"] = "unknown"

    for list_field in ("tool_familiarity", "motivations", "emotional_triggers", "simulation_rules"):
        val = data.get(list_field)
        if isinstance(val, str):
            data[list_field] = [val] if val.strip() else []
        elif isinstance(val, list):
            data[list_field] = [v for v in val if isinstance(v, str) and v.strip()]
        else:
            data[list_field] = []

    if not data["simulation_rules"]:
        data["simulation_rules"] = [
            "All emotional reactions must tie directly to persona traits. No generic responses."
        ]

    data["slug"] = "custom_persona"
    return data


def structure_custom_persona(description):
    """Use Gemini to convert a free-text persona description into a structured dict."""
    client = _get_client()
    prompt = CUSTOM_STRUCTURING_PROMPT.format(description=description)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return _parse_custom_persona_dict(response.text, description)


def run_analysis(product_flow):
    """Send product background + screenshots + persona prompt to Gemini and return the response."""
    client = _get_client()
    screenshots = product_flow.screenshots.all()

    # Build the system prompt based on persona type
    if product_flow.persona_type == "custom":
        structured_dict = structure_custom_persona(product_flow.custom_persona_description)
        global_kb_block = format_global_kb_for_prompt()
        system_prompt = build_system_prompt(structured_dict, OUTPUT_FORMAT_INSTRUCTIONS, global_kb_block)
    else:
        system_prompt = get_system_prompt(product_flow.persona_type)
        if not system_prompt:
            return "Error: Unknown persona type."

    # Build content parts: product background text + screenshots as images
    goals_block = (
        f"PRIMARY USER GOAL:\n{product_flow.goals}\n\n"
        "This is the central objective the persona must achieve. "
        "Evaluate all friction and recommendations against this goal.\n\n"
    ) if product_flow.goals else ""
    contents = [
        f"PRODUCT BACKGROUND:\n{product_flow.product_background}\n\n"
        + goals_block
        + f"The following {len(screenshots)} screenshot(s) show the product flow in order. "
        "Evaluate each step as this persona would experience it:\n",
    ]

    for i, screenshot in enumerate(screenshots, 1):
        contents.append(f"\n--- Screenshot {i} of {len(screenshots)} ---\n")
        contents.append(_read_screenshot(screenshot))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=65536,
        ),
        contents=contents,
    )
    return response.text
