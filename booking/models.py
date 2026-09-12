"""
Auditorium Booking System - Models
Generated and maintained by Bob
A highly skilled software engineer
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver


class Auditorium(models.Model):
    """Represents a single auditorium / tenant in the multi-tenant system."""
    name = models.CharField(max_length=200)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_auditorium'
    )
    is_active = models.BooleanField(default=True, help_text="Status of auditorium. If inactive, all its users are blocked from access.")
    suspension_reason = models.CharField(max_length=255, blank=True, default="", help_text="Reason for suspension (e.g. Non-payment of monthly subscription)")
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Monthly platform subscription charge")
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    notes = models.TextField(blank=True, default="", help_text="Owner/Platform notes for this auditorium")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_users_count(self):
        """Returns the exact count of unique users (owner + staff) belonging to this auditorium."""
        user_ids = set()
        if self.owner_id:
            user_ids.add(self.owner_id)
        for profile in self.staff_profiles.all():
            if profile.user_id:
                user_ids.add(profile.user_id)
        return len(user_ids)


class Booking(models.Model):
    auditorium = models.ForeignKey(
        Auditorium,
        on_delete=models.CASCADE,
        related_name='auditorium_bookings',
        null=True,
        blank=True,
    )
    serial_number = models.PositiveIntegerField(unique=True, null=True, blank=True, help_text="Auto-generated serial number")
    title = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, default='')
    mobile_number = models.CharField(max_length=20, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total booking amount")
    advance_received = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Advance payment received")
    payment_pending = models.BooleanField(default=True, help_text="Whether payment is still pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.start_time} - {self.end_time})"
    
    @property
    def pending_amount(self):
        """Calculate pending amount (total - advance)"""
        return self.total_amount - self.advance_received

    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time.")

            overlapping = Booking.objects.filter(
                auditorium=self.auditorium,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)

            if overlapping.exists():
                raise ValidationError("This time slot is already booked. Please select another duration.")

    def save(self, *args, **kwargs):
        self.clean()
        
        # Auto-generate serial number for new bookings (scoped per auditorium)
        if not self.serial_number:
            last_booking = Booking.objects.filter(auditorium=self.auditorium).order_by('-serial_number').first()
            self.serial_number = (last_booking.serial_number + 1) if last_booking and last_booking.serial_number else 1
        
        # Auto-mark as fully paid if advance equals or exceeds total amount
        if self.advance_received >= self.total_amount and self.total_amount > 0:
            self.payment_pending = False
        elif self.advance_received < self.total_amount:
            self.payment_pending = True
            
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """Extended user profile for additional permissions"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    auditorium = models.ForeignKey(
        'Auditorium',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='staff_profiles',
    )
    is_bookable = models.BooleanField(default=False, help_text="Whether this admin can create bookings.")
    is_staff2 = models.BooleanField(default=False, help_text="Staff2 role: minimum privileges, cannot see booking details.")
    expense_enabled = models.BooleanField(default=False, help_text="Whether this user can add expenses.")
    export_enabled = models.BooleanField(default=False, help_text="Whether this user can export bookings.")
    raw_password = models.CharField(max_length=128, blank=True, default='', help_text="Saved for platform owner reference")
    is_platform_owner = models.BooleanField(default=False, help_text="Designates this user as the Master Application/Platform Owner.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Bookable: {self.is_bookable}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created"""
    if created and instance.is_staff:
        UserProfile.objects.get_or_create(user=instance, defaults={
            'is_bookable': False,
            'expense_enabled': False,
            'export_enabled': False,
        })


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    if instance.is_staff:
        if not hasattr(instance, 'profile'):
            UserProfile.objects.create(user=instance, is_bookable=False, expense_enabled=False, export_enabled=False)


class Expense(models.Model):
    """A cash spend entry logged by any admin/staff."""

    CATEGORY_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('salary', 'Salary'),
        ('other', 'Other'),
    ]

    auditorium = models.ForeignKey(
        Auditorium,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(blank=True)
    date = models.DateField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} — ₹{self.amount} by {self.submitted_by}"


def get_auditorium_for_user(user):
    """Return the Auditorium that the given user belongs to (as owner or staff member)."""
    # Auditorium owner
    try:
        return user.owned_auditorium
    except Auditorium.DoesNotExist:
        pass
    # Staff member — look up via UserProfile.auditorium
    try:
        return user.profile.auditorium
    except Exception:
        pass
    return None
