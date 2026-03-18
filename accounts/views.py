import logging

from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from supabase_auth.errors import AuthApiError

from accounts.models import CustomUser, WaitlistEntry, is_email_allowed
from accounts.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def _sync_user(supabase_user):
    """Get or create a local CustomUser from a Supabase auth user."""
    user, created = CustomUser.objects.get_or_create(
        id=supabase_user.id,
        defaults={"email": supabase_user.email},
    )
    if created:
        # Supabase manages the password — set unusable password on Django side
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def _safe_next(request, fallback="/"):
    """Return next URL only if it's safe (same host, no open redirect)."""
    next_url = request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return fallback


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_safe_next(request, reverse("uploads:dashboard")))

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        if not is_email_allowed(email):
            return render(request, "accounts/login.html", {"error": "This email hasn't been approved for access."})
        try:
            res = get_supabase().auth.sign_in_with_password({"email": email, "password": password})
            user = _sync_user(res.user)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect(_safe_next(request, reverse("uploads:dashboard")))
        except AuthApiError as e:
            logger.warning("Supabase login failed: %s", e)
            return render(request, "accounts/login.html", {"error": "Invalid email or password."})
        except Exception as e:
            logger.error("Unexpected login error: %s", e)
            return render(request, "accounts/login.html", {"error": "Something went wrong. Please try again."})

    return render(request, "accounts/login.html")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if not is_email_allowed(email):
            return render(request, "accounts/signup.html", {"error": "This email hasn't been approved for access. Contact us to request an invite.", "email": email})
        if password != confirm:
            return render(request, "accounts/signup.html", {"error": "Passwords do not match."})
        if len(password) < 8:
            return render(request, "accounts/signup.html", {"error": "Password must be at least 8 characters.", "email": email})

        try:
            res = get_supabase().auth.sign_up({"email": email, "password": password})
            if res.user is None:
                # Email confirmation required
                return render(request, "accounts/signup.html", {"success": "Check your email to confirm your account."})
            user = _sync_user(res.user)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect(reverse("uploads:dashboard"))
        except AuthApiError as e:
            logger.warning("Supabase signup failed: %s", e)
            return render(request, "accounts/signup.html", {"error": "An account with this email may already exist.", "email": email})
        except Exception as e:
            logger.error("Unexpected signup error: %s", e)
            return render(request, "accounts/signup.html", {"error": "Something went wrong. Please try again.", "email": email})

    return render(request, "accounts/signup.html")


def waitlist_view(request):
    if request.user.is_authenticated:
        return redirect(reverse("uploads:dashboard"))

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        name = request.POST.get("name", "").strip()
        if not email:
            return render(request, "accounts/waitlist.html", {"error": "Please enter a valid email address."})
        if is_email_allowed(email):
            return render(request, "accounts/waitlist.html", {
                "already_approved": True,
            })
        WaitlistEntry.objects.get_or_create(email=email, defaults={"name": name})
        return render(request, "accounts/waitlist.html", {"success": True})

    return render(request, "accounts/waitlist.html")


def logout_view(request):
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    logout(request)
    return redirect("/")


def google_login(request):
    """Redirect user to Supabase Google OAuth flow."""
    callback_url = request.build_absolute_uri("/auth/google/callback/")
    try:
        res = get_supabase().auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": callback_url},
        })
        return redirect(res.url)
    except Exception as e:
        logger.error("Google OAuth initiation failed: %s", e)
        return redirect("/auth/login/?error=oauth_unavailable")


def google_callback(request):
    """
    Supabase redirects here with ?code=... after Google OAuth.
    Exchange the code for a session, sync user, start Django session.
    """
    code = request.GET.get("code")
    if not code:
        return redirect("/auth/login/?error=oauth_failed")
    try:
        res = get_supabase().auth.exchange_code_for_session({"auth_code": code})
        if not is_email_allowed(res.user.email):
            return redirect("/auth/login/?error=not_approved")
        user = _sync_user(res.user)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(reverse("uploads:dashboard"))
    except AuthApiError as e:
        logger.warning("Google OAuth callback failed: %s", e)
        return redirect("/auth/login/?error=oauth_failed")
    except Exception as e:
        logger.error("Unexpected Google callback error: %s", e)
        return redirect("/auth/login/?error=oauth_failed")
