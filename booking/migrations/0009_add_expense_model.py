import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0008_seed_initial_auditorium'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('category', models.CharField(
                    choices=[
                        ('maintenance', 'Maintenance'),
                        ('utilities', 'Utilities'),
                        ('supplies', 'Supplies'),
                        ('salary', 'Salary'),
                        ('marketing', 'Marketing'),
                        ('other', 'Other'),
                    ],
                    default='other',
                    max_length=50,
                )),
                ('description', models.TextField(blank=True)),
                ('date', models.DateField()),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('allowed', 'Allowed'),
                        ('blocked', 'Blocked'),
                    ],
                    default='pending',
                    max_length=10,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('auditorium', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='expenses',
                    to='booking.auditorium',
                )),
                ('submitted_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='expenses',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_expenses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
