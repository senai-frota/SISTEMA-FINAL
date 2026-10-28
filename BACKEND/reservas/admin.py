from django.contrib import admin
from .models import AutorizacaoCheckinAntecipado, EventoOperacional, Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'usuario', 'veiculo', 'data_inicio',
        'data_fim', 'pernoite', 'status', 'motivo_cancelamento',
        'admin_aprovador', 'criado_em',
    )
    list_filter = ('status', 'pernoite', 'motivo_cancelamento', 'data_inicio', 'criado_em')
    search_fields = (
        'usuario__nome', 'usuario__matricula', 'veiculo__placa',
        'motivo', 'unidade_pernoite',
    )
    ordering = ('-criado_em',)
    readonly_fields = ('criado_em', 'atualizado_em', 'data_aprovacao', 'unidade_checkin')
    date_hierarchy = 'data_inicio'

    fieldsets = (
        ('Solicitação', {
            'fields': ('usuario', 'veiculo', 'motivo', 'destino', 'passageiros')
        }),
        ('Datas e pernoite', {
            'fields': (
                'data_inicio', 'data_fim', 'data_devolucao_real',
                'pernoite', 'unidade_pernoite', 'unidade_checkin',
            )
        }),
        ('Modalidade', {
            'fields': ('modalidade', 'turno')
        }),
        ('Aprovação', {
            'fields': (
                'status', 'admin_aprovador', 'data_aprovacao',
                'observacao_admin', 'motivo_cancelamento',
            )
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AutorizacaoCheckinAntecipado)
class AutorizacaoCheckinAntecipadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'reserva', 'solicitante', 'status', 'admin_decisor', 'criado_em')
    list_filter = ('status',)
    search_fields = ('reserva__veiculo__placa', 'solicitante__nome', 'justificativa')
    readonly_fields = ('criado_em', 'decidido_em')


@admin.register(EventoOperacional)
class EventoOperacionalAdmin(admin.ModelAdmin):
    list_display = ('chave', 'tipo', 'reserva', 'criado_em')
    list_filter = ('tipo',)
    search_fields = ('chave',)
    readonly_fields = ('chave', 'tipo', 'reserva', 'destinatario', 'detalhes', 'criado_em')
