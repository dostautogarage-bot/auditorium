"""
Auditorium Booking System - Views
Generated and maintained by Bob
A highly skilled software engineer
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import json
from .models import Auditorium, Booking, Expense, UserProfile, get_auditorium_for_user
from .forms import (
    AdminCreationForm, AdminEditForm, AuditoriumRegistrationForm,
    BookingForm, ExpenseForm, PlatformAuditoriumCreateForm, PlatformAuditoriumEditForm
)

User = get_user_model()


def is_master_owner(user):
    """
    Check if the user is the Master Application / Platform Owner.
    Hardcoded master user is username 'owner', or userprofile marked with is_platform_owner=True.
    Auditorium superusers (tenant admins) are NOT platform owners.
    """
    if not user.is_authenticated:
        return False
    if user.username == "owner":
        return True
    try:
        if getattr(user.profile, 'is_platform_owner', False):
            return True
    except Exception:
        pass
    return False


def _deny_non_platform_owner(request):
    """Protect platform master owner portal views."""
    if not is_master_owner(request.user):
        messages.error(request, 'Access restricted to Platform Master Owner.')
        return redirect('dashboard')
    return None


def _is_staff2(user):
    """Return True if the user has the Staff2 role (minimum privileges)."""
    try:
        return user.profile.is_staff2
    except Exception:
        return False


def _deny_staff2(request):
    """
    Call at the top of any view that staff2 users must not access.
    Returns an HttpResponse redirect if denied, None if allowed.
    """
    if not request.user.is_superuser and _is_staff2(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'status': 'error', 'message': 'Access denied.'}, status=403)
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('calendar')
    return None


# -------------------- POST-LOGIN REDIRECT --------------------
@login_required
def after_login(request):
    """Smart post-login redirect: master platform owner → owner portal, auditorium superusers → dashboard, staff → calendar."""
    if is_master_owner(request.user):
        return redirect('owner_portal_dashboard')
    if request.user.is_superuser:
        return redirect('dashboard')
    return redirect('calendar')


# -------------------- REGISTRATION --------------------
def register(request):
    """Self-registration: create a new auditorium owner account."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuditoriumRegistrationForm(request.POST)
        if form.is_valid():
            user, auditorium = form.save()
            from django.contrib.auth import login as auth_login
            auth_login(request, user)
            messages.success(request, f'Welcome! Your auditorium "{auditorium.name}" is ready.')
            return redirect('dashboard')
    else:
        form = AuditoriumRegistrationForm()
    return render(request, 'booking/register.html', {'form': form})


