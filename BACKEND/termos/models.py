import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

from .validators import normalizar_documento, validar_cnh

VALIDADE_DIAS = 365


class TermoResponsabilidade(models.Model):
    ENTIDADE_CHOICES = [
        ('FIBRA', 'FIBRA'),
        ('SESI', 'SESI'),
        ('SENAI', 'SENAI'),
        ('IEL', 'IEL'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='termos',
        verbose_name='Empregado'
    )

    # Dados declarados pelo usuário no momento da solicitação
    entidade = models.CharField('Entidade', max_length=10, choices=ENTIDADE_CHOICES)
    cpf = models.CharField('CPF', max_length=14)
    cnh = models.CharField('CNH', max_length=20, validators=[validar_cnh])
    cpf_normalizado = models.CharField(max_length=11, blank=True, editable=False, db_index=True)
    cnh_normalizada = models.CharField(max_length=11, blank=True, editable=False, db_index=True)
    data_solicitacao = models.DateField('Data da solicitação')

    # Documento gerado (preenchido) a partir do formulário
    arquivo_pdf = models.FileField(
        'Termo gerado (PDF)',
        upload_to='termos/%Y/%m/',
        blank=True,
        null=True
    )

    # Fluxo de aprovação
    status = models.CharField(
        'Status',
        max_length=10,
        choices=STATUS_CHOICES,
        default='pendente'
    )
    admin_aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='termos_decididos',
        blank=True,
        null=True,
        verbose_name='Administrador responsável',
        limit_choices_to={'is_admin': True}
    )
    data_decisao = models.DateTimeField('Data da decisão', blank=True, null=True)
    observacao_admin = models.TextField('Observação do administrador', blank=True, null=True)

    # Validade: começa a contar a partir da aprovação (1 ano)
    data_validade = models.DateField('Válido até', blank=True, null=True)

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Termo de Responsabilidade'
        verbose_name_plural = 'Termos de Responsabilidade'
        ordering = ['-criado_em']

    def __str__(self):
        return f"Termo #{self.id} - {self.usuario.nome} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        self.cpf_normalizado = normalizar_documento(self.cpf)
        self.cnh_normalizada = normalizar_documento(self.cnh)
        super().save(*args, **kwargs)

    def aprovar(self, admin_user, observacao=None):
        agora = timezone.now()
        self.status = 'aprovado'
        self.admin_aprovador = admin_user
        self.data_decisao = agora
        self.data_validade = timezone.localdate() + datetime.timedelta(days=VALIDADE_DIAS)
        if observacao is not None:
            self.observacao_admin = observacao
        self.save()
        from .services_conta import ativar_conta
        ativar_conta(self.usuario)

    def rejeitar(self, admin_user, observacao=None):
        self.status = 'rejeitado'
        self.admin_aprovador = admin_user
        self.data_decisao = timezone.now()
        self.data_validade = None
        if observacao is not None:
            self.observacao_admin = observacao
        self.save()
        from .services_conta import desativar_conta
        desativar_conta(self.usuario)

    @property
    def dias_restantes(self):
        """Dias até o vencimento. None se não estiver aprovado."""
        if self.status != 'aprovado' or not self.data_validade:
            return None
        delta = (self.data_validade - timezone.localdate()).days
        return delta

    @property
    def esta_valido(self):
        return self.status == 'aprovado' and self.dias_restantes is not None and self.dias_restantes >= 0


def usuario_possui_termo_valido(usuario):
    """Retorna True se o usuário tem um Termo de Responsabilidade aprovado e dentro da validade."""
    termo = (
        TermoResponsabilidade.objects
        .filter(usuario=usuario, status='aprovado')
        .order_by('-data_decisao')
        .first()
    )
    return bool(termo and termo.esta_valido)
