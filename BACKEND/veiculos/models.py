from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Veiculo(models.Model):
    STATUS_CHOICES = [
        ('disponivel', 'Disponível'),
        ('em_uso', 'Em uso'),
        ('manutencao', 'Em manutenção'),
        ('inativo', 'Inativo'),
    ]

    COMBUSTIVEL_CHOICES = [
        ('gasolina', 'Gasolina'),
        ('etanol', 'Etanol'),
        ('diesel', 'Diesel'),
        ('flex', 'Flex'),
        ('eletrico', 'Elétrico'),
        ('hibrido', 'Híbrido'),
    ]

    placa = models.CharField('Placa', max_length=10, unique=True)
    modelo = models.CharField('Modelo', max_length=100)
    marca = models.CharField('Marca', max_length=100)
    ano = models.PositiveIntegerField('Ano')
    cor = models.CharField('Cor', max_length=50)
    tipo_combustivel = models.CharField(
        'Combustível',
        max_length=20,
        choices=COMBUSTIVEL_CHOICES,
        default='flex'
    )
    capacidade = models.PositiveIntegerField('Capacidade de passageiros', default=5)
    renavam = models.CharField('RENAVAM', max_length=20, blank=True, null=True)
    chassi = models.CharField('Chassi', max_length=30, blank=True, null=True)
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='disponivel'
    )
    observacoes = models.TextField('Observações', blank=True, null=True)
    foto = models.ImageField('Foto do veículo', upload_to='veiculos/', blank=True, null=True)
    km_atual = models.PositiveIntegerField(
        'Quilometragem atual (km)',
        default=0,
        help_text='Quilometragem conhecida do veículo; atualizada no check-out.',
    )
    data_ultima_manutencao = models.DateField(
        'Data da última manutenção',
        blank=True,
        null=True,
        help_text='Informativo apenas; não gera bloqueios ou alertas automáticos.',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'
        ordering = ['marca', 'modelo']

    def __str__(self):
        return f"{self.marca} {self.modelo} ({self.placa})"

    def clean(self):
        super().clean()
        if self.data_ultima_manutencao and self.data_ultima_manutencao > timezone.localdate():
            raise ValidationError({
                'data_ultima_manutencao':
                    'A data da última manutenção não pode ser posterior à data de hoje.',
            })


class FotoVeiculo(models.Model):
    """Fotos de referência do veículo (galeria). A capa permanece em Veiculo.foto."""

    veiculo = models.ForeignKey(
        Veiculo,
        on_delete=models.CASCADE,
        related_name='fotos',
        verbose_name='Veículo',
    )
    arquivo = models.ImageField('Foto', upload_to='veiculos/')
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Foto do veículo'
        verbose_name_plural = 'Fotos do veículo'
        ordering = ['ordem', 'id']

    def __str__(self):
        return f'Foto {self.ordem} de {self.veiculo.placa}'


class VeiculoBackup(models.Model):
    """Registro histórico de veículos removidos (mantido por compatibilidade)."""

    veiculo_original_id = models.PositiveIntegerField('ID do veículo original')
    placa = models.CharField('Placa', max_length=10)
    modelo = models.CharField('Modelo', max_length=100)
    marca = models.CharField('Marca', max_length=100)
    ano = models.PositiveIntegerField('Ano')
    cor = models.CharField('Cor', max_length=50)
    tipo_combustivel = models.CharField('Combustível', max_length=20)
    capacidade = models.PositiveIntegerField('Capacidade de passageiros')
    renavam = models.CharField('RENAVAM', max_length=20, blank=True, null=True)
    chassi = models.CharField('Chassi', max_length=30, blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True, null=True)
    foto = models.CharField('Foto do veículo (caminho/URL)', max_length=500, blank=True, null=True)
    status_no_momento = models.CharField('Status no momento da remoção', max_length=20)
    criado_em_original = models.DateTimeField('Cadastrado em (original)')
    removido_em = models.DateTimeField('Removido em', auto_now_add=True)
    removido_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        related_name='veiculos_removidos',
        blank=True,
        null=True,
        verbose_name='Removido por',
    )

    class Meta:
        verbose_name = 'Backup de Veículo'
        verbose_name_plural = 'Backups de Veículos'
        ordering = ['-removido_em']
