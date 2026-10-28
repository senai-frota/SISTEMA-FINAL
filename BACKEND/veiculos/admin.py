from django.contrib import admin

from .imagens import sincronizar_capa
from .models import FotoVeiculo, Veiculo


class FotoVeiculoInline(admin.TabularInline):
    model = FotoVeiculo
    extra = 0
    fields = ('arquivo', 'ordem', 'criado_em')
    readonly_fields = ('criado_em',)


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = (
        'placa', 'marca', 'modelo', 'ano', 'cor', 'status',
        'km_atual', 'data_ultima_manutencao', 'capacidade',
    )
    list_filter = ('status', 'marca', 'tipo_combustivel', 'ano')
    search_fields = ('placa', 'modelo', 'marca', 'renavam')
    ordering = ('marca', 'modelo')
    readonly_fields = ('criado_em', 'atualizado_em', 'foto')
    inlines = [FotoVeiculoInline]
    fieldsets = (
        ('Informações básicas', {
            'fields': ('placa', 'marca', 'modelo', 'ano', 'cor')
        }),
        ('Especificações', {
            'fields': ('tipo_combustivel', 'capacidade', 'renavam', 'chassi')
        }),
        ('Quilometragem e manutenção', {
            'fields': ('km_atual', 'data_ultima_manutencao')
        }),
        ('Status e mídia', {
            'fields': ('status', 'foto', 'observacoes')
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sincronizar_capa(form.instance)
