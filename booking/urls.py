"""
Auditorium Booking System - URL Configuration
Generated and maintained by Bob
A highly skilled software engineer
"""
from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Post-login redirect
    path('after-login/', views.after_login, name='after_login'),

    # Root redirects straight to login
    path('', RedirectView.as_view(url='/login/', permanent=False), name='home'),
    path('register/', views.register, name='register'),

    # Dashboard (Home)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Admin Management (Super Admin only typically, or as per views logic)
    path('admins/', views.admin_list, name='admin_list'),
    path('admins/create/', views.admin_create, name='admin_create'),
    path('admins/<int:pk>/edit/', views.admin_edit, name='admin_edit'),
    path('admins/<int:pk>/delete/', views.admin_delete, name='admin_delete'),
    path('admins/<int:pk>/reset-password/', views.reset_staff_password, name='reset_staff_password'),
    path('payment-report/', views.payment_report, name='payment_report'),
    
    # Booking Management
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/create/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/edit/', views.booking_edit, name='booking_edit'),
    path('bookings/<int:pk>/delete/', views.booking_delete, name='booking_delete'),
    path('bookings/export/pdf/', views.export_bookings_pdf, name='export_bookings_pdf'),
    path('bookings/export/excel/', views.export_bookings_excel, name='export_bookings_excel'),
    path('bookings/<int:pk>/export/pdf/', views.export_single_booking_pdf, name='export_single_booking_pdf'),
    
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
    path('api/toggle-payment/<int:pk>/', views.toggle_payment_status, name='toggle_payment_status'),

    # Expense Tracker
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('api/toggle-expense/<int:pk>/', views.toggle_expense_status, name='toggle_expense_status'),
    path('api/toggle-export/<int:pk>/', views.toggle_export_status, name='toggle_export_status'),

    # Master Platform Owner Portal
    path('owner-portal/', views.owner_portal_dashboard, name='owner_portal_dashboard'),
    path('owner-portal/auditoriums/create/', views.owner_portal_auditorium_create, name='owner_portal_auditorium_create'),
    path('owner-portal/auditoriums/<int:pk>/', views.owner_portal_auditorium_detail, name='owner_portal_auditorium_detail'),
    path('owner-portal/auditoriums/<int:pk>/edit/', views.owner_portal_auditorium_edit, name='owner_portal_auditorium_edit'),
    path('owner-portal/auditoriums/<int:pk>/toggle/', views.owner_portal_toggle_auditorium, name='owner_portal_toggle_auditorium'),
    path('owner-portal/auditoriums/<int:pk>/delete/', views.owner_portal_auditorium_delete, name='owner_portal_auditorium_delete'),
    path('owner-portal/users/<int:user_id>/toggle/', views.owner_portal_toggle_user, name='owner_portal_toggle_user'),
    path('owner-portal/users/<int:user_id>/reset-password/', views.owner_portal_reset_password, name='owner_portal_reset_password'),
]
