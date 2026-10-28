import datetime

from django.utils import timezone
from rest_framework import serializers

from .models import TermoResponsabilidade
from .validators import normalizar_documento
from usuarios.text_utils import aplicar_maiusculas
from auditoria.services import exigir_justificativa


class TermoResponsabilidadeSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)
    usuario_matricula = serializers.CharField(source='usuario.matricula', read_only=True)
    admin_aprovador_nome = serializers.CharField(source='admin_aprovador.nome', read_only=True)
    arquivo_pdf_url = serializers.SerializerMethodField()
    dias_restantes = serializers.ReadOnlyField()
    esta_valido = serializers.ReadOnlyField()

    class Meta:
        model = TermoResponsabilidade
        fields = [
            'id', 'usuario', 'usuario_nome', 'usuario_matricula',
            'entidade', 'cpf', 'cnh', 'data_solicitacao',
            'arquivo_pdf', 'arquivo_pdf_url',
            'status', 'admin_aprovador', 'admin_aprovador_nome',
            'data_decisao', 'observacao_admin', 'data_validade',
            'dias_restantes', 'esta_valido',
            'criado_em', 'atualizado_em',
        ]
        read_only_fields = [
            'id', 'usuario', 'data_solicitacao', 'status', 'admin_aprovador',
            'data_decisao', 'observacao_admin', 'data_validade',
            'criado_em', 'atualizado_em',
        ]

    def get_arquivo_pdf_url(self, obj):
        request = self.context.get('request')
        if not obj.arquivo_pdf or not request:
            return None
        user = request.user
        if not user.is_authenticated:
            return None
        if not user.is_admin and obj.usuario_id != user.id:
            return None
        return request.build_absolute_uri(obj.arquivo_pdf.url)


class TermoCreateSerializer(serializers.ModelSerializer):
    """Usuário envia o documento físico assinado (upload) para análise."""

    class Meta:
        model = TermoResponsabilidade
        fields = ['entidade', 'cpf', 'cnh', 'arquivo_pdf']
        extra_kwargs = {
            'arquivo_pdf': {'required': True, 'allow_null': False},
        }

    def validate(self, data):
        request = self.context['request']
        usuario = request.user
        documentos_de_outros = TermoResponsabilidade.objects.exclude(usuario=usuario)
        erros = {}

        cpf = normalizar_documento(data.get('cpf'))
        if cpf and documentos_de_outros.filter(cpf_normalizado=cpf).exists():
            erros['cpf'] = ['Este CPF já está vinculado a outro usuário.']

        cnh = normalizar_documento(data.get('cnh'))
        if cnh and documentos_de_outros.filter(cnh_normalizada=cnh).exists():
            erros['cnh'] = ['Esta CNH já está vinculada a outro usuário.']

        if erros:
            raise serializers.ValidationError(erros)

        if TermoResponsabilidade.objects.filter(usuario=usuario, status='pendente').exists():
            raise serializers.ValidationError(
                'Você já possui um Termo de Responsabilidade aguardando análise.'
            )
        return data

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        validated_data['data_solicitacao'] = timezone.localdate()
        validated_data['status'] = 'pendente'
        return super().create(validated_data)


class TermoDecisaoSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['aprovado', 'rejeitado'])
    observacao_admin = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get('status') == 'rejeitado':
            data['observacao_admin'] = exigir_justificativa(data.get('observacao_admin'))
        aplicar_maiusculas(data, ['observacao_admin'])
        return data

    def update(self, instance, validated_data):
        admin_user = self.context['request'].user
        observacao = validated_data.get('observacao_admin', '')
        if validated_data['status'] == 'aprovado':
            instance.aprovar(admin_user, observacao)
        else:
            instance.rejeitar(admin_user, observacao)
        return instance
