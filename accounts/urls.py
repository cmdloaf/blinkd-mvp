from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("waitlist/", views.waitlist_view, name="waitlist"),
    path("logout/", views.logout_view, name="logout"),
    path("google/", views.google_login, name="google_login"),
    path("google/callback/", views.google_callback, name="google_callback"),
]
