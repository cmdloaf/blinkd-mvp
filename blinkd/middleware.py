from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class DomainRedirectMiddleware:
    """301-redirect configured root domains to the app subdomain."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        redirect_map = getattr(settings, "DOMAIN_REDIRECTS", {})
        if host in redirect_map:
            target = redirect_map[host]
            return HttpResponsePermanentRedirect(f"https://{target}{request.get_full_path()}")
        return self.get_response(request)
