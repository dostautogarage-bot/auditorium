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

class Booking(models.Model):
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
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
                
            if overlapping.exists():
                raise ValidationError("This time slot is already booked. Please select another duration.")

    def save(self, *args, **kwargs):
        self.clean()
        
        # Auto-generate serial number for new bookings
        if not self.serial_number:
            last_booking = Booking.objects.order_by('-serial_number').first()
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
    is_bookable = models.BooleanField(default=True, help_text="Whether this admin can create bookings. If disabled, they can only view calendar in read-only mode.")
    is_auditorium_staff = models.BooleanField(default=False, help_text="Auditorium staff have minimum privileges and cannot see booking details.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Bookable: {self.is_bookable}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created"""
    if created and instance.is_staff:
        UserProfile.objects.get_or_create(user=instance, defaults={'is_bookable': True})


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved"""
    if instance.is_staff:
        if not hasattr(instance, 'profile'):
            UserProfile.objects.create(user=instance, is_bookable=True)
