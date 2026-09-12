from .models import get_auditorium_for_user


def auditorium_context(request):
    """Inject the current user's Auditorium and is_platform_owner status into every template context."""
    if request.user.is_authenticated:
        from .views import is_master_owner
        return {
            'current_auditorium': get_auditorium_for_user(request.user),
            'is_master_owner': is_master_owner(request.user),
        }
    return {
        'current_auditorium': None,
        'is_master_owner': False,
    }
