# Generated migration to change ImageField to URLField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='hero_image',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='room',
            name='thumbnail_image',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]