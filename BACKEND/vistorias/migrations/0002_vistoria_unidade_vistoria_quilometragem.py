from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vistorias', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vistoria',
            name='unidade',
            field=models.CharField(
                blank=True,
                choices=[
                    ('taguatinga', 'SENAI Taguatinga'),
                    ('gama', 'SENAI Gama'),
                    ('sobradinho', 'SENAI Sobradinho'),
                    ('sig', 'SENAI SIG'),
                ],
                help_text='Unidade do SENAI onde o check-in/check-out está sendo realizado',
                max_length=20,
                null=True,
                verbose_name='Unidade',
            ),
        ),
        migrations.AddField(
            model_name='vistoria',
            name='quilometragem',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Km inicial do veículo (check-in) ou km final do veículo (check-out)',
                null=True,
                verbose_name='Quilometragem (km)',
            ),
        ),
    ]
