from django.conf import settings
from django.db import models
from django.utils import timezone


class RegistroAuditoriaImutavel(Exception):
    """Tentativa de alterar ou apagar um registro de auditoria."""


MSG_IMUTAVEL = 'Registros de auditoria não podem ser alterados nem excluídos.'


class RegistroAuditoriaQuerySet(models.QuerySet):
    """Append-only: somente criação individual (encadeada) e leitura."""

    def update(self, **kwargs):
        raise RegistroAuditoriaImutavel(MSG_IMUTAVEL)

    def delete(self):
        raise RegistroAuditoriaImutavel(MSG_IMUTAVEL)

    def bulk_update(self, *args, **kwargs):
        raise RegistroAuditoriaImutavel(MSG_IMUTAVEL)

    def bulk_create(self, *args, **kwargs):
        raise RegistroAuditoriaImutavel(
            'Registros de auditoria devem ser criados um a um para manter a cadeia de integridade.'
        )

    def update_or_create(self, *args, **kwargs):
        raise RegistroAuditoriaImutavel(MSG_IMUTAVEL)


class RegistroAuditoria(models.Model):
    """
    Trilha de ações relevantes. Não guarda senha, token ou arquivo.

    Append-only: cada registro é selado com HMAC-SHA256 encadeado ao anterior
    (ver auditoria/integridade.py). Alterar ou remover registros quebra a cadeia.
    """

    class Acao(models.TextChoices):
        CRIAR_USUARIO = 'criar_usuario', 'Cadastro de usuário'
        ALTERAR_USUARIO = 'alterar_usuario', 'Alteração de usuário'
        ATIVAR_USUARIO = 'ativar_usuario', 'Ativação de usuário'
        INATIVAR_USUARIO = 'inativar_usuario', 'Inativação de usuário'
        DEFINIR_SENHA = 'definir_senha', 'Definição de senha'
        CRIAR_VEICULO = 'criar_veiculo', 'Cadastro de veículo'
        ALTERAR_VEICULO = 'alterar_veiculo', 'Alteração de veículo'
        INATIVAR_VEICULO = 'inativar_veiculo', 'Inativação de veículo'
        ADICIONAR_IMAGEM_VEICULO = 'adicionar_imagem_veiculo', 'Imagem de veículo adicionada'
        SUBSTITUIR_IMAGEM_VEICULO = 'substituir_imagem_veiculo', 'Imagem de veículo substituída'
        REMOVER_IMAGEM_VEICULO = 'remover_imagem_veiculo', 'Imagem de veículo removida'
        CRIAR_RESERVA = 'criar_reserva', 'Solicitação de reserva'
        APROVAR_RESERVA = 'aprovar_reserva', 'Aprovação de reserva'
        REJEITAR_RESERVA = 'rejeitar_reserva', 'Rejeição de reserva'
        CANCELAR_RESERVA = 'cancelar_reserva', 'Cancelamento de reserva'
        CANCELAR_RESERVA_AUTO = 'cancelar_reserva_auto', 'Cancelamento automático por falta de check-in'
        SOLICITAR_CHECKIN_ANTECIPADO = 'solicitar_checkin_antecipado', 'Solicitação de check-in antecipado'
        APROVAR_CHECKIN_ANTECIPADO = 'aprovar_checkin_antecipado', 'Aprovação de check-in antecipado'
        REJEITAR_CHECKIN_ANTECIPADO = 'rejeitar_checkin_antecipado', 'Rejeição de check-in antecipado'
        ENVIAR_TERMO = 'enviar_termo', 'Envio de termo'
        APROVAR_TERMO = 'aprovar_termo', 'Aprovação de termo'
        REJEITAR_TERMO = 'rejeitar_termo', 'Rejeição de termo'
        ENVIAR_CNH = 'enviar_cnh', 'Envio de CNH'
        APROVAR_CNH = 'aprovar_cnh', 'Aprovação de CNH'
        REJEITAR_CNH = 'rejeitar_cnh', 'Rejeição de CNH'
        REGISTRAR_VISTORIA = 'registrar_vistoria', 'Registro de vistoria'
        ENVIAR_FOTO = 'enviar_foto', 'Envio de foto'
        EXPORTAR_DADOS = 'exportar_dados', 'Exportação de dados'

    class Entidade(models.TextChoices):
        USUARIO = 'usuario', 'Usuário'
        VEICULO = 'veiculo', 'Veículo'
        RESERVA = 'reserva', 'Reserva'
        TERMO = 'termo', 'Termo'
        CNH = 'cnh', 'CNH'
        VISTORIA = 'vistoria', 'Vistoria'
        FOTO = 'foto', 'Foto'
        RELATORIO = 'relatorio', 'Relatório'

    criado_em = models.DateTimeField(
        'Data e hora', default=timezone.now, editable=False, db_index=True,
    )
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='acoes_auditoria',
        blank=True,
        null=True,
        verbose_name='Responsável',
    )
    ator_nome = models.CharField('Nome do responsável', max_length=150, blank=True)
    ator_matricula = models.CharField('Matrícula do responsável', max_length=50, blank=True)
    acao = models.CharField('Ação', max_length=40, choices=Acao.choices, db_index=True)
    entidade = models.CharField('Entidade', max_length=30, choices=Entidade.choices, db_index=True)
    entidade_id = models.PositiveIntegerField('ID da entidade', blank=True, null=True)
    identificacao = models.CharField('Identificação', max_length=200, blank=True)
    descricao = models.TextField('Descrição')
    detalhes = models.JSONField('Detalhes', default=dict, blank=True)
    justificativa = models.TextField('Justificativa', blank=True, default='')
    usuario_afetado_id = models.PositiveIntegerField(
        'ID do usuário afetado', blank=True, null=True, db_index=True,
    )
    usuario_afetado_nome = models.CharField('Nome do usuário afetado', max_length=150, blank=True, default='')
    usuario_afetado_matricula = models.CharField(
        'Matrícula do usuário afetado', max_length=50, blank=True, default='',
    )

    sequencia = models.PositiveBigIntegerField('Sequência', unique=True, editable=False)
    hash_anterior = models.CharField('Hash do registro anterior', max_length=64, editable=False)
    hash = models.CharField('Hash do registro', max_length=64, editable=False)
    versao_hash = models.PositiveSmallIntegerField('Versão do hash', editable=False)

    objects = RegistroAuditoriaQuerySet.as_manager()

    class Meta:
        verbose_name = 'Registro de auditoria'
        verbose_name_plural = 'Registros de auditoria'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['entidade', 'entidade_id']),
        ]

    def __str__(self):
        return f'{self.get_acao_display()} — {self.identificacao or self.entidade}'

    def save(self, *args, **kwargs):
        if not self._state.adding or self.pk is not None:
            raise RegistroAuditoriaImutavel(MSG_IMUTAVEL)
        from .integridade import gravar_encadeado

        using = kwargs.get('using')
        gravar_encadeado(
            self,
            lambda: super(RegistroAuditoria, self).save(force_insert=True, using=using),
            using=using,
        )

    def delete(self, *args, **kwargs):
        raise RegistroAuditoriaImutavel(MSG_IMUTAVEL)
