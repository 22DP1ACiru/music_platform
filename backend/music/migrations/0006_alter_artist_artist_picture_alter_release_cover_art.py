from django.db import migrations, models
import music.models # Keep this for artist_pic_path and cover_art_path
from vaultwave.utils import validate_image_not_gif_utility # Import the validator from its new location


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0005_seed_initial_genres'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artist',
            name='artist_picture',
            field=models.ImageField(blank=True, null=True, upload_to=music.models.artist_pic_path, validators=[validate_image_not_gif_utility]),
        ),
        migrations.AlterField(
            model_name='release',
            name='cover_art',
            field=models.ImageField(blank=True, null=True, upload_to=music.models.cover_art_path, validators=[validate_image_not_gif_utility]),
        ),
    ]