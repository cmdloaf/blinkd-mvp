from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PersonaSelectionForm, ProductBackgroundForm
from .gemini import run_analysis
from .models import AnalysisResult, ProductFlow, Screenshot
from .personas import PERSONAS


def step1_background(request):
    if request.method == "POST":
        form = ProductBackgroundForm(request.POST)
        if form.is_valid():
            flow = form.save()
            return redirect("uploads:step2", flow_id=flow.id)
    else:
        form = ProductBackgroundForm()
    return render(request, "uploads/step1_background.html", {"form": form, "step": 1})


def step2_persona(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)

    if request.method == "POST":
        form = PersonaSelectionForm(request.POST)
        if form.is_valid():
            flow.persona_type = form.cleaned_data["persona_type"]
            flow.custom_persona_description = form.cleaned_data.get(
                "custom_persona_description", ""
            )
            flow.save()
            return redirect("uploads:step3", flow_id=flow.id)
    else:
        form = PersonaSelectionForm(initial={
            "persona_type": flow.persona_type or None,
            "custom_persona_description": flow.custom_persona_description,
        })

    return render(request, "uploads/step2_persona.html", {
        "flow": flow,
        "form": form,
        "personas": PERSONAS,
        "step": 2,
    })


def step3_screenshots(request, flow_id):
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
        return redirect("uploads:complete", flow_id=flow.id)

    existing = flow.screenshots.all()
    return render(request, "uploads/step3_screenshots.html", {
        "flow": flow,
        "existing": existing,
        "step": 3,
    })


def step_complete(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)
    screenshots = flow.screenshots.all()
    persona_name = PERSONAS.get(flow.persona_type, {}).get("name", "Custom Persona")
    has_analysis = hasattr(flow, "analysis")
    return render(request, "uploads/step_complete.html", {
        "flow": flow,
        "screenshots": screenshots,
        "persona_name": persona_name,
        "has_analysis": has_analysis,
        "step": 4,
    })


def analysis_view(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)

    if request.method == "POST":
        print(f"[DEBUG] Running analysis for flow {flow_id}")
        print(f"[DEBUG] API key loaded: {'yes' if settings.GEMINI_API_KEY else 'NO - EMPTY'}")
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
    return render(request, "uploads/analysis.html", {
        "flow": flow,
        "analysis": analysis,
        "persona_name": persona_name,
    })
