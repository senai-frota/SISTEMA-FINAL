from django.db import migrations, models
import django.db.models.deletion


def copiar_foto_existente(apps, schema_editor):
    Veiculo = apps.get_model('veiculos', 'Veiculo')
    FotoVeiculo = apps.get_model('veiculos', 'FotoVeiculo')
    ja_tem = set(FotoVeiculo.objects.values_list('veiculo_id', flat=True))
    for veiculo in Veiculo.objects.exclude(foto='').exclude(foto__isnull=True):
        if veiculo.id in ja_tem:
            continue
        FotoVeiculo.objects.create(
            veiculo=veiculo,
            arquivo=veiculo.foto,
            ordem=0,
        )


def reverter_copia(apps, schema_editor):
    FotoVeiculo = apps.get_model('veiculos', 'FotoVeiculo')
    FotoVeiculo.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('veiculos', '0004_recreate_veiculobackup'),
    ]

    operations = [
        migrations.CreateModel(
            name='FotoVeiculo',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                )),
                ('arquivo', models.ImageField(upload_to='veiculos/', verbose_name='Foto')),
                ('ordem', models.PositiveSmallIntegerField(default=0, verbose_name='Ordem')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('veiculo', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fotos',
                    to='veiculos.veiculo',
                    verbose_name='Veículo',
                )),
            ],
            options={
                'verbose_name': 'Foto do veículo',
                'verbose_name_plural': 'Fotos do veículo',
                'ordering': ['ordem', 'id'],
            },
        ),
        migrations.RunPython(copiar_foto_existente, reverter_copia),
    ]
