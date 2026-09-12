from django.contrib import admin
from .models import Auditorium, Booking, Expense, UserProfile


@admin.register(Auditorium)
class AuditoriumAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at']
    search_fields = ['name', 'owner__username']
    readonly_fields = ['created_at']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'category', 'date', 'submitted_by', 'created_at']
    list_filter = ['category', 'date']
    search_fields = ['title', 'submitted_by__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'start_time', 'end_time', 'advance_received', 'created_at']
    list_filter = ['created_at', 'start_time', 'created_by']
    search_fields = ['title', 'contact_person', 'mobile_number']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Event Information', {'fields': ('title', 'contact_person', 'mobile_number')}),
        ('Booking Details', {'fields': ('created_by', 'start_time', 'end_time')}),
        ('Payment', {'fields': ('advance_received',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_bookable', 'created_at']
    list_filter = ['is_bookable', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
