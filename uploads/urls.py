from django.urls import path

from . import views

app_name = "uploads"

urlpatterns = [
    path("step1/", views.step1_background, name="step1"),
    path("step2/<uuid:flow_id>/", views.step2_persona, name="step2"),
    path("step3/<uuid:flow_id>/", views.step3_screenshots, name="step3"),
    path("complete/<uuid:flow_id>/", views.step_complete, name="complete"),
    path("analysis/<uuid:flow_id>/", views.analysis_view, name="analysis"),
]
