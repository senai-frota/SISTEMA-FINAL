from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('veiculos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VeiculoBackup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('veiculo_original_id', models.PositiveIntegerField(verbose_name='ID do veículo original')),
                ('placa', models.CharField(max_length=10, verbose_name='Placa')),
                ('modelo', models.CharField(max_length=100, verbose_name='Modelo')),
                ('marca', models.CharField(max_length=100, verbose_name='Marca')),
                ('ano', models.PositiveIntegerField(verbose_name='Ano')),
                ('cor', models.CharField(max_length=50, verbose_name='Cor')),
                ('tipo_combustivel', models.CharField(max_length=20, verbose_name='Combustível')),
                ('capacidade', models.PositiveIntegerField(verbose_name='Capacidade de passageiros')),
                ('renavam', models.CharField(blank=True, max_length=20, null=True, verbose_name='RENAVAM')),
                ('chassi', models.CharField(blank=True, max_length=30, null=True, verbose_name='Chassi')),
                ('observacoes', models.TextField(blank=True, null=True, verbose_name='Observações')),
                ('foto', models.CharField(blank=True, max_length=500, null=True, verbose_name='Foto do veículo (caminho/URL)')),
                ('status_no_momento', models.CharField(max_length=20, verbose_name='Status no momento da remoção')),
                ('criado_em_original', models.DateTimeField(verbose_name='Cadastrado em (original)')),
                ('removido_em', models.DateTimeField(auto_now_add=True, verbose_name='Removido em')),
                ('removido_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='veiculos_removidos', to=settings.AUTH_USER_MODEL, verbose_name='Removido por')),
            ],
            options={
                'verbose_name': 'Backup de Veículo',
                'verbose_name_plural': 'Backups de Veículos',
                'ordering': ['-removido_em'],
            },
        ),
    ]
