from django.urls import path

from . import views

app_name = "uploads"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("step1/", views.step1_background, name="step1"),
    path("step2/<uuid:flow_id>/", views.step2_screenshots, name="step2"),
    path("step2/<uuid:flow_id>/upload/", views.upload_screenshot_ajax, name="upload_screenshot"),
    path("step2/<uuid:flow_id>/delete/<int:screenshot_id>/", views.delete_screenshot, name="delete_screenshot"),
    path("step2/<uuid:flow_id>/reorder/", views.reorder_screenshots, name="reorder_screenshots"),
    path("step2/<uuid:flow_id>/rename/<int:screenshot_id>/", views.rename_screenshot, name="rename_screenshot"),
    path("step3/<uuid:flow_id>/", views.step3_persona, name="step3"),
    path("step4/<uuid:flow_id>/", views.step4_goals, name="step4"),
    path("confirm/<uuid:flow_id>/", views.confirm, name="confirm"),
    path("analysis/start/<uuid:flow_id>/", views.start_analysis, name="start_analysis"),
    path("analysis/loading/<uuid:flow_id>/", views.analysis_loading, name="analysis_loading"),
    path("analysis/status/<uuid:flow_id>/", views.analysis_status_api, name="analysis_status"),
    path("analysis/<uuid:flow_id>/", views.analysis_view, name="analysis"),
]
