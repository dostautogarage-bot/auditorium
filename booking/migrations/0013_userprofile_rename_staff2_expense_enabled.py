from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0012_seed_userprofile_auditorium'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userprofile',
            old_name='is_auditorium_staff',
            new_name='is_staff2',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='expense_enabled',
            field=models.BooleanField(default=True, help_text='Whether this user can add expenses.'),
        ),
    ]
