from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_message_original_attachment_filename'), # Ensure this points to your PREVIOUS migration file for the chat app
    ]

    operations = [
        migrations.RenameField(
            model_name='message',
            old_name='sender',      # The name of the field in the database
            new_name='sender_user',  # The name of the field in your models.py
        ),
    ]