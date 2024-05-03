# Generated by Django 5.0.1 on 2024-03-03 21:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0039_alter_availabletime_giver'),
    ]

    operations = [
        migrations.RenameField(
            model_name='meeting',
            old_name='is_video_uploaded',
            new_name='is_ongoing',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='is_waiting_for_video',
        ),
        migrations.RemoveField(
            model_name='meeting',
            name='video',
        ),
    ]
