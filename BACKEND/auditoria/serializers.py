from rest_framework import serializers

from .models import RegistroAuditoria


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    acao_label = serializers.CharField(source='get_acao_display', read_only=True)
    entidade_label = serializers.CharField(source='get_entidade_display', read_only=True)
    registro_ativo = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAuditoria
        fields = [
            'id',
            'criado_em',
            'ator',
            'ator_nome',
            'ator_matricula',
            'acao',
            'acao_label',
            'entidade',
            'entidade_label',
            'entidade_id',
            'identificacao',
            'descricao',
            'detalhes',
            'justificativa',
            'usuario_afetado_id',
            'usuario_afetado_nome',
            'usuario_afetado_matricula',
            'sequencia',
            'hash',
            'registro_ativo',
        ]
        read_only_fields = fields

    def get_registro_ativo(self, obj):
        mapa = self.context.get('ativos') or {}
        return mapa.get((obj.entidade, obj.entidade_id))