# -------------------- DASHBOARD --------------------
@login_required
def dashboard(request):
    if not request.user.is_superuser:
        return redirect('calendar')

    auditorium = get_auditorium_for_user(request.user)

    now = timezone.now()
    today_str = now.strftime('%Y-%m-%d')
    
    # Filters
    selected_month = request.GET.get('month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # If no filters at all, default to current month for a clear overview
    if not any([selected_month, start_date, end_date]):
        selected_month = now.strftime('%Y-%m')
    
    # Default end_date to today if not in month-priority mode and not specified
    if not selected_month and not end_date:
        end_date = today_str
    
    admin_id = request.GET.get('admin_id')
    
    # Base query scoped to this auditorium
    filtered_qs = Booking.objects.filter(auditorium=auditorium)
    
    # Filter Logic (Priority: Month > Date Range)
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
            filtered_qs = filtered_qs.filter(start_time__year=year, start_time__month=month)
        except (ValueError, AttributeError):
            pass
    else:
        if start_date:
            filtered_qs = filtered_qs.filter(start_time__date__gte=start_date)
        if end_date:
            filtered_qs = filtered_qs.filter(start_time__date__lte=end_date)
            
    if admin_id:
        filtered_qs = filtered_qs.filter(created_by_id=admin_id)
 
    # Stats
    total_advance = filtered_qs.aggregate(Sum('advance_received'))['advance_received__sum'] or 0
    total_amount = filtered_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    pending_amount = total_amount - total_advance
    filtered_count = filtered_qs.count()
    
    # Fixed Stats (Contextual — scoped to this auditorium)
    month_total = Booking.objects.filter(auditorium=auditorium, start_time__month=now.month, start_time__year=now.year).count()
    my_total = Booking.objects.filter(auditorium=auditorium, created_by=request.user).count()
    admin_total = User.objects.filter(is_staff=True).count()
    total_life = Booking.objects.filter(auditorium=auditorium).count()
    
    # Admin Breakdown — scoped to this auditorium
    admin_breakdown = User.objects.filter(profile__auditorium=auditorium).annotate(
        collected=Sum('bookings__advance_received', filter=Q(bookings__in=filtered_qs)),
        booking_count=Count('bookings', filter=Q(bookings__in=filtered_qs)),
        total_booking_amount=Sum('bookings__total_amount', filter=Q(bookings__in=filtered_qs))
    ).order_by('-collected')
    
    # Calculate pending amount for each admin
    for admin in admin_breakdown:
        admin.pending_amount = (admin.total_booking_amount or 0) - (admin.collected or 0)
    
    # Month list for dropdown (last 12 months)
    month_options = []
    for i in range(12):
        m = (now.month - i - 1) % 12 + 1
        y = now.year + (now.month - i - 1) // 12
        date_obj = now.replace(year=y, month=m, day=1)
        month_options.append({
            'value': date_obj.strftime('%Y-%m'),
            'label': date_obj.strftime('%B %Y')
        })

    # Filter Helpers
    all_admins = User.objects.filter(profile__auditorium=auditorium).order_by('username')
    recent_bookings = filtered_qs.order_by('-start_time')[:10]

    # Expense summary
    expense_qs = Expense.objects.filter(auditorium=auditorium)
    expense_total_spent = expense_qs.aggregate(s=Sum('amount'))['s'] or 0
    recent_expenses = expense_qs.order_by('-created_at')[:5]

    return render(request, 'booking/dashboard.html', {
        'auditorium': auditorium,
        'stats': {
            'month_total': month_total,
            'total_advance': total_advance,
            'total_amount': total_amount,
            'pending_amount': pending_amount,
            'my_total': my_total,
            'admin_total': admin_total,
            'total_life': total_life,
            'filtered_count': filtered_count
        },
        'expense_total_spent': expense_total_spent,
        'recent_expenses': recent_expenses,
        'admin_breakdown': admin_breakdown,
        'all_admins': all_admins,
        'month_options': month_options,
        'recent_bookings': recent_bookings,
        'filters': {
            'month': selected_month,
            'start_date': start_date,
            'end_date': end_date,
            'admin_id': admin_id
        }
    })

# -------------------- ADMIN MANAGEMENT --------------------
@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_list(request):
    """List admin users scoped to the current auditorium."""
    query = request.GET.get('q', '').strip()
    auditorium = get_auditorium_for_user(request.user)

    # Only users whose profile belongs to this auditorium
    admins = User.objects.filter(
        profile__auditorium=auditorium
    ).order_by('-date_joined')

    if query:
        admins = admins.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

    per_page = int(request.GET.get('per_page', 100))
    if per_page not in [100, 200, 300, 500]:
        per_page = 100

    paginator = Paginator(admins, per_page)
    page_number = request.GET.get('page')
    admin_page = paginator.get_page(page_number)

    return render(request, 'booking/admin_list.html', {
        'admins': admin_page,
        'query': query,
        'per_page': per_page,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_create(request):
    """Create a new admin user, stamped to the current auditorium."""
    auditorium = get_auditorium_for_user(request.user)
    if request.method == 'POST':
        form = AdminCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Link the new user's profile to this auditorium
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={
                'is_bookable': False,
                'expense_enabled': False,
                'export_enabled': False,
            })
            profile.auditorium = auditorium
            profile.save()
            messages.success(request, f'Admin user "{user.username}" created successfully!')
            return redirect('admin_list')
    else:
        form = AdminCreationForm()

    return render(request, 'booking/admin_form.html', {
        'form': form,
        'title': 'Create New Admin',
        'submit_text': 'Create Admin'
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_edit(request, pk):
    """Edit an admin user — must belong to the same auditorium."""
    auditorium = get_auditorium_for_user(request.user)
    admin = get_object_or_404(User, pk=pk, is_staff=True, profile__auditorium=auditorium)

    if request.method == 'POST':
        form = AdminEditForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            messages.success(request, f'Admin user \"{admin.username}\" updated successfully!')
            return redirect('admin_list')
    else:
        form = AdminEditForm(instance=admin)

    return render(request, 'booking/admin_form.html', {
        'form': form,
        'admin': admin,
        'title': f'Edit Admin: {admin.username}',
        'submit_text': 'Update Admin'
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete(request, pk):
    """Delete an admin user — must belong to the same auditorium."""
    auditorium = get_auditorium_for_user(request.user)
    admin = get_object_or_404(User, pk=pk, is_staff=True, profile__auditorium=auditorium)

    if admin.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('admin_list')

    if request.method == 'POST':
        username = admin.username
        admin.delete()
        messages.success(request, f'Admin user \"{username}\" deleted successfully!')
        return redirect('admin_list')

    return render(request, 'booking/admin_confirm_delete.html', {'admin': admin})


# -------------------- RESET STAFF PASSWORD --------------------

@login_required
@user_passes_test(lambda u: u.is_superuser)
def reset_staff_password(request, pk):
    """Superuser resets a staff member's password."""
    auditorium = get_auditorium_for_user(request.user)
    staff = get_object_or_404(User, pk=pk, is_staff=True, profile__auditorium=auditorium)

    if request.method != 'POST':
        return redirect('admin_list')

    new_password = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()

    if not new_password:
        messages.error(request, 'Password cannot be empty.')
        return redirect('admin_list')

    if new_password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return redirect('admin_list')

    if len(new_password) < 6:
        messages.error(request, 'Password must be at least 6 characters.')
        return redirect('admin_list')

    staff.set_password(new_password)
    staff.save()
    messages.success(request, f'Password for "{staff.username}" has been reset successfully.')
    return redirect('admin_list')


# -------------------- BOOKING MANAGEMENT --------------------

@login_required
def booking_list(request):
    deny = _deny_staff2(request)
    if deny:
        return deny
    now = timezone.now()
    auditorium = get_auditorium_for_user(request.user)

    query = request.GET.get('q', '').strip()
    payment_status = request.GET.get('payment_status', '').strip()
    
    bookings = Booking.objects.filter(auditorium=auditorium).order_by('-created_at')
    
    # Stats scoped to this auditorium
    total_this_month = Booking.objects.filter(auditorium=auditorium, start_time__month=now.month, start_time__year=now.year).count()
    my_bookings_count = Booking.objects.filter(auditorium=auditorium, created_by=request.user).count()
    total_admins = User.objects.filter(is_staff=True).count()

    # Search filter
    if query:
        bookings = bookings.filter(
            Q(title__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(mobile_number__icontains=query)
        )
    
    # Payment status filter
    if payment_status == 'paid':
        bookings = bookings.filter(payment_pending=False)
    elif payment_status == 'pending':
        bookings = bookings.filter(payment_pending=True)
    # 'all' or empty shows everything
        
    per_page = int(request.GET.get('per_page', 300))
    if per_page not in [50, 100, 300, 500]:
        per_page = 300

    paginator = Paginator(bookings, per_page)
    page_number = request.GET.get('page')
    booking_page = paginator.get_page(page_number)
    
    return render(request, 'booking/booking_list.html', {
        'bookings': booking_page,
        'query': query,
        'payment_status': payment_status,
        'per_page': per_page,
        'stats': {
            'month_total': total_this_month,
            'my_total': my_bookings_count,
            'admin_total': total_admins
        }
    })

@login_required
def booking_create(request):
    deny = _deny_staff2(request)
    if deny:
        return deny
    # Check if user is allowed to create bookings
    if request.user.is_staff and not request.user.is_superuser:
        try:
            profile = request.user.profile
            if profile.is_staff2 or not profile.is_bookable:
                error_msg = 'You do not have permission to create bookings.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect(request.META.get('HTTP_REFERER', 'calendar'))
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            UserProfile.objects.create(user=request.user, is_bookable=True)
    
    auditorium = get_auditorium_for_user(request.user)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            
            # Prevent Past Bookings
            if booking.start_time < timezone.now():
                error_msg = 'Cannot create a booking in the past!'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('calendar')

            # Backend Conflict Check (scoped to this auditorium)
            conflicts = Booking.objects.filter(
                auditorium=auditorium,
            ).filter(
                Q(start_time__lt=booking.end_time, end_time__gt=booking.start_time)
            )
            if conflicts.exists():
                error_msg = 'Conflict detected! This slot is already partially or fully booked.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('calendar')

            booking.created_by = request.user
            booking.auditorium = auditorium
            booking.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Booking successfully created.'})
            messages.success(request, 'Booking successfully created.')
            return redirect('calendar')
        else:
            # Form validation failed - return form with errors for display
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # For AJAX, return JSON with error messages
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == '__all__':
                            error_messages.append(str(error))
                        else:
                            friendly_field = field.replace('_', ' ').title()
                            error_messages.append(f"{friendly_field}: {error}")
                final_msg = '<br>'.join(error_messages)
                return JsonResponse({'status': 'error', 'message': final_msg})
            # For regular requests, render form with errors
            return render(request, 'booking/booking_form.html', {
                'form': form,
                'title': 'Create New Booking',
                'submit_text': 'Create Booking'
            })
    
    else:
        initial_data = {}
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')
        if start_time:
            initial_data['start_time'] = start_time
        if end_time:
            initial_data['end_time'] = end_time
        form = BookingForm(initial=initial_data)
        
    return render(request, 'booking/booking_form.html', {
        'form': form,
        'title': 'Create New Booking',
        'submit_text': 'Create Booking'
    })

@login_required
def booking_edit(request, pk):
    deny = _deny_staff2(request)
    if deny:
        return deny
    # Check if user is allowed to edit bookings
    if request.user.is_staff and not request.user.is_superuser:
        try:
            profile = request.user.profile
            if profile.is_staff2 or not profile.is_bookable:
                error_msg = 'You do not have permission to edit bookings.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect(request.META.get('HTTP_REFERER', 'calendar'))
        except UserProfile.DoesNotExist:
            pass

    booking = get_object_or_404(Booking, pk=pk)

    # Only the creator or superuser can edit
    if not request.user.is_superuser and booking.created_by != request.user:
        error_msg = 'You can only edit bookings you created.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': error_msg})
        messages.error(request, error_msg)
        return redirect('calendar')
    
    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            new_booking = form.save(commit=False)
            if new_booking.start_time < timezone.now():
                error_msg = 'Cannot set a booking to a past time!'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('calendar')
            new_booking.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Booking successfully updated.'})
            messages.success(request, 'Booking successfully updated.')
            return redirect('calendar')
        else:
            # Form validation failed - return form with errors for display
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # For AJAX, return JSON with error messages
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        if field == '__all__':
                            error_messages.append(str(error))
                        else:
                            friendly_field = field.replace('_', ' ').title()
                            error_messages.append(f"{friendly_field}: {error}")
                final_msg = '<br>'.join(error_messages)
                return JsonResponse({'status': 'error', 'message': final_msg})
            # For regular requests, render form with errors
            return render(request, 'booking/booking_form.html', {
                'form': form,
                'title': f'Edit Booking: {booking.title}',
                'submit_text': 'Update Booking'
            })
    else:
        form = BookingForm(instance=booking)
        
    return render(request, 'booking/booking_form.html', {
        'form': form,
        'title': f'Edit Booking: {booking.title}',
        'submit_text': 'Update Booking'
    })

@login_required
def booking_delete(request, pk):
    deny = _deny_staff2(request)
    if deny:
        return deny
    booking = get_object_or_404(Booking, pk=pk)

    # Only the creator or superuser can delete
    if not request.user.is_superuser and booking.created_by != request.user:
        error_msg = 'You can only delete bookings you created.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': error_msg})
        messages.error(request, error_msg)
        return redirect('calendar')

    if request.method == 'POST':
        booking.delete()
        messages.success(request, 'Booking deleted successfully.')
        
        # Smart redirection based on origin
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
            
        referer = request.META.get('HTTP_REFERER', '')
        if 'calendar' in referer:
            return redirect('calendar')
        return redirect('booking_list')
        
    return render(request, 'booking/booking_confirm_delete.html', {'booking': booking})


# -------------------- PAYMENT REPORT (SUPER ADMIN ONLY) --------------------

@login_required
@user_passes_test(lambda u: u.is_superuser)
def payment_report(request):
    """Payment report showing which admins received advance payments"""
    auditorium = get_auditorium_for_user(request.user)

    # Get all admins with their bookings and total advance received
    admins = User.objects.filter(is_staff=True).prefetch_related('bookings')
    
    admin_payment_data = []
    total_advance = 0
    
    for admin in admins:
        bookings_with_advance = admin.bookings.filter(auditorium=auditorium, advance_received__gt=0)
        advance_sum = bookings_with_advance.aggregate(total=Sum('advance_received'))['total'] or 0
        
        admin_payment_data.append({
            'admin': admin,
            'booking_count': admin.bookings.filter(auditorium=auditorium).count(),
            'bookings_with_advance': bookings_with_advance.count(),
            'total_advance': advance_sum,
            'bookable': getattr(admin.profile, 'is_bookable', True) if hasattr(admin, 'profile') else True
        })
        total_advance += advance_sum
    
    # Sort by total advance
    admin_payment_data.sort(key=lambda x: x['total_advance'], reverse=True)
    
    # Pagination
    per_page = int(request.GET.get('per_page', 50))
    if per_page not in [25, 50, 100]:
        per_page = 50
    
    paginator = Paginator(admin_payment_data, per_page)
    page_number = request.GET.get('page')
    admin_data_page = paginator.get_page(page_number)
    
    admin_count = len(admin_payment_data)
    avg_per_admin = total_advance / admin_count if admin_count > 0 else 0
    
    return render(request, 'booking/payment_report.html', {
        'admin_data': admin_data_page,
        'total_advance': total_advance,
        'avg_per_admin': avg_per_admin,
        'per_page': per_page,
    })


# -------------------- PWA --------------------

def manifest_json(request):
    manifest = {
        "id": "/",
        "name": "Audy — Auditorium Booking",
        "short_name": "Audy",
        "description": "Book and manage auditorium reservations",
        "start_url": "/login/",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "background_color": "#ffffff",
        "theme_color": "#FF7A00",
        "orientation": "portrait",
        "categories": ["productivity", "business"],
        "icons": [
            {
                "src": "/static/favicon-32.png",
                "sizes": "32x32",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable"
            }
        ]
    }
    response = JsonResponse(manifest)
    response['Content-Type'] = 'application/manifest+json'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def sw_js(request):
    sw_content = """
const CACHE_VERSION = 'audy-v5';
const STATIC_ASSETS = [
    '/static/favicon.png',
    '/static/favicon-32.png',
    '/static/favicon-16.png',
    '/static/icon-192.png',
    '/static/icon-512.png',
];

// Shell pages that must be pre-cached so Chrome counts this SW as capable
// of serving navigate requests (required for the install prompt to fire).
const SHELL_PAGES = [
    '/login/',
    '/calendar/',
];

self.addEventListener('install', function(event) {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_VERSION).then(cache =>
            cache.addAll([...STATIC_ASSETS, ...SHELL_PAGES])
        )
    );
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_VERSION).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', function(event) {
    const url = new URL(event.request.url);

    // Only handle same-origin requests
    if (url.origin !== self.location.origin) return;

    // Static assets: cache-first
    if (STATIC_ASSETS.some(a => url.pathname === a)) {
        event.respondWith(
            caches.match(event.request).then(r => r || fetch(event.request))
        );
        return;
    }

    // Navigation requests: network-first with shell-page fallback
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() =>
                caches.match(event.request).then(r =>
                    r || caches.match('/login/')
                )
            )
        );
    }
});
"""
    response = HttpResponse(sw_content, content_type='application/javascript')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


# -------------------- CALENDAR --------------------

@login_required
def calendar_view(request):
    is_staff_role = False
    export_enabled = True  # superusers always can export
    if hasattr(request.user, 'profile'):
        is_staff_role = request.user.profile.is_staff2
        if not request.user.is_superuser:
            export_enabled = request.user.profile.export_enabled
    return render(request, 'booking/calendar.html', {
        'is_staff2': is_staff_role,
        'export_enabled': export_enabled,
    })


@login_required
def booking_api(request):
    from django.utils import timezone
    auditorium = get_auditorium_for_user(request.user)
    bookings = Booking.objects.filter(auditorium=auditorium)
    events = []
    is_staff_role = False
    if hasattr(request.user, 'profile'):
        is_staff_role = request.user.profile.is_staff2

    for booking in bookings:
        # Ensure times are in the correct timezone
        start_time = timezone.localtime(booking.start_time)
        end_time = timezone.localtime(booking.end_time)
        
        # Determine shift (Day: 9 AM - 4 PM, Night: 5 PM - 9 PM)
        start_hour = start_time.hour
        end_hour = end_time.hour
        
        is_start_day = 9 <= start_hour < 16
        is_start_night = 17 <= start_hour < 21
        
        # Check if it's a day shift (9 AM - 4 PM)
        if 9 <= start_hour < 16 and 9 <= end_hour <= 16:
            shift = 'day'
        # Check if it's a night shift (5 PM - 9 PM)
        elif 17 <= start_hour < 21 and 17 <= end_hour <= 21:
            shift = 'night'
        else:
            shift = 'overlap'
        
        # Clamp display end to 23:59 of the START day so FullCalendar
        # treats it as a single-day event (actual DB data is untouched).
        display_end = end_time
        if end_time.date() > start_time.date():
            display_end = start_time.replace(hour=23, minute=59, second=59, microsecond=0)
        
        # Use display_end for the time label so we show "6 PM - 11:59 PM"
        # instead of the confusing "6 PM - 6 AM" on the calendar cell.
        time_str = f"{start_time.strftime('%I:%M %p').lstrip('0').replace(' 0', ' ')} - {display_end.strftime('%I:%M %p').lstrip('0').replace(' 0', ' ')}"
        
        if is_staff_role:
            # Hide personal details for auditorium staff
            events.append({
                'id': booking.pk,
                'title': 'BOOKED',
                'start': start_time.isoformat(),
                'end': display_end.isoformat(),
                'extendedProps': {
                    'shift': shift,
                    'timing': time_str
                }
            })
        else:
            events.append({
                'id': booking.pk,
                'title': booking.title,
                'start': start_time.isoformat(),
                'end': display_end.isoformat(),
                'contact_person': booking.contact_person,
                'mobile_number': booking.mobile_number,
                'total_amount': str(booking.total_amount),
                'advance_received': str(booking.advance_received),
                'pending_amount': str(booking.pending_amount),
                'payment_pending': booking.payment_pending,
                'created_by': booking.created_by.username,
                'created_by_id': booking.created_by.pk,
                'created_at': booking.created_at.strftime('%b %d, %Y %I:%M %p'),
                'url': f'/bookings/{booking.pk}/edit/',
                'extendedProps': {
                    'shift': shift,
                    'contact': booking.contact_person,
                    'mobile': booking.mobile_number,
                    'timing': time_str,
                    'total_amount': str(booking.total_amount),
                    'advance_received': str(booking.advance_received),
                    'pending_amount': str(booking.pending_amount),
                    'payment_pending': booking.payment_pending,
                    'created_by_id': booking.created_by.pk,
                }
            })
    return JsonResponse(events, safe=False)


@login_required
def check_conflict(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    if not start or not end:
        return JsonResponse({'conflict': False})

    # Check if requested time is in the past
    from django.utils.dateparse import parse_datetime
    requested_start = parse_datetime(start)
    if requested_start and timezone.is_naive(requested_start):
        requested_start = timezone.make_aware(requested_start)
    
    if requested_start and requested_start < timezone.now():
        return JsonResponse({
            'conflict': True, 
            'is_past': True,
            'message': 'Cannot book time in the past.'
        })

    exclude_id = request.GET.get('exclude_id')
    
    auditorium = get_auditorium_for_user(request.user)
    conflicts = Booking.objects.filter(auditorium=auditorium).filter(
        Q(start_time__lt=end, end_time__gt=start)
    )
    
    if exclude_id:
        conflicts = conflicts.exclude(pk=exclude_id)
        
    conflicts = conflicts.values('title', 'start_time', 'end_time')
    
    conflict_list = []
    for c in conflicts:
        conflict_list.append({
            'title': c['title'],
            'start': c['start_time'].strftime('%I:%M %p'),
            'end': c['end_time'].strftime('%I:%M %p')
        })
        
    return JsonResponse({
        'conflict': len(conflict_list) > 0,
        'conflicts': conflict_list
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_admin_status(request, pk):
    auditorium = get_auditorium_for_user(request.user)
    user = get_object_or_404(User, pk=pk, profile__auditorium=auditorium)
    if user != request.user:
        user.is_active = not user.is_active
        user.save()
    return JsonResponse({'status': 'success', 'is_active': user.is_active})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_booking_status(request, pk):
    auditorium = get_auditorium_for_user(request.user)
    user = get_object_or_404(User, pk=pk, profile__auditorium=auditorium)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.is_bookable = not profile.is_bookable
    profile.save()
    return JsonResponse({'status': 'success', 'is_bookable': profile.is_bookable})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_staff_status(request, pk):
    auditorium = get_auditorium_for_user(request.user)
    user = get_object_or_404(User, pk=pk, profile__auditorium=auditorium)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.is_staff2 = not profile.is_staff2
    profile.save()
    return JsonResponse({'status': 'success', 'is_staff2': profile.is_staff2})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_expense_status(request, pk):
    auditorium = get_auditorium_for_user(request.user)
    user = get_object_or_404(User, pk=pk, profile__auditorium=auditorium)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.expense_enabled = not profile.expense_enabled
    profile.save()
    return JsonResponse({'status': 'success', 'expense_enabled': profile.expense_enabled})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_export_status(request, pk):
    auditorium = get_auditorium_for_user(request.user)
    user = get_object_or_404(User, pk=pk, profile__auditorium=auditorium)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.export_enabled = not profile.export_enabled
    profile.save()
    return JsonResponse({'status': 'success', 'export_enabled': profile.export_enabled})


@login_required
@csrf_exempt
def toggle_payment_status(request, pk):
    deny = _deny_staff2(request)
    if deny:
        return deny
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=400)

    try:
        booking = get_object_or_404(Booking, pk=pk)

        # Only the creator or superuser can mark as paid
        if not request.user.is_superuser and booking.created_by != request.user:
            return JsonResponse({'status': 'error', 'message': 'You can only mark your own bookings as paid.'}, status=403)

        # Mark as paid by setting payment_pending to False and advance_received to total_amount
        booking.payment_pending = False
        booking.advance_received = booking.total_amount
        booking.save()
        
        # Get redirect_to from request body
        try:
            body = json.loads(request.body.decode('utf-8'))
            redirect_to = body.get('redirect_to', 'current')
        except:
            redirect_to = 'current'
        
        return JsonResponse({
            'status': 'success',
            'payment_pending': booking.payment_pending,
            'redirect_to': redirect_to,
            'message': 'Payment marked as complete successfully'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

from django.http import HttpResponse
from .utils import generate_bookings_pdf, generate_single_booking_pdf


def _deny_export(request):
    """Block non-superusers whose export_enabled is False."""
    if not request.user.is_superuser:
        try:
            if not request.user.profile.export_enabled:
                messages.error(request, 'Export access has been disabled for your account.')
                return redirect('calendar')
        except Exception:
            pass
    return None


@login_required
def export_bookings_pdf(request):
    """Export bookings list to PDF"""
    deny = _deny_staff2(request)
    if deny:
        return deny
    deny = _deny_export(request)
    if deny:
        return deny
    now = timezone.now()
    
    # Get filters from request
    selected_month = request.GET.get('month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    admin_id = request.GET.get('admin_id')
    query = request.GET.get('q', '').strip()
    
    auditorium = get_auditorium_for_user(request.user)
    # Base query scoped to this auditorium
    bookings = Booking.objects.filter(auditorium=auditorium).order_by('-start_time')
    
    # Apply filters
    filters = {}
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
            bookings = bookings.filter(start_time__year=year, start_time__month=month)
            filters['month'] = selected_month
        except (ValueError, AttributeError):
            pass
    else:
        if start_date:
            bookings = bookings.filter(start_time__date__gte=start_date)
            filters['start_date'] = start_date
        if end_date:
            bookings = bookings.filter(start_time__date__lte=end_date)
            filters['end_date'] = end_date
    
    if admin_id:
        bookings = bookings.filter(created_by_id=admin_id)
        try:
            admin = User.objects.get(pk=admin_id)
            filters['admin_name'] = admin.username
        except User.DoesNotExist:
            pass
    
    if query:
        bookings = bookings.filter(Q(title__icontains=query))
    
    # Generate PDF
    pdf = generate_bookings_pdf(bookings, filters, auditorium=auditorium)
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'bookings_report_{now.strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def export_bookings_excel(request):
    """Export bookings list to Excel"""
    deny = _deny_staff2(request)
    if deny:
        return deny
    deny = _deny_export(request)
    if deny:
        return deny
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return HttpResponse('openpyxl is not installed. Run: pip install openpyxl', status=500)

    now = timezone.now()

    # Reuse the same filters as the booking list / PDF export
    query = request.GET.get('q', '').strip()
    payment_status = request.GET.get('payment_status', '').strip()

    auditorium = get_auditorium_for_user(request.user)
    bookings = Booking.objects.filter(auditorium=auditorium).order_by('-created_at')

    if query:
        bookings = bookings.filter(
            Q(title__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(mobile_number__icontains=query)
        )

    if payment_status == 'paid':
        bookings = bookings.filter(payment_pending=False)
    elif payment_status == 'pending':
        bookings = bookings.filter(payment_pending=True)

    # Build workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Bookings'

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='14B8A6', end_color='14B8A6', fill_type='solid')
    center = Alignment(horizontal='center', vertical='center')

    headers = ['#', 'Serial No', 'Title', 'Contact Person', 'Mobile', 'Start Time', 'End Time', 'Total (₹)', 'Advance (₹)', 'Pending (₹)', 'Status', 'Created By']
    ws.append(headers)
    for col_num, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center

    for i, b in enumerate(bookings, 1):
        pending = b.total_amount - b.advance_received if b.total_amount else 0
        status = 'Paid' if not b.payment_pending else 'Pending'
        ws.append([
            i,
            b.serial_number or '',
            b.title,
            b.contact_person or '',
            b.mobile_number or '',
            b.start_time.strftime('%d-%m-%Y %H:%M') if b.start_time else '',
            b.end_time.strftime('%d-%m-%Y %H:%M') if b.end_time else '',
            float(b.total_amount) if b.total_amount else 0,
            float(b.advance_received) if b.advance_received else 0,
            float(pending),
            status,
            b.created_by.get_full_name() or b.created_by.username if b.created_by else '',
        ])

    # Auto-size columns
    for col in ws.columns:
        max_len = max((len(str(cell.value)) if cell.value else 0) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    # Stream response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'bookings_{now.strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@login_required
def export_single_booking_pdf(request, pk):
    """Export a single booking as PDF receipt"""
    deny = _deny_staff2(request)
    if deny:
        return deny
    deny = _deny_export(request)
    if deny:
        return deny
    booking = get_object_or_404(Booking, pk=pk)
    
    # Generate PDF
    pdf = generate_single_booking_pdf(booking)
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f'booking_{booking.pk}_{booking.title[:20].replace(" ", "_")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


# -------------------- EXPENSE TRACKER --------------------

@login_required
def expense_list(request):
    """List all expenses for this auditorium."""
    deny = _deny_staff2(request)
    if deny:
        return deny
    auditorium = get_auditorium_for_user(request.user)
    qs = Expense.objects.filter(auditorium=auditorium).select_related('submitted_by')

    # Category filter
    category_filter = request.GET.get('category', '')
    if category_filter:
        qs = qs.filter(category=category_filter)

    # Total spent across all entries in this auditorium
    total_spent = Expense.objects.filter(auditorium=auditorium).aggregate(s=Sum('amount'))['s'] or 0

    form = ExpenseForm()

    return render(request, 'booking/expense_list.html', {
        'expenses': qs,
        'form': form,
        'category_filter': category_filter,
        'category_choices': Expense.CATEGORY_CHOICES,
        'total_spent': total_spent,
    })


@login_required
def expense_create(request):
    """Log a new cash expense — blocked if admin has disabled expense for this user."""
    deny = _deny_staff2(request)
    if deny:
        return deny
    if request.method != 'POST':
        return redirect('expense_list')

    # Check if expense adding is enabled for this user (superusers always allowed)
    if not request.user.is_superuser:
        try:
            if not request.user.profile.expense_enabled:
                err = 'Expense logging has been disabled for your account.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': err})
                messages.error(request, err)
                return redirect('expense_list')
        except Exception:
            pass

    auditorium = get_auditorium_for_user(request.user)
    form = ExpenseForm(request.POST)
    if form.is_valid():
        expense = form.save(commit=False)
        expense.auditorium = auditorium
        expense.submitted_by = request.user
        expense.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': 'Expense added successfully.'})
        messages.success(request, 'Expense added successfully.')
    else:
        error_parts = []
        for field, errs in form.errors.items():
            for e in errs:
                error_parts.append(f"{field}: {e}" if field != '__all__' else str(e))
        msg = ' | '.join(error_parts)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': msg})
        messages.error(request, msg)

    return redirect('expense_list')


@login_required
def expense_delete(request, pk):
    """Delete an expense. Only the submitter or superuser can delete."""
    deny = _deny_staff2(request)
    if deny:
        return deny
    auditorium = get_auditorium_for_user(request.user)
    expense = get_object_or_404(Expense, pk=pk, auditorium=auditorium)

    # Only the creator or superuser can delete
    if not request.user.is_superuser and expense.submitted_by != request.user:
        messages.error(request, 'You can only delete expenses you created.')
        return redirect('expense_list')

    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted.')
    return redirect('expense_list')


# =====================================================================
# PLATFORM MASTER OWNER PORTAL VIEWS
# =====================================================================

@login_required
def owner_portal_dashboard(request):
    """Platform Master Owner Overview Portal."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    auditoriums = Auditorium.objects.select_related('owner').prefetch_related('staff_profiles__user', 'auditorium_bookings').all().order_by('-created_at')
    
    # Platform metrics
    total_auditoriums = auditoriums.count()
    active_auditoriums = auditoriums.filter(is_active=True).count()
    suspended_auditoriums = auditoriums.filter(is_active=False).count()
    total_monthly_revenue = auditoriums.filter(is_active=True).aggregate(total=Sum('monthly_fee'))['total'] or 0
    total_bookings_system_wide = Booking.objects.count()
    total_users_count = User.objects.count()
    create_form = PlatformAuditoriumCreateForm()

    context = {
        'auditoriums': auditoriums,
        'total_auditoriums': total_auditoriums,
        'active_auditoriums': active_auditoriums,
        'suspended_auditoriums': suspended_auditoriums,
        'total_monthly_revenue': total_monthly_revenue,
        'total_bookings_system_wide': total_bookings_system_wide,
        'total_users_count': total_users_count,
        'create_form': create_form,
    }
    return render(request, 'booking/owner_portal/dashboard.html', context)


@login_required
def owner_portal_auditorium_create(request):
    """Platform Master Owner creates an auditorium and assigns initial super admin."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    if request.method == 'POST':
        form = PlatformAuditoriumCreateForm(request.POST)
        if form.is_valid():
            auditorium, admin_user = form.save()
            messages.success(request, f'Auditorium "{auditorium.name}" and Super Admin "{admin_user.username}" created successfully!')
            return redirect('owner_portal_auditorium_detail', pk=auditorium.pk)
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}")
            return redirect('owner_portal_dashboard')

    return redirect('owner_portal_dashboard')


@login_required
def owner_portal_auditorium_detail(request, pk):
    """Detailed view for a single auditorium with credentials, staff, suspension toggles, and stats."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    auditorium = get_object_or_404(Auditorium.objects.select_related('owner'), pk=pk)
    
    # Fetch all users associated with this auditorium (owner + staff)
    staff_profiles = UserProfile.objects.filter(auditorium=auditorium).select_related('user')
    staff_users = [p.user for p in staff_profiles]
    if auditorium.owner and auditorium.owner not in staff_users:
        all_users = [auditorium.owner] + staff_users
    else:
        all_users = staff_users

    # Bookings & stats for this auditorium
    bookings_count = Booking.objects.filter(auditorium=auditorium).count()
    total_booking_revenue = Booking.objects.filter(auditorium=auditorium).aggregate(total=Sum('total_amount'))['total'] or 0
    expenses_count = Expense.objects.filter(auditorium=auditorium).count()
    total_expense_amount = Expense.objects.filter(auditorium=auditorium).aggregate(total=Sum('amount'))['total'] or 0

    recent_bookings = Booking.objects.filter(auditorium=auditorium).order_by('-start_time')[:10]

    context = {
        'auditorium': auditorium,
        'staff_profiles': staff_profiles,
        'all_users': all_users,
        'bookings_count': bookings_count,
        'total_booking_revenue': total_booking_revenue,
        'expenses_count': expenses_count,
        'total_expense_amount': total_expense_amount,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'booking/owner_portal/auditorium_detail.html', context)


@login_required
def owner_portal_auditorium_edit(request, pk):
    """Edit auditorium settings, billing, suspension status."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    auditorium = get_object_or_404(Auditorium, pk=pk)
    if request.method == 'POST':
        form = PlatformAuditoriumEditForm(request.POST, instance=auditorium)
        if form.is_valid():
            form.save()
            messages.success(request, f'Auditorium "{auditorium.name}" details updated successfully.')
            return redirect('owner_portal_auditorium_detail', pk=auditorium.pk)
    else:
        form = PlatformAuditoriumEditForm(instance=auditorium)

    return render(request, 'booking/owner_portal/auditorium_edit.html', {'form': form, 'auditorium': auditorium})


@login_required
def owner_portal_toggle_auditorium(request, pk):
    """Toggle active/suspended status for an entire auditorium."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    auditorium = get_object_or_404(Auditorium, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('suspension_reason', '').strip()
        auditorium.is_active = not auditorium.is_active
        if not auditorium.is_active:
            auditorium.suspension_reason = reason or "Monthly payment overdue / Administrative suspension"
        else:
            auditorium.suspension_reason = ""
        auditorium.save()

        status_str = "Activated" if auditorium.is_active else "Suspended & Locked"
        messages.success(request, f'Auditorium "{auditorium.name}" is now {status_str}.')

    return redirect(request.META.get('HTTP_REFERER') or 'owner_portal_dashboard')


@login_required
def owner_portal_toggle_user(request, user_id):
    """Master owner can activate or block any individual user (owner or staff) from logging in."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot deactivate your own master account.')
        return redirect(request.META.get('HTTP_REFERER') or 'owner_portal_dashboard')

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()
        status_text = "Activated" if target_user.is_active else "Blocked / Deactivated"
        messages.success(request, f'User "{target_user.username}" has been {status_text}.')

    return redirect(request.META.get('HTTP_REFERER') or 'owner_portal_dashboard')


@login_required
def owner_portal_reset_password(request, user_id):
    """Master owner can set a new password for any auditorium super admin or staff."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    target_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        if len(new_password) < 4:
            messages.error(request, 'Password must be at least 4 characters.')
        else:
            target_user.set_password(new_password)
            target_user.save()
            profile, _ = UserProfile.objects.get_or_create(user=target_user)
            profile.raw_password = new_password
            profile.save()
            messages.success(request, f'Password successfully changed for user "{target_user.username}".')

    return redirect(request.META.get('HTTP_REFERER') or 'owner_portal_dashboard')


@login_required
def owner_portal_auditorium_delete(request, pk):
    """Delete an auditorium and completely cascade delete all its staff users, bookings, expenses, and data."""
    deny = _deny_non_platform_owner(request)
    if deny:
        return deny

    auditorium = get_object_or_404(Auditorium, pk=pk)
    if request.method == 'POST':
        aud_name = auditorium.name
        
        # Collect all users to delete: owner + all staff linked to this auditorium
        staff_users = list(User.objects.filter(profile__auditorium=auditorium))
        owner_user = auditorium.owner

        # Explicitly delete associated bookings and expenses
        Booking.objects.filter(auditorium=auditorium).delete()
        Expense.objects.filter(auditorium=auditorium).delete()

        # Delete the auditorium (cascades related models)
        auditorium.delete()

        # Delete staff users (excluding platform owner 'owner')
        for staff in staff_users:
            if staff.username != 'owner':
                staff.delete()

        # Delete owner user if not platform owner 'owner'
        if owner_user and owner_user.username != 'owner':
            owner_user.delete()

        messages.success(request, f'Auditorium "{aud_name}" and all corresponding users and data have been permanently deleted.')
        return redirect('owner_portal_dashboard')

    return redirect('owner_portal_dashboard')
