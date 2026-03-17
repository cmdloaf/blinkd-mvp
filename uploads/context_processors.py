from django.conf import settings


def app_env(request):
    return {"APP_ENV": settings.APP_ENV}
