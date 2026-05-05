from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import json
from .models import Booking, UserProfile
from .forms import AdminCreationForm, AdminEditForm, BookingForm

User = get_user_model()


# -------------------- DASHBOARD --------------------
@login_required
def dashboard(request):
    if not request.user.is_superuser:
        return redirect('calendar')
    
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
    
    # Base query for filtered metrics
    filtered_qs = Booking.objects.all()
    
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
    filtered_count = filtered_qs.count()
    
    # Fixed Stats (Contextual)
    month_total = Booking.objects.filter(start_time__month=now.month, start_time__year=now.year).count()
    my_total = Booking.objects.filter(created_by=request.user).count()
    admin_total = User.objects.filter(is_staff=True).count()
    total_life = Booking.objects.count()
    
    # Admin Breakdown
    admin_breakdown = User.objects.filter(is_staff=True).annotate(
        collected=Sum('bookings__advance_received', filter=Q(bookings__in=filtered_qs)),
        booking_count=Count('bookings', filter=Q(bookings__in=filtered_qs))
    ).filter(booking_count__gt=0).order_by('-collected')
    
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
    all_admins = User.objects.filter(is_staff=True).order_by('username')
    recent_bookings = filtered_qs.order_by('-start_time')[:10]
    
    return render(request, 'booking/dashboard.html', {
        'stats': {
            'month_total': month_total,
            'total_advance': total_advance,
            'my_total': my_total,
            'admin_total': admin_total,
            'total_life': total_life,
            'filtered_count': filtered_count
        },
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
    """List all admin users"""
    query = request.GET.get('q', '').strip()
    
    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    
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
    """Create a new admin user"""
    if request.method == 'POST':
        form = AdminCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Admin user "{form.cleaned_data.get("username")}" created successfully!')
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
    """Edit an admin user"""
    admin = get_object_or_404(User, pk=pk, is_staff=True)
    
    if request.method == 'POST':
        form = AdminEditForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            messages.success(request, f'Admin user "{admin.username}" updated successfully!')
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
    """Delete an admin user"""
    admin = get_object_or_404(User, pk=pk, is_staff=True)
    
    if admin.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('admin_list')
    
    if request.method == 'POST':
        username = admin.username
        admin.delete()
        messages.success(request, f'Admin user "{username}" deleted successfully!')
        return redirect('admin_list')
    
    return render(request, 'booking/admin_confirm_delete.html', {'admin': admin})


# -------------------- BOOKING MANAGEMENT --------------------

@login_required
def booking_list(request):
    now = timezone.now()
    
    query = request.GET.get('q', '').strip()
    bookings = Booking.objects.all().order_by('-start_time')
    
    # Stats
    total_this_month = Booking.objects.filter(start_time__month=now.month, start_time__year=now.year).count()
    my_bookings_count = Booking.objects.filter(created_by=request.user).count()
    total_admins = User.objects.filter(is_staff=True).count()

    if query:
        bookings = bookings.filter(
            Q(title__icontains=query)
        )
        
    per_page = int(request.GET.get('per_page', 100))
    if per_page not in [100, 200, 300, 500]:
        per_page = 100

    paginator = Paginator(bookings, per_page)
    page_number = request.GET.get('page')
    booking_page = paginator.get_page(page_number)
    
    return render(request, 'booking/booking_list.html', {
        'bookings': booking_page,
        'query': query,
        'per_page': per_page,
        'stats': {
            'month_total': total_this_month,
            'my_total': my_bookings_count,
            'admin_total': total_admins
        }
    })

@login_required
def booking_create(request):
    # Check if user is allowed to create bookings
    if request.user.is_staff and not request.user.is_superuser:
        try:
            profile = request.user.profile
            if profile.is_auditorium_staff or not profile.is_bookable:
                error_msg = 'You do not have permission to create bookings.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect(request.META.get('HTTP_REFERER', 'calendar'))
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            UserProfile.objects.create(user=request.user, is_bookable=True)
    
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

            # Backend Conflict Check
            conflicts = Booking.objects.filter(
                Q(start_time__lt=booking.end_time, end_time__gt=booking.start_time)
            )
            if conflicts.exists():
                error_msg = 'Conflict detected! This slot is already partially or fully booked.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('calendar')

            booking.created_by = request.user
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
    # Check if user is allowed to edit bookings
    if request.user.is_staff and not request.user.is_superuser:
        try:
            profile = request.user.profile
            if profile.is_auditorium_staff or not profile.is_bookable:
                error_msg = 'You do not have permission to edit bookings.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg})
                messages.error(request, error_msg)
                return redirect(request.META.get('HTTP_REFERER', 'calendar'))
        except UserProfile.DoesNotExist:
            pass
            
    booking = get_object_or_404(Booking, pk=pk)
    
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
    booking = get_object_or_404(Booking, pk=pk)
    
    if request.method == 'POST':
        booking.delete()
        messages.success(request, 'Booking deleted successfully.')
        return redirect('booking_list')
        
    return render(request, 'booking/booking_confirm_delete.html', {'booking': booking})


# -------------------- PAYMENT REPORT (SUPER ADMIN ONLY) --------------------

@login_required
@user_passes_test(lambda u: u.is_superuser)
def payment_report(request):
    """Payment report showing which admins received advance payments"""
    # Get all admins with their bookings and total advance received
    admins = User.objects.filter(is_staff=True).prefetch_related('bookings')
    
    admin_payment_data = []
    total_advance = 0
    
    for admin in admins:
        bookings_with_advance = admin.bookings.filter(advance_received__gt=0)
        advance_sum = bookings_with_advance.aggregate(total=Sum('advance_received'))['total'] or 0
        
        admin_payment_data.append({
            'admin': admin,
            'booking_count': admin.bookings.count(),
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
        "name": "ABC Auditorium Booking System",
        "short_name": "ABC Auditorium",
        "description": "Book auditoriums and manage bookings",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#FF5A00",
        "icons": [
            {
                "src": "/static/logo.png",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }
    return JsonResponse(manifest)


def sw_js(request):
    sw_content = """
self.addEventListener('install', function(event) {
    console.log('Service Worker installing.');
});

self.addEventListener('activate', function(event) {
    console.log('Service Worker activating.');
});

self.addEventListener('fetch', function(event) {
    // Basic caching can be added here
});
"""
    return HttpResponse(sw_content, content_type='application/javascript')


# -------------------- CALENDAR --------------------

@login_required
def calendar_view(request):
    is_staff_role = False
    if hasattr(request.user, 'profile'):
        is_staff_role = request.user.profile.is_auditorium_staff
    return render(request, 'booking/calendar.html', {'is_auditorium_staff': is_staff_role})


@login_required
def booking_api(request):
    from django.utils import timezone
    bookings = Booking.objects.all()
    events = []
    is_staff_role = False
    if hasattr(request.user, 'profile'):
        is_staff_role = request.user.profile.is_auditorium_staff

    for booking in bookings:
        # Ensure times are in the correct timezone
        start_time = timezone.localtime(booking.start_time)
        end_time = timezone.localtime(booking.end_time)
        
        # Determine shift (Day: 7 AM - 7 PM, Night: 7 PM - 7 AM)
        hour = start_time.hour
        shift = 'day' if 7 <= hour < 19 else 'night'
        
        time_str = f"{start_time.strftime('%I:%M %p').lstrip('0').replace(' 0', ' ')} - {end_time.strftime('%I:%M %p').lstrip('0').replace(' 0', ' ')}"
        if is_staff_role:
            # Hide personal details for auditorium staff
            events.append({
                'id': booking.pk,
                'title': 'BOOKED',
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
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
                'end': end_time.isoformat(),
                'contact_person': booking.contact_person,
                'mobile_number': booking.mobile_number,
                'advance_received': str(booking.advance_received),
                'created_by': booking.created_by.username,
                'created_at': booking.created_at.strftime('%b %d, %Y %I:%M %p'),
                'url': f'/bookings/{booking.pk}/edit/',
                'extendedProps': {
                    'shift': shift,
                    'contact': booking.contact_person,
                    'mobile': booking.mobile_number
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
    # The 'start' from request is usually ISO string or similar
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
    
    conflicts = Booking.objects.filter(
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
    user = get_object_or_404(User, pk=pk)
    if user != request.user: # Prevent self-deactivation
        user.is_active = not user.is_active
        user.save()
    return JsonResponse({'status': 'success', 'is_active': user.is_active})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_booking_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.is_bookable = not profile.is_bookable
    profile.save()
    return JsonResponse({'status': 'success', 'is_bookable': profile.is_bookable})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_staff_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.is_auditorium_staff = not profile.is_auditorium_staff
    profile.save()
    return JsonResponse({'status': 'success', 'is_auditorium_staff': profile.is_auditorium_staff})

def manifest_json(request):
    manifest = {
        "name": "ABC Auditorium",
        "short_name": "ABC Audit",
        "description": "Real-time ABC Auditorium booking schedule.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#FF7A00",
        "icons": [
            {
                "src": "/static/favicon.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/static/favicon.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JsonResponse(manifest)

def sw_js(request):
    sw_code = """
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('abc-audit-store').then((cache) => cache.addAll([
      '/',
      '/static/favicon.png',
    ])),
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => response || fetch(e.request)),
  );
});
"""
    return HttpResponse(sw_code, content_type='application/javascript')
