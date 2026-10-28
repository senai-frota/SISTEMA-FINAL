from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copiar_unidade_checkin(apps, schema_editor):
    Reserva = apps.get_model('reservas', 'Reserva')
    Vistoria = apps.get_model('vistorias', 'Vistoria')
    for vistoria in Vistoria.objects.filter(tipo='checkin').exclude(unidade='').exclude(unidade__isnull=True):
        Reserva.objects.filter(pk=vistoria.reserva_id, unidade_checkin__isnull=True).update(
            unidade_checkin=vistoria.unidade,
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reservas', '0004_reserva_pernoite'),
        ('vistorias', '0003_vistoria_geolocalizacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='unidade_checkin',
            field=models.CharField(
                blank=True,
                choices=[
                    ('taguatinga', 'SENAI Taguatinga'),
                    ('gama', 'SENAI Gama'),
                    ('sobradinho', 'SENAI Sobradinho'),
                    ('sig', 'SENAI SIG'),
                ],
                help_text='Unidade histórica do check-in normal desta reserva. Não muda se o veículo for relocado depois.',
                max_length=20,
                null=True,
                verbose_name='Unidade do check-in',
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='motivo_cancelamento',
            field=models.CharField(
                blank=True,
                choices=[
                    ('usuario', 'Cancelada pelo solicitante'),
                    ('admin', 'Cancelada pelo administrador'),
                    ('falta_checkin', 'Cancelamento automático por falta de check-in'),
                ],
                default='',
                help_text='Preenchido quando a reserva é cancelada (manual ou automático).',
                max_length=30,
                verbose_name='Motivo do cancelamento',
            ),
        ),
        migrations.CreateModel(
            name='AutorizacaoCheckinAntecipado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('justificativa', models.TextField(verbose_name='Justificativa')),
                ('status', models.CharField(
                    choices=[
                        ('pendente', 'Pendente'),
                        ('aprovada', 'Aprovada'),
                        ('rejeitada', 'Rejeitada'),
                    ],
                    db_index=True,
                    default='pendente',
                    max_length=20,
                    verbose_name='Status',
                )),
                ('observacao_admin', models.TextField(blank=True, default='', verbose_name='Observação do administrador')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('decidido_em', models.DateTimeField(blank=True, null=True, verbose_name='Decidido em')),
                ('admin_decisor', models.ForeignKey(
                    blank=True,
                    limit_choices_to={'is_admin': True},
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='autorizacoes_checkin_decididas',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Administrador',
                )),
                ('reserva', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='autorizacoes_checkin',
                    to='reservas.reserva',
                    verbose_name='Reserva',
                )),
                ('solicitante', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='solicitacoes_checkin_antecipado',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Solicitante',
                )),
            ],
            options={
                'verbose_name': 'Autorização de check-in antecipado',
                'verbose_name_plural': 'Autorizações de check-in antecipado',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='autorizacaocheckinantecipado',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status', 'pendente')),
                fields=('reserva',),
                name='unique_autorizacao_checkin_pendente_por_reserva',
            ),
        ),
        migrations.CreateModel(
            name='EventoOperacional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chave', models.CharField(max_length=80, unique=True, verbose_name='Chave idempotente')),
                ('tipo', models.CharField(
                    choices=[
                        ('checkout_atrasado', 'Check-out atrasado'),
                        ('cancelamento_automatico', 'Cancelamento automático'),
                        ('email_checkout_atrasado', 'E-mail de check-out atrasado'),
                        ('email_cancelamento_automatico', 'E-mail de cancelamento automático'),
                    ],
                    db_index=True,
                    max_length=40,
                    verbose_name='Tipo',
                )),
                ('detalhes', models.JSONField(blank=True, default=dict, verbose_name='Detalhes')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('destinatario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='eventos_operacionais',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Destinatário',
                )),
                ('reserva', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='eventos_operacionais',
                    to='reservas.reserva',
                    verbose_name='Reserva',
                )),
            ],
            options={
                'verbose_name': 'Evento operacional',
                'verbose_name_plural': 'Eventos operacionais',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.RunPython(copiar_unidade_checkin, migrations.RunPython.noop),
    ]
