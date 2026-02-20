import threading

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import GoalsForm, PersonaSelectionForm, ProductBackgroundForm
from .llm import run_analysis
from .models import AnalysisResult, ProductFlow, Screenshot
from .personas import PERSONAS


WIZARD_STEPS = [
    {"num": 1, "name": "Describe", "url_name": "uploads:step1", "needs_flow_id": False},
    {"num": 2, "name": "Upload", "url_name": "uploads:step2", "needs_flow_id": True},
    {"num": 3, "name": "Choose", "url_name": "uploads:step3", "needs_flow_id": True},
    {"num": 4, "name": "Define", "url_name": "uploads:step4", "needs_flow_id": True},
    {"num": 5, "name": "Review", "url_name": "uploads:confirm", "needs_flow_id": True},
    {"num": 6, "name": "Analysis", "url_name": "uploads:analysis", "needs_flow_id": True},
]


def _get_max_reachable_step(flow):
    """Return the highest step number the user can navigate to."""
    if not flow:
        return 1
    if not (flow.product_background and flow.product_background.strip()):
        return 1
    if not flow.screenshots.exists():
        return 2
    if not (flow.persona_type and flow.persona_type.strip()):
        return 3
    if not (flow.goals and flow.goals.strip()):
        return 4
    analysis = getattr(flow, "analysis", None)
    if not analysis:
        return 5
    return 6


def _build_stepper_context(flow, current_step):
    """Return list of step dicts with num, name, state, url."""
    max_reachable = _get_max_reachable_step(flow) if flow else 1
    steps = []
    for s in WIZARD_STEPS:
        num, name, url_name, needs_flow_id = s["num"], s["name"], s["url_name"], s["needs_flow_id"]
        if num < current_step:
            state = "done"
        elif num == current_step:
            state = "active"
        elif num <= max_reachable:
            state = "available"
        else:
            state = "locked"

        if num == 1:
            url = reverse("uploads:step1")
            if flow:
                url = url + "?flow_id=" + str(flow.id)
        elif flow and needs_flow_id:
            url = reverse(url_name, kwargs={"flow_id": flow.id})
        else:
            url = None

        steps.append({"num": num, "name": name, "state": state, "url": url})
    return steps


def _check_prerequisites(flow, target_step):
    """Return redirect Response if prerequisites not met, else None."""
    max_reachable = _get_max_reachable_step(flow)
    if target_step <= max_reachable:
        return None
    step_config = next(s for s in WIZARD_STEPS if s["num"] == max_reachable)
    if max_reachable == 1:
        url = reverse("uploads:step1")
        if flow:
            url = url + "?flow_id=" + str(flow.id)
        return redirect(url)
    return redirect(step_config["url_name"], flow_id=flow.id)


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
        "stepper": _build_stepper_context(flow, 1),
        "next": request.GET.get("next", ""),
    })


def step2_screenshots(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)
    guard = _check_prerequisites(flow, 2)
    if guard:
        return guard

    if request.method == "POST":
        # All uploads already happened via AJAX — just apply reorder/removal
        order_csv = request.POST.get("screenshot_order", "")
        if order_csv:
            ids = [x.strip() for x in order_csv.split(",") if x.strip()]
            flow.screenshots.exclude(pk__in=ids).delete()
            for idx, sid in enumerate(ids):
                flow.screenshots.filter(pk=sid).update(order=idx)
        return _redirect_target(request, "step3", flow.id)

    existing = flow.screenshots.all()
    return render(request, "uploads/step2_screenshots.html", {
        "flow": flow,
        "existing": existing,
        "step": 2,
        "stepper": _build_stepper_context(flow, 2),
        "next": request.GET.get("next", ""),
    })


