from django.db import models
from django.conf import settings
from reservas.models import Reserva


class Vistoria(models.Model):
    TIPO_CHOICES = [
        ('checkin', 'Check-in'),
        ('checkout', 'Check-out'),
    ]

    UNIDADE_CHOICES = [
        ('taguatinga', 'SENAI Taguatinga'),
        ('gama', 'SENAI Gama'),
        ('sobradinho', 'SENAI Sobradinho'),
        ('sig', 'SENAI SIG'),
    ]

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='vistorias',
        verbose_name='Reserva'
    )
    tipo = models.CharField(
        'Tipo de vistoria',
        max_length=10,
        choices=TIPO_CHOICES
    )
    unidade = models.CharField(
        'Unidade',
        max_length=20,
        choices=UNIDADE_CHOICES,
        blank=True,
        null=True,
        help_text='Unidade do SENAI onde o check-in/check-out está sendo realizado'
    )
    quilometragem = models.PositiveIntegerField(
        'Quilometragem (km)',
        blank=True,
        null=True,
        help_text='Km inicial do veículo (check-in) ou km final do veículo (check-out)'
    )
    realizada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vistorias_realizadas',
        verbose_name='Realizada por'
    )
    observacoes = models.TextField('Observações gerais', blank=True, null=True)
    data_hora = models.DateTimeField('Data e hora', auto_now_add=True)

    # Geolocalização opcional (preparação — não obrigatória no fluxo atual)
    latitude = models.DecimalField(
        'Latitude',
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text='Latitude opcional do dispositivo no momento da vistoria.',
    )
    longitude = models.DecimalField(
        'Longitude',
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text='Longitude opcional do dispositivo no momento da vistoria.',
    )
    precisao_metros = models.FloatField(
        'Precisão (m)',
        blank=True,
        null=True,
        help_text='Precisão opcional da geolocalização em metros.',
    )

    class Meta:
        verbose_name = 'Vistoria'
        verbose_name_plural = 'Vistorias'
        ordering = ['-data_hora']
        # Uma reserva só pode ter um checkin e um checkout
        constraints = [
            models.UniqueConstraint(
                fields=['reserva', 'tipo'],
                name='unique_vistoria_por_tipo'
            )
        ]

    def __str__(self):
        return f"Vistoria {self.get_tipo_display()} - Reserva #{self.reserva.id}"

    @staticmethod
    def get_ultimo_registro_quilometragem(veiculo, excluir_reserva_id=None):
        """
        Retorna a ÚLTIMA vistoria deste veículo (em qualquer reserva, de
        qualquer usuário) que tenha quilometragem registrada.

        Normalmente é o check-out mais recente, mas também considera um
        check-in quando o veículo ainda está em uso ou quando o check-out
        anterior não chegou a ser registrado. Isso evita que a corrente de
        quilometragem se quebre e volte a pedir o km manualmente.

        `excluir_reserva_id` é usado ao registrar uma vistoria: os registros
        da própria reserva não servem de origem para ela mesma.
        """
        qs = Vistoria.objects.filter(
            reserva__veiculo=veiculo,
            quilometragem__isnull=False
        )
        if excluir_reserva_id is not None:
            qs = qs.exclude(reserva_id=excluir_reserva_id)
        # '-data_hora' resolve pela ordem cronológica e '-id' desempata
        # registros gravados no mesmo instante.
        return qs.order_by('-data_hora', '-id').first()

    @staticmethod
    def get_ultima_quilometragem(veiculo, excluir_reserva_id=None):
        """
        Quilometragem que deve ser herdada como km inicial do próximo
        check-in deste veículo. Retorna None apenas no primeiro uso do
        veículo no sistema.
        """
        registro = Vistoria.get_ultimo_registro_quilometragem(
            veiculo, excluir_reserva_id=excluir_reserva_id
        )
        return registro.quilometragem if registro else None


class FotoVistoria(models.Model):
    DESCRICAO_CHOICES = [
        ('frente', 'Frente'),
        ('tras', 'Traseira'),
        ('lateral_esq', 'Lateral Esquerda'),
        ('lateral_dir', 'Lateral Direita'),
        ('painel', 'Painel / Interior'),
    ]

    vistoria = models.ForeignKey(
        Vistoria,
        on_delete=models.CASCADE,
        related_name='fotos',
        verbose_name='Vistoria'
    )
    foto = models.ImageField(
        'Foto',
        upload_to='vistorias/%Y/%m/',
        help_text='Foto do estado do veículo'
    )
    descricao = models.CharField(
        'Descrição',
        max_length=20,
        choices=DESCRICAO_CHOICES,
        blank=True,
        null=True
    )
    observacao = models.CharField('Observação', max_length=255, blank=True, null=True)
    upload_em = models.DateTimeField('Enviada em', auto_now_add=True)

    class Meta:
        verbose_name = 'Foto da Vistoria'
        verbose_name_plural = 'Fotos das Vistorias'
        ordering = ['vistoria', 'descricao']

    def __str__(self):
        return f"Foto {self.get_descricao_display() or 'Sem descrição'} - {self.vistoria}"