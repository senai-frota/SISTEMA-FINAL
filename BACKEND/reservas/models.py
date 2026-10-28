from django.conf import settings
from django.db import models
from veiculos.models import Veiculo

UNIDADE_CHECKIN_CHOICES = [
    ('taguatinga', 'SENAI Taguatinga'),
    ('gama', 'SENAI Gama'),
    ('sobradinho', 'SENAI Sobradinho'),
    ('sig', 'SENAI SIG'),
]

MOTIVO_CANCELAMENTO_USUARIO = 'usuario'
MOTIVO_CANCELAMENTO_ADMIN = 'admin'
MOTIVO_CANCELAMENTO_FALTA_CHECKIN = 'falta_checkin'

MOTIVO_CANCELAMENTO_CHOICES = [
    (MOTIVO_CANCELAMENTO_USUARIO, 'Cancelada pelo solicitante'),
    (MOTIVO_CANCELAMENTO_ADMIN, 'Cancelada pelo administrador'),
    (MOTIVO_CANCELAMENTO_FALTA_CHECKIN, 'Cancelamento automático por falta de check-in'),
]


class Reserva(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovada', 'Aprovada'),
        ('negada', 'Negada'),
        ('em_andamento', 'Em andamento'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]

    MODALIDADE_CHOICES = [
        ('horario', 'Horário personalizado'),
        ('turno', 'Turno'),
    ]

    TURNO_CHOICES = [
        ('manha', 'Manhã (06:00 – 12:00)'),
        ('tarde', 'Tarde (12:00 – 18:00)'),
        ('noite', 'Noite (18:00 – 22:00)'),
    ]

    # Horários oficiais dos turnos (início inclusivo, fim exclusivo na prática de UI).
    TURNOS_HORARIOS = {
        'manha': (6, 0, 12, 0),
        'tarde': (12, 0, 18, 0),
        'noite': (18, 0, 22, 0),
    }

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Solicitante'
    )
    veiculo = models.ForeignKey(
        Veiculo,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Veículo'
    )

    # Datas da reserva
    data_inicio = models.DateTimeField('Data e hora de retirada')
    data_fim = models.DateTimeField('Data e hora de devolução prevista')
    data_devolucao_real = models.DateTimeField('Data de devolução real', blank=True, null=True)

    modalidade = models.CharField(
        'Modalidade',
        max_length=20,
        choices=MODALIDADE_CHOICES,
        default='horario',
    )
    turno = models.CharField(
        'Turno',
        max_length=20,
        choices=TURNO_CHOICES,
        blank=True,
        null=True,
    )

    # Informações da solicitação
    motivo = models.TextField('Motivo da solicitação')
    destino = models.CharField('Destino', max_length=255, blank=True, null=True)
    passageiros = models.PositiveIntegerField('Quantidade de passageiros', default=1)

    pernoite = models.BooleanField(
        'Pernoite',
        default=False,
        help_text='Indica se o veículo permanece fora da unidade durante a noite.',
    )
    unidade_pernoite = models.CharField(
        'Unidade do pernoite',
        max_length=255,
        blank=True,
        null=True,
        help_text='Local onde o veículo ficará durante a noite (obrigatório se pernoite=True).',
    )
    unidade_checkin = models.CharField(
        'Unidade do check-in',
        max_length=20,
        choices=UNIDADE_CHECKIN_CHOICES,
        blank=True,
        null=True,
        help_text=(
            'Unidade histórica do check-in normal desta reserva. '
            'Não muda se o veículo for relocado depois.'
        ),
    )

    # Status e aprovação
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente'
    )
    admin_aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reservas_aprovadas',
        blank=True,
        null=True,
        verbose_name='Administrador aprovador',
        limit_choices_to={'is_admin': True}
    )
    data_aprovacao = models.DateTimeField('Data da aprovação/negação', blank=True, null=True)
    observacao_admin = models.TextField('Observação do administrador', blank=True, null=True)
    motivo_cancelamento = models.CharField(
        'Motivo do cancelamento',
        max_length=30,
        choices=MOTIVO_CANCELAMENTO_CHOICES,
        blank=True,
        default='',
        help_text='Preenchido quando a reserva é cancelada (manual ou automático).',
    )

    # Metadados
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-criado_em']

    def __str__(self):
        return f"Reserva #{self.id} - {self.usuario.nome} → {self.veiculo}"

    def pode_editar(self):
        return self.status in ['pendente']

    def pode_cancelar(self):
        return self.status in ['pendente', 'aprovada']

    def esta_ativa(self):
        return self.status in ['aprovada', 'em_andamento']

    @property
    def cancelamento_automatico(self):
        return (
            self.status == 'cancelada'
            and self.motivo_cancelamento == MOTIVO_CANCELAMENTO_FALTA_CHECKIN
        )


class AutorizacaoCheckinAntecipado(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovada', 'Aprovada'),
        ('rejeitada', 'Rejeitada'),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='autorizacoes_checkin',
        verbose_name='Reserva',
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solicitacoes_checkin_antecipado',
        verbose_name='Solicitante',
    )
    justificativa = models.TextField('Justificativa')
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        db_index=True,
    )
    admin_decisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='autorizacoes_checkin_decididas',
        blank=True,
        null=True,
        verbose_name='Administrador',
        limit_choices_to={'is_admin': True},
    )
    observacao_admin = models.TextField('Observação do administrador', blank=True, default='')
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    decidido_em = models.DateTimeField('Decidido em', blank=True, null=True)

    class Meta:
        verbose_name = 'Autorização de check-in antecipado'
        verbose_name_plural = 'Autorizações de check-in antecipado'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(
                fields=['reserva'],
                condition=models.Q(status='pendente'),
                name='unique_autorizacao_checkin_pendente_por_reserva',
            ),
        ]

    def __str__(self):
        return f'Check-in antecipado #{self.id} · reserva #{self.reserva_id} · {self.status}'


class EventoOperacional(models.Model):
    """Eventos idempotentes (alertas, e-mails, cancelamento automático)."""

    class Tipo(models.TextChoices):
        CHECKOUT_ATRASADO = 'checkout_atrasado', 'Check-out atrasado'
        CANCELAMENTO_AUTOMATICO = 'cancelamento_automatico', 'Cancelamento automático'
        EMAIL_CHECKOUT_ATRASADO = 'email_checkout_atrasado', 'E-mail de check-out atrasado'
        EMAIL_CANCELAMENTO = 'email_cancelamento_automatico', 'E-mail de cancelamento automático'

    chave = models.CharField('Chave idempotente', max_length=80, unique=True)
    tipo = models.CharField('Tipo', max_length=40, choices=Tipo.choices, db_index=True)
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='eventos_operacionais',
        verbose_name='Reserva',
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='eventos_operacionais',
        blank=True,
        null=True,
        verbose_name='Destinatário',
    )
    detalhes = models.JSONField('Detalhes', default=dict, blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Evento operacional'
        verbose_name_plural = 'Eventos operacionais'
        ordering = ['-criado_em']

    def __str__(self):
        return self.chave
