from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Booking(models.Model):
    title = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, default='')
    mobile_number = models.CharField(max_length=20, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.start_time} - {self.end_time})"

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
        super().save(*args, **kwargs)
