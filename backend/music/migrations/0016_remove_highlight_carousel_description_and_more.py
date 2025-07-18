# Generated by Django 4.2.21 on 2025-05-30 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0015_alter_highlight_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='highlight',
            name='carousel_description',
        ),
        migrations.RemoveField(
            model_name='highlight',
            name='carousel_subtitle',
        ),
        migrations.RemoveField(
            model_name='highlight',
            name='carousel_title',
        ),
        migrations.AddField(
            model_name='highlight',
            name='description',
            field=models.TextField(blank=True, help_text='Optional: Description for the highlight.'),
        ),
        migrations.AddField(
            model_name='highlight',
            name='subtitle',
            field=models.CharField(blank=True, help_text='Optional: Subtitle for the highlight.', max_length=200),
        ),
        migrations.AddField(
            model_name='highlight',
            name='title',
            field=models.CharField(blank=True, help_text='Optional: Highlight title. Defaults to release title.', max_length=200),
        ),
    ]