@require_POST
def upload_screenshot_ajax(request, flow_id):
    """Accept a single screenshot file via AJAX, return JSON with id/url/order."""
    flow = get_object_or_404(ProductFlow, id=flow_id)
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "No file provided"}, status=400)

    next_order = flow.screenshots.count()
    screenshot = Screenshot.objects.create(
        product_flow=flow, image=f, order=next_order,
    )
    return JsonResponse({
        "id": screenshot.pk,
        "url": screenshot.image.url,
        "order": screenshot.order,
    })


def _reindex_screenshots(flow):
    """Re-number screenshot order fields to be sequential (0, 1, 2...)."""
    for idx, screenshot in enumerate(flow.screenshots.all()):
        if screenshot.order != idx:
            screenshot.order = idx
            screenshot.save(update_fields=["order"])


@require_POST
def delete_screenshot(request, flow_id, screenshot_id):
    """Delete a single screenshot and re-index the remaining ones."""
    flow = get_object_or_404(ProductFlow, id=flow_id)
    flow.screenshots.filter(pk=screenshot_id).delete()
    _reindex_screenshots(flow)
    next_url = request.POST.get("next", "")
    if next_url == "confirm":
        return redirect("uploads:confirm", flow_id=flow.id)
    return redirect("uploads:step2", flow_id=flow.id)


def step3_persona(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)
    guard = _check_prerequisites(flow, 3)
    if guard:
        return guard

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
        "stepper": _build_stepper_context(flow, 3),
        "next": request.GET.get("next", ""),
    })


def step4_goals(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)
    guard = _check_prerequisites(flow, 4)
    if guard:
        return guard

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
        "stepper": _build_stepper_context(flow, 4),
        "next": request.GET.get("next", ""),
    })


def confirm(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)
    guard = _check_prerequisites(flow, 5)
    if guard:
        return guard
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
        "stepper": _build_stepper_context(flow, 5),
    })


def _run_analysis_in_background(flow_id):
    """Run AI analysis in a background thread and update status on completion."""
    from django.db import connection
    try:
        flow = ProductFlow.objects.get(id=flow_id)
        response_text = run_analysis(flow)
        AnalysisResult.objects.update_or_create(
            product_flow=flow,
            defaults={"raw_response": response_text},
        )
        flow.analysis_status = "complete"
        flow.save(update_fields=["analysis_status"])
    except Exception as e:
        print(f"[DEBUG] Background analysis ERROR: {type(e).__name__}: {e}")
        try:
            flow = ProductFlow.objects.get(id=flow_id)
            flow.analysis_status = "failed"
            flow.save(update_fields=["analysis_status"])
        except Exception:
            pass
    finally:
        connection.close()


@require_POST
def start_analysis(request, flow_id):
    """Start AI analysis in background and redirect to loading page."""
    flow = get_object_or_404(ProductFlow, id=flow_id)

    if flow.analysis_status == "processing":
        return redirect("uploads:analysis_loading", flow_id=flow.id)

    flow.analysis_status = "processing"
    flow.save(update_fields=["analysis_status"])

    thread = threading.Thread(
        target=_run_analysis_in_background,
        args=(flow.id,),
        daemon=True,
    )
    thread.start()

    return redirect("uploads:analysis_loading", flow_id=flow.id)


@require_GET
def analysis_loading(request, flow_id):
    """Show loading screen while analysis is processing."""
    flow = get_object_or_404(ProductFlow, id=flow_id)
    guard = _check_prerequisites(flow, 5)
    if guard:
        return guard

    if flow.analysis_status == "complete":
        return redirect("uploads:analysis", flow_id=flow.id)

    persona_name = PERSONAS.get(flow.persona_type, {}).get("name", "Custom Persona")
    return render(request, "uploads/analysis_loading.html", {
        "flow": flow,
        "persona_name": persona_name,
        "stepper": _build_stepper_context(flow, 6),
    })


@require_GET
def analysis_status_api(request, flow_id):
    """JSON endpoint for polling analysis status."""
    flow = get_object_or_404(ProductFlow, id=flow_id)
    return JsonResponse({"status": flow.analysis_status})


