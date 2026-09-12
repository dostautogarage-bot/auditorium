"""
Data migration: creates an Auditorium for the first/only superuser that
exists in the database and assigns all existing Booking rows to it.

This is safe to run against a live DB — it only INSERTs one Auditorium row
and UPDATEs the existing bookings' FK. The existing user's credentials,
bookings, and all other data are untouched.
"""
from django.db import migrations


def create_initial_auditorium(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Auditorium = apps.get_model('booking', 'Auditorium')
    Booking = apps.get_model('booking', 'Booking')

    # Find the first superuser (the existing owner of this app)
    superuser = User.objects.filter(is_superuser=True).order_by('date_joined').first()
    if superuser is None:
        # No superuser yet — nothing to migrate
        return

    # Create an Auditorium owned by the superuser using their username as the name
    auditorium, _ = Auditorium.objects.get_or_create(
        owner=superuser,
        defaults={'name': f"{superuser.username}'s Auditorium"},
    )

    # Assign all existing bookings that have no auditorium yet
    Booking.objects.filter(auditorium__isnull=True).update(auditorium=auditorium)


def reverse_migration(apps, schema_editor):
    # On reverse: just clear the FK; the Auditorium row will be dropped by
    # the schema migration reversal automatically.
    Booking = apps.get_model('booking', 'Booking')
    Booking.objects.all().update(auditorium=None)


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0007_add_auditorium_model'),
    ]

    operations = [
        migrations.RunPython(create_initial_auditorium, reverse_migration),
    ]
