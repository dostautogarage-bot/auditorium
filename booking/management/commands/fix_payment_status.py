from django.core.management.base import BaseCommand
from booking.models import Booking


class Command(BaseCommand):
    help = 'Fix payment status for existing bookings where advance equals total'

    def handle(self, *args, **kwargs):
        bookings = Booking.objects.all()
        fixed_count = 0
        
        for booking in bookings:
            old_status = booking.payment_pending
            
            # Apply the same logic as in model's save method
            if booking.advance_received >= booking.total_amount and booking.total_amount > 0:
                booking.payment_pending = False
            elif booking.advance_received < booking.total_amount:
                booking.payment_pending = True
            
            # Only save if status changed
            if old_status != booking.payment_pending:
                booking.save()
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Fixed booking #{booking.pk}: {booking.title} - '
                        f'Total: Rs.{booking.total_amount}, Paid: Rs.{booking.advance_received} - '
                        f'Status: {"Fully Paid" if not booking.payment_pending else "Pending"}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal bookings fixed: {fixed_count}')
        )

# Made with Bob
