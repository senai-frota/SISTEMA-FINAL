# Generated manually for optional geolocation fields on Vistoria

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vistorias', '0002_vistoria_unidade_vistoria_quilometragem'),
    ]

    operations = [
        migrations.AddField(
            model_name='vistoria',
            name='latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text='Latitude opcional do dispositivo no momento da vistoria.',
                max_digits=9,
                null=True,
                verbose_name='Latitude',
            ),
        ),
        migrations.AddField(
            model_name='vistoria',
            name='longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text='Longitude opcional do dispositivo no momento da vistoria.',
                max_digits=9,
                null=True,
                verbose_name='Longitude',
            ),
        ),
        migrations.AddField(
            model_name='vistoria',
            name='precisao_metros',
            field=models.FloatField(
                blank=True,
                help_text='Precisão opcional da geolocalização em metros.',
                null=True,
                verbose_name='Precisão (m)',
            ),
        ),
    ]
