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


_APP_PATHS = ("/upload/", "/auth/", "/admin/")


class DomainRedirectMiddleware:
    """
    1. 301-redirect www to the canonical root domain.
    2. 302-redirect app paths (/upload/, /auth/, /admin/) from the marketing
       domain to APP_HOST, so all app traffic stays on app.blinkd.site.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        path = request.get_full_path()

        # www → canonical root (301 permanent)
        redirect_map = getattr(settings, "DOMAIN_REDIRECTS", {})
        if host in redirect_map:
            target = redirect_map[host]
            return HttpResponsePermanentRedirect(f"https://{target}{path}")

        # app paths on non-app host → app subdomain (302 temporary)
        app_host = getattr(settings, "APP_HOST", "")
        if app_host and host != app_host and path.startswith(_APP_PATHS):
            return HttpResponsePermanentRedirect(f"https://{app_host}{path}")

        return self.get_response(request)
