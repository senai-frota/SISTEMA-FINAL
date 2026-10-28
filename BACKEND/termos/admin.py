from django.contrib import admin
from .models import TermoResponsabilidade


@admin.register(TermoResponsabilidade)
class TermoResponsabilidadeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'usuario', 'entidade', 'status',
        'data_solicitacao', 'data_validade', 'admin_aprovador', 'criado_em'
    )
    list_filter = ('status', 'entidade', 'criado_em')
    search_fields = ('usuario__nome', 'usuario__matricula', 'cpf', 'cnh')
    ordering = ('-criado_em',)
    readonly_fields = ('criado_em', 'atualizado_em', 'arquivo_pdf', 'data_decisao', 'data_validade')

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        if obj is not None:
            return (*campos, 'data_solicitacao')
        return campos

    fieldsets = (
        ('Solicitação', {
            'fields': ('usuario', 'entidade', 'cpf', 'cnh', 'data_solicitacao', 'arquivo_pdf')
        }),
        ('Decisão', {
            'fields': ('status', 'admin_aprovador', 'data_decisao', 'observacao_admin', 'data_validade')
        }),
        ('Metadados', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
