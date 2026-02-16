"""
Provider-agnostic LLM interface for Blinkd.
Delegates to Gemini or Anthropic based on settings.LLM_PROVIDER.
"""
from django.conf import settings

_PROVIDER = getattr(settings, "LLM_PROVIDER", "gemini").strip().lower()


def _impl():
    if _PROVIDER == "anthropic":
        from . import anthropic_client as impl
        return impl
    # default: gemini
    from . import gemini as impl
    return impl


def structure_custom_persona(description):
    """Convert free-text persona description into a structured profile."""
    return _impl().structure_custom_persona(description)


def run_analysis(product_flow):
    """Run persona-based UX analysis on the product flow; returns raw markdown response."""
    return _impl().run_analysis(product_flow)
