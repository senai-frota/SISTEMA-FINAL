from django.contrib import admin
from .models import Vistoria, FotoVistoria


class FotoVistoriaInline(admin.TabularInline):
    model = FotoVistoria
    extra = 0
    readonly_fields = ('upload_em',)
    fields = ('foto', 'descricao', 'observacao', 'upload_em')


@admin.register(Vistoria)
class VistoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'reserva', 'tipo', 'unidade', 'quilometragem', 'realizada_por', 'data_hora')
    list_filter = ('tipo', 'unidade', 'data_hora')
    search_fields = ('reserva__usuario__nome', 'reserva__veiculo__placa')
    readonly_fields = ('data_hora',)
    inlines = [FotoVistoriaInline]

    fieldsets = (
        ('Informações', {
            'fields': ('reserva', 'tipo', 'unidade', 'quilometragem', 'realizada_por')
        }),
        ('Detalhes', {
            'fields': ('observacoes', 'data_hora')
        }),
    )


@admin.register(FotoVistoria)
class FotoVistoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'vistoria', 'descricao', 'upload_em')
    list_filter = ('descricao', 'upload_em')
    search_fields = ('vistoria__reserva__veiculo__placa', 'observacao')
    readonly_fields = ('upload_em',)
