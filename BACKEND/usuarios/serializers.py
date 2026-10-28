from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.utils import timezone

from .models import (
    Usuario,
    DocumentoCNH,
    resumo_cnh_usuario,
    cnh_pendente,
    CNH_DIAS_ALERTA_VENCIMENTO,
)
from .text_utils import aplicar_maiusculas
from auditoria.services import exigir_justificativa


class DocumentoCNHSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)
    usuario_matricula = serializers.CharField(source='usuario.matricula', read_only=True)
    admin_aprovador_nome = serializers.CharField(
        source='admin_aprovador.nome', read_only=True
    )
    arquivo_url = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    esta_vencida = serializers.BooleanField(read_only=True)
    proxima_do_vencimento = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentoCNH
        fields = [
            'id', 'usuario', 'usuario_nome', 'usuario_matricula',
            'data_validade', 'arquivo', 'arquivo_url',
            'status', 'admin_aprovador', 'admin_aprovador_nome',
            'data_decisao', 'observacao_admin',
            'dias_restantes', 'esta_vencida', 'proxima_do_vencimento',
            'criado_em', 'atualizado_em',
        ]
        read_only_fields = [
            'id', 'usuario', 'data_validade', 'status', 'admin_aprovador',
            'data_decisao', 'observacao_admin',
            'criado_em', 'atualizado_em',
        ]

    def get_dias_restantes(self, obj):
        return obj.dias_restantes

    def get_arquivo_url(self, obj):
        request = self.context.get('request')
        if not obj.arquivo or not request:
            return None
        user = request.user
        if not user.is_authenticated:
            return None
        if not user.is_admin and obj.usuario_id != user.id:
            return None
        return request.build_absolute_uri(obj.arquivo.url)


class DocumentoCNHCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoCNH
        fields = ['arquivo']

    def validate(self, data):
        usuario = self.context['request'].user
        if cnh_pendente(usuario):
            raise serializers.ValidationError(
                'Você já possui uma CNH aguardando aprovação do gestor.'
            )
        return data

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        validated_data['status'] = 'pendente'
        validated_data['data_validade'] = None
        return super().create(validated_data)


class DocumentoCNHDecisaoSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['aprovado', 'rejeitado'])
    data_validade = serializers.DateField(required=False, allow_null=True)
    observacao_admin = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get('status') == 'aprovado':
            if not data.get('data_validade'):
                raise serializers.ValidationError({
                    'data_validade': [
                        'Informe a data de validade da CNH para aprovar o documento.'
                    ]
                })
            if data['data_validade'] < timezone.localdate():
                raise serializers.ValidationError({
                    'data_validade': [
                        'A data de validade não pode estar no passado.'
                    ]
                })
        if data.get('status') == 'rejeitado':
            data['observacao_admin'] = exigir_justificativa(data.get('observacao_admin'))
        aplicar_maiusculas(data, ['observacao_admin'])
        return data

    def update(self, instance, validated_data):
        admin_user = self.context['request'].user
        observacao = validated_data.get('observacao_admin', '')
        if validated_data['status'] == 'aprovado':
            instance.aprovar(admin_user, validated_data['data_validade'], observacao)
        else:
            instance.rejeitar(admin_user, observacao)
        return instance


class UsuarioSerializer(serializers.ModelSerializer):
    cnh = serializers.SerializerMethodField()
    termo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'matricula', 'nome', 'email', 'telefone', 'setor',
            'is_admin', 'is_active', 'precisa_definir_senha', 'criado_em',
            'cnh', 'termo',
        ]
        read_only_fields = ['id', 'criado_em', 'precisa_definir_senha']

    def get_cnh(self, obj):
        if obj.is_admin:
            return None
        return resumo_cnh_usuario(obj)

    def get_termo(self, obj):
        if obj.is_admin:
            return None
        from termos.services_conta import resumo_termo_usuario
        return resumo_termo_usuario(obj)


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Admin cria usuário sem senha; conta fica em primeiro acesso."""

    matricula = serializers.CharField(
        max_length=50,
        validators=[
            UniqueValidator(
                queryset=Usuario.objects.all(),
                message='Esta matrícula já está cadastrada.',
            )
        ],
        error_messages={
            'blank': 'Informe a matrícula.',
            'required': 'Informe a matrícula.',
        },
    )

    class Meta:
        model = Usuario
        fields = [
            'matricula', 'nome', 'email', 'telefone', 'setor',
            'is_admin', 'is_active',
        ]
        extra_kwargs = {
            'nome': {
                'error_messages': {
                    'blank': 'Informe o nome completo.',
                    'required': 'Informe o nome completo.',
                },
            },
        }

    def validate(self, data):
        aplicar_maiusculas(data, ['nome', 'setor', 'telefone'])
        return data

    def create(self, validated_data):
        return Usuario.objects.create_user(
            password=None,
            precisa_definir_senha=True,
            **validated_data,
        )


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['nome', 'email', 'telefone', 'setor', 'is_active']

    def validate_is_active(self, value):
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_admin', False):
            raise serializers.ValidationError(
                'Apenas administradores podem alterar o status da conta.'
            )
        return value

    def validate(self, data):
        aplicar_maiusculas(data, ['nome', 'setor', 'telefone'])
        return data


class PerfilSerializer(serializers.ModelSerializer):
    cnh = serializers.SerializerMethodField()
    cnh_dias_alerta = serializers.SerializerMethodField()
    termo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'matricula', 'nome', 'email', 'telefone', 'setor',
            'is_admin', 'is_active', 'precisa_definir_senha',
            'cnh', 'cnh_dias_alerta', 'termo',
        ]

    def get_cnh(self, obj):
        return resumo_cnh_usuario(obj)

    def get_cnh_dias_alerta(self, obj):
        return CNH_DIAS_ALERTA_VENCIMENTO

    def get_termo(self, obj):
        from termos.services_conta import resumo_termo_usuario, sincronizar_status_conta
        sincronizar_status_conta(obj)
        obj.refresh_from_db(fields=['is_active'])
        return resumo_termo_usuario(obj)
