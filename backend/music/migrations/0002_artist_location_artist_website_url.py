# Generated by Django 4.2.20 on 2025-04-09 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='artist',
            name='location',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='artist',
            name='website_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
