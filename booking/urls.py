from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.dashboard, name='dashboard'),

    # Dashboard (Home)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Admin Management (Super Admin only typically, or as per views logic)
    path('admins/', views.admin_list, name='admin_list'),
    path('admins/create/', views.admin_create, name='admin_create'),
    path('admins/<int:pk>/edit/', views.admin_edit, name='admin_edit'),
    path('admins/<int:pk>/delete/', views.admin_delete, name='admin_delete'),
    path('payment-report/', views.payment_report, name='payment_report'),
    
    # Booking Management
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/create/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/edit/', views.booking_edit, name='booking_edit'),
    path('bookings/<int:pk>/delete/', views.booking_delete, name='booking_delete'),
    
    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/bookings/', views.booking_api, name='booking_api'),
    path('api/check-conflict/', views.check_conflict, name='check_conflict'),
    
    # PWA
    path('manifest.json', views.manifest_json, name='manifest_json'),
    path('sw.js', views.sw_js, name='sw_js'),
    path('api/toggle-admin/<int:pk>/', views.toggle_admin_status, name='toggle_admin_status'),
    path('api/toggle-booking/<int:pk>/', views.toggle_booking_status, name='toggle_booking_status'),
    path('api/toggle-staff/<int:pk>/', views.toggle_staff_status, name='toggle_staff_status'),
]
