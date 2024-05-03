# Generated by Django 5.0.1 on 2024-03-03 00:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0034_alter_availabletime_giver'),
    ]

    operations = [
        migrations.AlterField(
            model_name='availabletime',
            name='giver',
            field=models.ForeignKey(default='3', on_delete=django.db.models.deletion.CASCADE, related_name='available_times', to='myapp.giver'),
        ),
    ]