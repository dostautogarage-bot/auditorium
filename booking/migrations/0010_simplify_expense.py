import django.db.models.deletion
from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0009_add_expense_model'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(model_name='expense', name='status'),
        migrations.RemoveField(model_name='expense', name='reviewed_by'),
    ]
