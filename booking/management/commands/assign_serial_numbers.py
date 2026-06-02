from django.core.management.base import BaseCommand
from booking.models import Booking


class Command(BaseCommand):
    help = 'Assign serial numbers to existing bookings'

    def handle(self, *args, **kwargs):
        bookings = Booking.objects.filter(serial_number__isnull=True).order_by('created_at')
        
        if not bookings.exists():
            self.stdout.write(self.style.SUCCESS('All bookings already have serial numbers!'))
            return
        
        # Get the last serial number
        last_booking = Booking.objects.filter(serial_number__isnull=False).order_by('-serial_number').first()
        next_serial = (last_booking.serial_number + 1) if last_booking and last_booking.serial_number else 1
        
        count = 0
        for booking in bookings:
            booking.serial_number = next_serial
            booking.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Assigned serial #{next_serial} to booking: {booking.title}'
                )
            )
            next_serial += 1
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal bookings assigned serial numbers: {count}')
        )

# Made with Bob
