# Generated by Django 5.0.1 on 2024-03-20 02:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0055_giver_is_payout_setup'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='is_failed_by_giver',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='meeting',
            name='is_failed_by_receiver',
            field=models.BooleanField(default=False),
        ),
    ]