def _build_dashboard_context(recommendations, friction_items, simulation_steps, goal_achievability=None):
    """Build sorted/counted dashboard context for the template."""
    priority_order = {"high": 0, "med": 1, "low": 2}

    sorted_recs = sorted(
        recommendations or [],
        key=lambda r: priority_order.get(r.get("priority", "med"), 1),
    )
    sorted_friction = sorted(
        friction_items or [],
        key=lambda f: priority_order.get(f.get("severity", "med"), 1),
    )

    high_recs = sum(1 for r in sorted_recs if r.get("priority") == "high")
    high_friction = sum(1 for f in sorted_friction if f.get("severity") == "high")
    # Goal blockers not already counted as high priority
    goal_blockers = sum(
        1 for r in sorted_recs
        if "blocker" in r.get("goal_impact", "").lower()
        and r.get("priority") != "high"
    )

    problematic_steps = [
        s for s in (simulation_steps or [])
        if s.get("verdict", "").lower() in ("drop", "hesitate")
    ]

    return {
        "critical_count": high_recs + high_friction + goal_blockers,
        "total_recommendations": len(sorted_recs),
        "total_friction": len(sorted_friction),
        "sorted_recommendations": sorted_recs,
        "sorted_friction": sorted_friction,
        "problematic_steps_count": len(problematic_steps),
        "total_steps": len(simulation_steps) if simulation_steps else 0,
        "goal_achievable": goal_achievability.get("achievable", "N/A") if goal_achievability else "N/A",
        "goal_achievable_class": goal_achievability.get("achievable_class", "") if goal_achievability else "",
    }


def analysis_view(request, flow_id):
    flow = get_object_or_404(ProductFlow, id=flow_id)
    guard = _check_prerequisites(flow, 6)
    if guard:
        return guard

    # Re-run analysis (from results page re-run button)
    if request.method == "POST":
        if flow.analysis_status == "processing":
            return redirect("uploads:analysis_loading", flow_id=flow.id)

        flow.analysis_status = "processing"
        flow.save(update_fields=["analysis_status"])

        thread = threading.Thread(
            target=_run_analysis_in_background,
            args=(flow.id,),
            daemon=True,
        )
        thread.start()

        return redirect("uploads:analysis_loading", flow_id=flow.id)

    analysis = getattr(flow, "analysis", None)
    persona_name = PERSONAS.get(flow.persona_type, {}).get("name", "Custom Persona")

    sections = None
    executive_summary = None
    goal_achievability = None
    recommendations = None
    friction_items = None
    simulation_steps = None
    dashboard = None

    if analysis:
        from .parsing import (
            parse_analysis_sections,
            parse_executive_summary,
            parse_friction_items,
            parse_goal_achievability,
            parse_recommendations,
            parse_simulation_steps,
        )
        sections = parse_analysis_sections(analysis.raw_response)
        if sections:
            executive_summary = parse_executive_summary(sections.get("product_understanding", ""))
            goal_achievability = parse_goal_achievability(sections.get("goal_achievability", ""))
            recommendations = parse_recommendations(sections.get("recommendations", ""))
            friction_items = parse_friction_items(sections.get("friction_summary", ""))
            simulation_steps = parse_simulation_steps(sections.get("persona_simulation", ""))
            dashboard = _build_dashboard_context(recommendations, friction_items, simulation_steps, goal_achievability)

    return render(request, "uploads/analysis.html", {
        "flow": flow,
        "analysis": analysis,
        "persona_name": persona_name,
        "sections": sections,
        "executive_summary": executive_summary,
        "goal_achievability": goal_achievability,
        "recommendations": recommendations,
        "friction_items": friction_items,
        "simulation_steps": simulation_steps,
        "dashboard": dashboard,
        "stepper": _build_stepper_context(flow, 6),
    })
