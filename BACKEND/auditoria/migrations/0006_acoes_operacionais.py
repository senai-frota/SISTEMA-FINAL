from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0005_acoes_imagem_veiculo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registroauditoria',
            name='acao',
            field=models.CharField(
                choices=[
                    ('criar_usuario', 'Cadastro de usuário'),
                    ('alterar_usuario', 'Alteração de usuário'),
                    ('ativar_usuario', 'Ativação de usuário'),
                    ('inativar_usuario', 'Inativação de usuário'),
                    ('definir_senha', 'Definição de senha'),
                    ('criar_veiculo', 'Cadastro de veículo'),
                    ('alterar_veiculo', 'Alteração de veículo'),
                    ('inativar_veiculo', 'Inativação de veículo'),
                    ('adicionar_imagem_veiculo', 'Imagem de veículo adicionada'),
                    ('substituir_imagem_veiculo', 'Imagem de veículo substituída'),
                    ('remover_imagem_veiculo', 'Imagem de veículo removida'),
                    ('criar_reserva', 'Solicitação de reserva'),
                    ('aprovar_reserva', 'Aprovação de reserva'),
                    ('rejeitar_reserva', 'Rejeição de reserva'),
                    ('cancelar_reserva', 'Cancelamento de reserva'),
                    ('cancelar_reserva_auto', 'Cancelamento automático por falta de check-in'),
                    ('solicitar_checkin_antecipado', 'Solicitação de check-in antecipado'),
                    ('aprovar_checkin_antecipado', 'Aprovação de check-in antecipado'),
                    ('rejeitar_checkin_antecipado', 'Rejeição de check-in antecipado'),
                    ('enviar_termo', 'Envio de termo'),
                    ('aprovar_termo', 'Aprovação de termo'),
                    ('rejeitar_termo', 'Rejeição de termo'),
                    ('enviar_cnh', 'Envio de CNH'),
                    ('aprovar_cnh', 'Aprovação de CNH'),
                    ('rejeitar_cnh', 'Rejeição de CNH'),
                    ('registrar_vistoria', 'Registro de vistoria'),
                    ('enviar_foto', 'Envio de foto'),
                    ('exportar_dados', 'Exportação de dados'),
                ],
                db_index=True,
                max_length=40,
                verbose_name='Ação',
            ),
        ),
    ]
