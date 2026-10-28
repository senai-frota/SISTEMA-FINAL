import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TermoResponsabilidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entidade', models.CharField(choices=[('FIBRA', 'FIBRA'), ('SESI', 'SESI'), ('SENAI', 'SENAI'), ('IEL', 'IEL')], max_length=10, verbose_name='Entidade')),
                ('cpf', models.CharField(max_length=14, verbose_name='CPF')),
                ('cnh', models.CharField(max_length=20, verbose_name='CNH')),
                ('data_solicitacao', models.DateField(verbose_name='Data da solicitação')),
                ('arquivo_pdf', models.FileField(blank=True, null=True, upload_to='termos/%Y/%m/', verbose_name='Termo gerado (PDF)')),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('aprovado', 'Aprovado'), ('rejeitado', 'Rejeitado')], default='pendente', max_length=10, verbose_name='Status')),
                ('data_decisao', models.DateTimeField(blank=True, null=True, verbose_name='Data da decisão')),
                ('observacao_admin', models.TextField(blank=True, null=True, verbose_name='Observação do administrador')),
                ('data_validade', models.DateField(blank=True, null=True, verbose_name='Válido até')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('admin_aprovador', models.ForeignKey(blank=True, limit_choices_to={'is_admin': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='termos_decididos', to=settings.AUTH_USER_MODEL, verbose_name='Administrador responsável')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='termos', to=settings.AUTH_USER_MODEL, verbose_name='Empregado')),
            ],
            options={
                'verbose_name': 'Termo de Responsabilidade',
                'verbose_name_plural': 'Termos de Responsabilidade',
                'ordering': ['-criado_em'],
            },
        ),
    ]
