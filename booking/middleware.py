from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages
from django.urls import reverse
from .models import get_auditorium_for_user


class AuditoriumAccessMiddleware:
    """
    Ensures that if an auditorium is deactivated or suspended,
    none of its users (owner or staff) can access the system.
    Master platform owners (superusers not tied to a deactivated auditorium, or superusers in general)
    can always access the owner portal.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if user account itself is inactive
            if not request.user.is_active:
                logout(request)
                messages.error(request, 'Your account has been deactivated. Please contact support.')
                return redirect('login')

            # Master platform owners (superusers who own no specific auditorium or superuser bypassing check)
            # If a user is a superuser who does not own an auditorium or is managing the platform, allow.
            # But if a regular tenant user or tenant owner belongs to an auditorium that is inactive:
            aud = get_auditorium_for_user(request.user)
            if aud and not aud.is_active:
                # If they are not the platform owner (or even if they are tenant owner/staff)
                # If tenant's auditorium is deactivated, block access!
                # Superuser who owns no auditorium is the Master Platform Admin.
                is_tenant_owner_or_staff = (aud.owner == request.user) or (hasattr(request.user, 'profile') and request.user.profile.auditorium == aud)
                
                # If the user is specifically a tenant user / tenant admin of a suspended auditorium:
                # Even if tenant owner was given is_superuser locally, their auditorium is suspended.
                # Only a global platform superuser without a suspended auditorium (or explicitly allowing logout/suspended page) can pass.
                # Check exempt paths like logout
                exempt_paths = [reverse('logout'), reverse('login'), '/static/', '/media/']
                if not any(request.path.startswith(p) for p in exempt_paths):
                    reason = aud.suspension_reason or "Account suspended due to non-payment or administrative review."
                    logout(request)
                    messages.error(request, f'Access Denied: Auditorium "{aud.name}" is suspended. Reason: {reason}. Please contact the platform owner.')
                    return redirect('login')

        response = self.get_response(request)
        return response
