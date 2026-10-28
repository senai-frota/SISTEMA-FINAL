from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Somente consulta: sem inclusão, alteração, exclusão ou ações em massa."""

    list_display = ('sequencia', 'criado_em', 'ator_nome', 'acao', 'entidade', 'entidade_id', 'identificacao')
    list_filter = ('acao', 'entidade')
    search_fields = ('descricao', 'identificacao', 'ator_nome', 'ator_matricula', 'usuario_afetado_nome')
    ordering = ('-sequencia',)
    actions = None

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
