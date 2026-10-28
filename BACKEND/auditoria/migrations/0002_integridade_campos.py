import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0001_registro_auditoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registroauditoria',
            name='criado_em',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False, verbose_name='Data e hora'),
        ),
        migrations.AlterField(
            model_name='registroauditoria',
            name='acao',
            field=models.CharField(choices=[('criar_usuario', 'Cadastro de usuário'), ('alterar_usuario', 'Alteração de usuário'), ('ativar_usuario', 'Ativação de usuário'), ('inativar_usuario', 'Inativação de usuário'), ('definir_senha', 'Definição de senha'), ('criar_veiculo', 'Cadastro de veículo'), ('alterar_veiculo', 'Alteração de veículo'), ('inativar_veiculo', 'Inativação de veículo'), ('criar_reserva', 'Solicitação de reserva'), ('aprovar_reserva', 'Aprovação de reserva'), ('rejeitar_reserva', 'Rejeição de reserva'), ('cancelar_reserva', 'Cancelamento de reserva'), ('enviar_termo', 'Envio de termo'), ('aprovar_termo', 'Aprovação de termo'), ('rejeitar_termo', 'Rejeição de termo'), ('enviar_cnh', 'Envio de CNH'), ('aprovar_cnh', 'Aprovação de CNH'), ('rejeitar_cnh', 'Rejeição de CNH'), ('registrar_vistoria', 'Registro de vistoria'), ('enviar_foto', 'Envio de foto'), ('exportar_dados', 'Exportação de dados')], db_index=True, max_length=40, verbose_name='Ação'),
        ),
        migrations.AlterField(
            model_name='registroauditoria',
            name='entidade',
            field=models.CharField(choices=[('usuario', 'Usuário'), ('veiculo', 'Veículo'), ('reserva', 'Reserva'), ('termo', 'Termo'), ('cnh', 'CNH'), ('vistoria', 'Vistoria'), ('foto', 'Foto'), ('relatorio', 'Relatório')], db_index=True, max_length=30, verbose_name='Entidade'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='justificativa',
            field=models.TextField(blank=True, default='', verbose_name='Justificativa'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='usuario_afetado_id',
            field=models.PositiveIntegerField(blank=True, db_index=True, null=True, verbose_name='ID do usuário afetado'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='usuario_afetado_nome',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='Nome do usuário afetado'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='usuario_afetado_matricula',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='Matrícula do usuário afetado'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='sequencia',
            field=models.PositiveBigIntegerField(editable=False, null=True, verbose_name='Sequência'),
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='hash_anterior',
            field=models.CharField(default='', editable=False, max_length=64, verbose_name='Hash do registro anterior'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='hash',
            field=models.CharField(default='', editable=False, max_length=64, verbose_name='Hash do registro'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='registroauditoria',
            name='versao_hash',
            field=models.PositiveSmallIntegerField(default=1, editable=False, verbose_name='Versão do hash'),
            preserve_default=False,
        ),
    ]
