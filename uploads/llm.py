"""
Provider-agnostic LLM interface for Blinkd.
Tries Gemini first (priority), falls back to Anthropic if Gemini fails or has no key.
"""
from django.conf import settings


def _providers():
    """Return list of available providers in priority order (Gemini first)."""
    providers = []
    if getattr(settings, "GEMINI_API_KEY", ""):
        providers.append("gemini")
    if getattr(settings, "ANTHROPIC_API_KEY", ""):
        providers.append("anthropic")
    return providers


def _get_impl(name):
    if name == "anthropic":
        from . import anthropic_client as impl
    else:
        from . import gemini as impl
    return impl


def structure_custom_persona(description):
    """Convert free-text persona description into a structured profile."""
    providers = _providers()
    if not providers:
        raise RuntimeError("No LLM API key configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY.")
    for provider in providers:
        try:
            return _get_impl(provider).structure_custom_persona(description)
        except Exception:
            if provider == providers[-1]:
                raise
            print(f"[LLM] {provider} failed for structure_custom_persona, falling back...")
    raise RuntimeError("No LLM provider available.")


def run_analysis(product_flow):
    """Run persona-based UX analysis on the product flow; returns raw markdown response."""
    providers = _providers()
    if not providers:
        raise RuntimeError("No LLM API key configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY.")
    for provider in providers:
        try:
            return _get_impl(provider).run_analysis(product_flow)
        except Exception:
            if provider == providers[-1]:
                raise
            print(f"[LLM] {provider} failed for run_analysis, falling back...")
    raise RuntimeError("No LLM provider available.")
