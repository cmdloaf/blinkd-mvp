"""Anthropic (Claude) API client for Blinkd analysis. Same interface as gemini.py."""
import base64
import json
import re

from django.conf import settings
from anthropic import Anthropic

from .personas import (
    CUSTOM_STRUCTURING_PROMPT,
    OUTPUT_FORMAT_INSTRUCTIONS,
    build_system_prompt,
    format_global_kb_for_prompt,
    get_system_prompt,
)

# Vision-capable model for screenshot analysis
ANTHROPIC_MODEL = "claude-sonnet-4-6"


def _get_client():
    return Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _read_screenshot(screenshot):
    """Read a screenshot's image file; return (base64_data, media_type) for Anthropic."""
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

    b64 = base64.standard_b64encode(data).decode("utf-8")
    return b64, mime


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
    """Use Claude to convert a free-text persona description into a structured dict."""
    client = _get_client()
    prompt = CUSTOM_STRUCTURING_PROMPT.format(description=description)
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_custom_persona_dict(message.content[0].text, description)


def run_analysis(product_flow):
    """Send product background + screenshots + persona prompt to Claude and return the response."""
    client = _get_client()
    screenshots = product_flow.screenshots.all()

    if product_flow.persona_type == "custom":
        structured_dict = structure_custom_persona(product_flow.custom_persona_description)
        global_kb_block = format_global_kb_for_prompt()
        system_prompt = build_system_prompt(structured_dict, OUTPUT_FORMAT_INSTRUCTIONS, global_kb_block)
    else:
        system_prompt = get_system_prompt(product_flow.persona_type)
        if not system_prompt:
            return "Error: Unknown persona type."

    # Build user content: intro text + alternating screenshot labels and images
    content = [
        {
            "type": "text",
            "text": (
                f"PRODUCT BACKGROUND:\n{product_flow.product_background}\n\n"
                + (
                    f"PRIMARY USER GOAL:\n{product_flow.goals}\n\n"
                    "This is the central objective the persona must achieve. "
                    "Evaluate all friction and recommendations against this goal.\n\n"
                    if product_flow.goals else ""
                )
                + f"The following {len(screenshots)} screenshot(s) show the product flow in order. "
                "Evaluate each step as this persona would experience it:\n"
            ),
        },
    ]

    for i, screenshot in enumerate(screenshots, 1):
        content.append({"type": "text", "text": f"\n--- Screenshot {i} of {len(screenshots)} ---\n"})
        b64_data, media_type = _read_screenshot(screenshot)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64_data,
            },
        })

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )
    return message.content[0].text
