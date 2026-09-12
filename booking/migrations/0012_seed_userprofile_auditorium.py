"""
Data migration: assign every existing UserProfile that has no auditorium
to the first Auditorium (the one seeded from the original superuser).
"""
from django.db import migrations


def assign_profiles_to_auditorium(apps, schema_editor):
    Auditorium = apps.get_model('booking', 'Auditorium')
    UserProfile = apps.get_model('booking', 'UserProfile')

    auditorium = Auditorium.objects.order_by('created_at').first()
    if auditorium is None:
        return

    UserProfile.objects.filter(auditorium__isnull=True).update(auditorium=auditorium)


def reverse_migration(apps, schema_editor):
    UserProfile = apps.get_model('booking', 'UserProfile')
    UserProfile.objects.all().update(auditorium=None)


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0011_userprofile_auditorium'),
    ]

    operations = [
        migrations.RunPython(assign_profiles_to_auditorium, reverse_migration),
    ]
