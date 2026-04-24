from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import Booking
from .forms import AdminCreationForm, AdminEditForm, BookingForm

User = get_user_model()

# -------------------- PUBLIC HOME --------------------
def home(request):
    """Public landing page / advertisement page"""
    return render(request, 'booking/home.html')

# -------------------- DASHBOARD --------------------
@login_required
def dashboard(request):
    now = timezone.now()
    
    # Stats
    total_this_month = Booking.objects.filter(start_time__month=now.month, start_time__year=now.year).count()
    my_bookings_count = Booking.objects.filter(created_by=request.user).count()
    total_admins = User.objects.filter(is_staff=True).count()
    total_bookings = Booking.objects.count()
    
    # Recent bookings
    recent_bookings = Booking.objects.all().order_by('-start_time')[:10]
    
    return render(request, 'booking/dashboard.html', {
        'stats': {
            'month_total': total_this_month,
            'my_total': my_bookings_count,
            'admin_total': total_admins,
            'total_life': total_bookings
        },
        'recent_bookings': recent_bookings
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
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            
            # Prevent Past Bookings
            if booking.start_time < timezone.now():
                messages.error(request, 'Cannot create a booking in the past!')
                return redirect(request.META.get('HTTP_REFERER', 'calendar'))

            # Backend Conflict Check
            conflicts = Booking.objects.filter(
                Q(start_time__lt=booking.end_time, end_time__gt=booking.start_time)
            )
            if conflicts.exists():
                messages.error(request, 'Conflict detected! This slot is already partially or fully booked.')
                return redirect(request.META.get('HTTP_REFERER', 'calendar'))

            booking.created_by = request.user
            booking.save()
            messages.success(request, 'Booking successfully created.')
            return redirect(request.META.get('HTTP_REFERER', 'booking_list'))
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
    booking = get_object_or_404(Booking, pk=pk)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            new_booking = form.save(commit=False)
            if new_booking.start_time < timezone.now():
                messages.error(request, 'Cannot set a booking to a past time!')
                return redirect('booking_list')
            new_booking.save()
            messages.success(request, 'Booking successfully updated.')
            return redirect('booking_list')
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


# -------------------- PWA --------------------

def manifest_json(request):
    manifest = {
        "name": "Auditorium Booking System",
        "short_name": "Auditorium",
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
    return render(request, 'booking/calendar.html')


@login_required
def booking_api(request):
    from django.utils import timezone
    bookings = Booking.objects.all()
    events = []
    for booking in bookings:
        # Ensure times are in the correct timezone
        start_time = timezone.localtime(booking.start_time)
        end_time = timezone.localtime(booking.end_time)
        events.append({
            'id': booking.pk,
            'title': booking.title,
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'contact_person': booking.contact_person,
            'mobile_number': booking.mobile_number,
            'created_by': booking.created_by.username,
            'created_at': booking.created_at.strftime('%b %d, %Y %I:%M %p'),
            'url': f'/bookings/{booking.pk}/edit/'
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
