from django.db import migrations

COMMON_GENRES = [
    "Electronic", "Rock", "Pop", "Hip Hop", "Jazz", "Classical", "Blues", 
    "Country", "Folk", "Reggae", "R&B", "Soul", "Metal", "Punk", 
    "Alternative", "Indie", "Dance", "House", "Techno", "Trance",
    "Ambient", "Soundtrack", "World Music", "Latin", "K-Pop", "J-Pop",
    "Experimental", "Lo-fi", "Synthwave", "Funk", "Gospel", "Afrobeat"
]

def seed_genres(apps, schema_editor):
    Genre = apps.get_model('music', 'Genre')
    for genre_name in COMMON_GENRES:
        Genre.objects.get_or_create(name=genre_name)

def unseed_genres(apps, schema_editor):
    Genre = apps.get_model('music', 'Genre')
    Genre.objects.filter(name__in=COMMON_GENRES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0004_remove_release_genre_remove_track_genre_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_genres, reverse_code=unseed_genres),
    ]
