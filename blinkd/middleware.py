import base64
import os

from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect


class BasicAuthMiddleware:
    """Require HTTP Basic Auth when APP_ENV=staging."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.APP_ENV != "staging":
            return self.get_response(request)

        username = os.environ.get("STAGING_USER", "")
        password = os.environ.get("STAGING_PASS", "")
        if not username or not password:
            return self.get_response(request)

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                provided_user, provided_pass = decoded.split(":", 1)
                if provided_user == username and provided_pass == password:
                    return self.get_response(request)
            except Exception:
                pass

        response = HttpResponse("Unauthorized", status=401)
        response["WWW-Authenticate"] = 'Basic realm="Staging"'
        return response


class DomainRedirectMiddleware:
    """301-redirect www to the canonical root domain."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        redirect_map = getattr(settings, "DOMAIN_REDIRECTS", {})
        if host in redirect_map:
            target = redirect_map[host]
            return HttpResponsePermanentRedirect(f"https://{target}{request.get_full_path()}")
        return self.get_response(request)
