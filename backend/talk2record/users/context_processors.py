from django.conf import settings


def allauth_settings(request):
    """Expose some settings from django-allauth in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
        "DJANGO_ADMIN_FORCE_ALLAUTH": settings.DJANGO_ADMIN_FORCE_ALLAUTH,
    }
