from django.conf import settings

from google import genai
from google.genai import types

from .personas import (
    BASE_SIMULATION_PROMPT,
    CUSTOM_STRUCTURING_PROMPT,
    GOAL_ACHIEVABILITY_CHECK,
    OUTPUT_FORMAT_INSTRUCTIONS,
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


def structure_custom_persona(description):
    """Use Gemini to convert a free-text persona description into a structured profile."""
    client = _get_client()
    prompt = CUSTOM_STRUCTURING_PROMPT.format(description=description)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text


def run_analysis(product_flow):
    """Send product background + screenshots + persona prompt to Gemini and return the response."""
    client = _get_client()
    screenshots = product_flow.screenshots.all()

    # Build the system prompt based on persona type
    if product_flow.persona_type == "custom":
        structured = structure_custom_persona(product_flow.custom_persona_description)
        global_kb_block = format_global_kb_for_prompt()
        system_prompt = BASE_SIMULATION_PROMPT.format(
            structured_persona=structured,
            global_kb=global_kb_block,
            goal_check=GOAL_ACHIEVABILITY_CHECK,
            output_format=OUTPUT_FORMAT_INSTRUCTIONS,
        )
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
        ),
        contents=contents,
    )
    return response.text
