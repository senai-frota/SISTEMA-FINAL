from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario, DocumentoCNH
from .forms import UsuarioCreationForm, UsuarioChangeForm


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ('matricula', 'nome', 'email', 'setor', 'is_admin', 'is_active', 'precisa_definir_senha', 'criado_em')
    list_filter = ('is_admin', 'is_active', 'precisa_definir_senha', 'setor', 'criado_em')
    search_fields = ('matricula', 'nome', 'email')
    ordering = ('nome',)
    readonly_fields = ('criado_em', 'atualizado_em')

    fieldsets = (
        (None, {'fields': ('matricula', 'password')}),
        ('Informações pessoais', {'fields': ('nome', 'email', 'telefone', 'setor')}),
        ('Permissões', {'fields': ('is_admin', 'is_superuser', 'groups', 'user_permissions')}),
        ('Status', {'fields': ('is_active', 'precisa_definir_senha', 'criado_em', 'atualizado_em')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('matricula', 'nome', 'email', 'telefone', 'setor', 'password1', 'password2', 'is_admin', 'is_active'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions',)


@admin.register(DocumentoCNH)
class DocumentoCNHAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'data_validade', 'status', 'admin_aprovador', 'criado_em')
    list_filter = ('status', 'data_validade')
    search_fields = ('usuario__nome', 'usuario__matricula')
    readonly_fields = ('criado_em', 'atualizado_em', 'data_decisao')
