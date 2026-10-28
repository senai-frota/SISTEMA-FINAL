from django.utils import timezone
from rest_framework import serializers
from .imagens import validar_imagem
from .models import FotoVeiculo, Veiculo
from usuarios.text_utils import aplicar_maiusculas


class FotoVeiculoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = FotoVeiculo
        fields = ['id', 'url', 'ordem']

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.arquivo and request:
            return request.build_absolute_uri(obj.arquivo.url)
        return None


class VeiculoSerializer(serializers.ModelSerializer):
    foto_url = serializers.SerializerMethodField()
    fotos = serializers.SerializerMethodField()

    class Meta:
        model = Veiculo
        fields = [
            'id', 'placa', 'modelo', 'marca', 'ano', 'cor',
            'tipo_combustivel', 'capacidade', 'renavam', 'chassi',
            'status', 'observacoes', 'foto', 'foto_url', 'fotos',
            'km_atual', 'data_ultima_manutencao',
            'criado_em', 'atualizado_em',
        ]
        # A imagem só muda pelo endpoint /veiculos/<id>/imagem/ (validação + auditoria).
        read_only_fields = ['id', 'foto', 'criado_em', 'atualizado_em']

    def _url_arquivo(self, campo):
        request = self.context.get('request')
        if campo and request:
            try:
                return request.build_absolute_uri(campo.url)
            except ValueError:
                return None
        return None

    def get_fotos(self, obj):
        itens = [
            item for item in FotoVeiculoSerializer(
                obj.fotos.all(), many=True, context=self.context,
            ).data
            if item.get('url')
        ]
        if not itens:
            url = self._url_arquivo(obj.foto)
            if url:
                itens.append({'id': None, 'url': url, 'ordem': 0})
        return itens

    def get_foto_url(self, obj):
        fotos = self.get_fotos(obj)
        return fotos[0]['url'] if fotos else None

    def validate_km_atual(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError(
                'Informe uma quilometragem válida (número ≥ 0).'
            )
        if self.instance and value < self.instance.km_atual:
            raise serializers.ValidationError(
                f'A quilometragem atual não pode ser menor que {self.instance.km_atual} km.'
            )
        return value

    def validate_data_ultima_manutencao(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError(
                'A data da última manutenção não pode ser posterior à data de hoje.'
            )
        return value

    def validate(self, data):
        aplicar_maiusculas(
            data,
            ['placa', 'modelo', 'marca', 'cor', 'observacoes', 'renavam', 'chassi'],
        )
        return data


class VeiculoImagemSerializer(serializers.Serializer):
    imagem = serializers.FileField(
        allow_empty_file=True,
        required=False,
        error_messages={
            'required': 'Selecione uma imagem.',
            'invalid': 'Envie um arquivo de imagem.',
            'no_name': 'Envie um arquivo de imagem.',
        },
    )

    def validate_imagem(self, arquivo):
        self.metadados = validar_imagem(arquivo)
        return arquivo
