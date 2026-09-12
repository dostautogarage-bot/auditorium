import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0006_booking_serial_number'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create the Auditorium table
        migrations.CreateModel(
            name='Auditorium',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='owned_auditorium',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        # 2. Add nullable FK on Booking (nullable so existing rows don't break)
        migrations.AddField(
            model_name='booking',
            name='auditorium',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='auditorium_bookings',
                to='booking.auditorium',
            ),
        ),
    ]
