from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render

from .forms import GoalsForm, PersonaSelectionForm, ProductBackgroundForm
from .llm import run_analysis
from .models import AnalysisResult, ProductFlow, Screenshot
from .personas import PERSONAS


def _redirect_target(request, default_name, flow_id):
    """If ?next=confirm is set, redirect back to confirmation instead of the normal next step."""
    if request.GET.get("next") == "confirm":
        return redirect("uploads:confirm", flow_id=flow_id)
    return redirect(f"uploads:{default_name}", flow_id=flow_id)


def step1_background(request):
    flow_id = request.GET.get("flow_id")
    flow = get_object_or_404(ProductFlow, id=flow_id) if flow_id else None

    if request.method == "POST":
        if flow:
            form = ProductBackgroundForm(request.POST, instance=flow)
        else:
            form = ProductBackgroundForm(request.POST)
        if form.is_valid():
            flow = form.save()
            return _redirect_target(request, "step2", flow.id)
    else:
        form = ProductBackgroundForm(instance=flow) if flow else ProductBackgroundForm()

    return render(request, "uploads/step1_background.html", {
        "form": form,
        "flow": flow,
        "step": 1,
        "next": request.GET.get("next", ""),
    })


def step2_screenshots(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)

    if request.method == "POST":
        files = request.FILES.getlist("screenshots")
        order_data = request.POST.get("order", "")
        order_map = {}
        if order_data:
            for idx, name in enumerate(order_data.split(",")):
                order_map[name.strip()] = idx

        for f in files:
            order = order_map.get(f.name, 0)
            Screenshot.objects.create(
                product_flow=flow,
                image=f,
                order=order,
            )
        return _redirect_target(request, "step3", flow.id)

    existing = flow.screenshots.all()
    return render(request, "uploads/step2_screenshots.html", {
        "flow": flow,
        "existing": existing,
        "step": 2,
        "next": request.GET.get("next", ""),
    })


def step3_persona(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)

    if request.method == "POST":
        form = PersonaSelectionForm(request.POST)
        if form.is_valid():
            flow.persona_type = form.cleaned_data["persona_type"]
            flow.custom_persona_description = form.cleaned_data.get(
                "custom_persona_description", ""
            )
            flow.save()
            return _redirect_target(request, "step4", flow.id)
    else:
        form = PersonaSelectionForm(initial={
            "persona_type": flow.persona_type or None,
            "custom_persona_description": flow.custom_persona_description,
        })

    return render(request, "uploads/step3_persona.html", {
        "flow": flow,
        "form": form,
        "personas": PERSONAS,
        "step": 3,
        "next": request.GET.get("next", ""),
    })


def step4_goals(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)

    if request.method == "POST":
        form = GoalsForm(request.POST, instance=flow)
        if form.is_valid():
            form.save()
            return _redirect_target(request, "confirm", flow.id)
    else:
        form = GoalsForm(instance=flow)

    return render(request, "uploads/step4_goals.html", {
        "flow": flow,
        "form": form,
        "step": 4,
        "next": request.GET.get("next", ""),
    })


def confirm(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)
    screenshots = flow.screenshots.all()
    persona_name = PERSONAS.get(flow.persona_type, {}).get("name", "Custom Persona")
    persona_data = PERSONAS.get(flow.persona_type)
    has_analysis = hasattr(flow, "analysis")
    return render(request, "uploads/confirm.html", {
        "flow": flow,
        "screenshots": screenshots,
        "persona_name": persona_name,
        "persona_data": persona_data,
        "has_analysis": has_analysis,
        "step": 5,
    })


def analysis_view(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)

    if request.method == "POST":
        print(f"[DEBUG] Running analysis for flow {flow_id}")
        key_setting = getattr(settings, "GEMINI_API_KEY", "") if settings.LLM_PROVIDER == "gemini" else getattr(settings, "ANTHROPIC_API_KEY", "")
        print(f"[DEBUG] API key loaded: {'yes' if key_setting else 'NO - EMPTY'} (provider={settings.LLM_PROVIDER})")
        print(f"[DEBUG] Persona type: {flow.persona_type}")
        print(f"[DEBUG] Screenshots: {flow.screenshots.count()}")
        try:
            response_text = run_analysis(flow)
            print(f"[DEBUG] Success! Response length: {len(response_text)}")
        except Exception as e:
            print(f"[DEBUG] ERROR: {type(e).__name__}: {e}")
            response_text = f"Error calling API: {e}"
        AnalysisResult.objects.update_or_create(
            product_flow=flow,
            defaults={"raw_response": response_text},
        )
        return redirect("uploads:analysis", flow_id=flow.id)

    analysis = getattr(flow, "analysis", None)
    persona_name = PERSONAS.get(flow.persona_type, {}).get("name", "Custom Persona")

    sections = recommendations = friction_items = simulation_steps = None
    if analysis:
        from .parsing import (
            parse_analysis_sections,
            parse_friction_items,
            parse_recommendations,
            parse_simulation_steps,
        )
        sections = parse_analysis_sections(analysis.raw_response)
        if sections:
            recommendations = parse_recommendations(sections.get("recommendations", ""))
            friction_items = parse_friction_items(sections.get("friction_summary", ""))
            simulation_steps = parse_simulation_steps(sections.get("persona_simulation", ""))

    return render(request, "uploads/analysis.html", {
        "flow": flow,
        "analysis": analysis,
        "persona_name": persona_name,
        "sections": sections,
        "recommendations": recommendations,
        "friction_items": friction_items,
        "simulation_steps": simulation_steps,
    })
