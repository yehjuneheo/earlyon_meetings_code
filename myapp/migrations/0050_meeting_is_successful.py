# Generated by Django 5.0.1 on 2024-03-12 01:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0049_rename_is_ongoing_meeting_is_failed'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='is_successful',
            field=models.BooleanField(default=False),
        ),
    ]