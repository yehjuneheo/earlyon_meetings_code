# Generated by Django 5.0.1 on 2024-03-03 00:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0030_remove_giver_availability_availabletime_giver'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='availabletime',
            name='giver',
        ),
    ]
