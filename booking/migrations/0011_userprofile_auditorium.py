import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0010_simplify_expense'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='auditorium',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='staff_profiles',
                to='booking.auditorium',
            ),
        ),
    ]
