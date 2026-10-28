from rest_framework import serializers
from .models import Vistoria, FotoVistoria
from .regras import (
    validar_janela_operacional,
    validar_checkin_horario_reserva,
    validar_checkout_horario_reserva,
    MSG_CHECKOUT_UNIDADE,
    MSG_VEICULO_INDISPONIVEL,
)
from usuarios.text_utils import aplicar_maiusculas


class FotoVistoriaSerializer(serializers.ModelSerializer):
    foto_url = serializers.SerializerMethodField()

    class Meta:
        model = FotoVistoria
        fields = ['id', 'vistoria', 'foto', 'foto_url', 'descricao', 'observacao', 'upload_em']
        read_only_fields = ['id', 'upload_em']

    def get_foto_url(self, obj):
        request = self.context.get('request')
        if obj.foto and request:
            return request.build_absolute_uri(obj.foto.url)
        return None

    def validate(self, data):
        return aplicar_maiusculas(data, ['descricao', 'observacao'])


class FotoUploadSerializer(serializers.ModelSerializer):
    """Serializer simplificado para upload de fotos."""
    class Meta:
        model = FotoVistoria
        fields = ['foto', 'descricao', 'observacao']

    def validate(self, data):
        return aplicar_maiusculas(data, ['descricao', 'observacao'])


class VistoriaSerializer(serializers.ModelSerializer):
    fotos = FotoVistoriaSerializer(many=True, read_only=True)
    realizada_por_nome = serializers.CharField(source='realizada_por.nome', read_only=True)
    reserva_info = serializers.CharField(source='reserva.__str__', read_only=True)
    unidade_display = serializers.CharField(source='get_unidade_display', read_only=True)
    reserva_status = serializers.CharField(source='reserva.status', read_only=True)

    class Meta:
        model = Vistoria
        fields = [
            'id', 'reserva', 'reserva_info', 'reserva_status', 'tipo',
            'unidade', 'unidade_display', 'quilometragem',
            'realizada_por', 'realizada_por_nome',
            'observacoes', 'fotos', 'data_hora',
            'latitude', 'longitude', 'precisao_metros',
        ]
        read_only_fields = ['id', 'realizada_por', 'data_hora']


class VistoriaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criar/registrar a vistoria (check-in ou check-out).

    Regras importantes:

    * O campo `id` é devolvido na resposta — o front-end precisa dele para
      anexar as fotos e para exibir a vistoria criada.
    * O validador automático de unicidade (reserva + tipo) do DRF é
      desativado de propósito (`validators = []`). Quem controla se a
      vistoria pode ou não ser registrada é o STATUS DA RESERVA, validado
      logo abaixo. Assim, uma tentativa anterior que falhou no meio do
      caminho (por exemplo: a vistoria foi gravada mas as fotos não) não
      deixa o usuário travado — a vistoria incompleta é reaproveitada e
      sobrescrita na nova tentativa.
    """

    class Meta:
        model = Vistoria
        fields = [
            'id', 'reserva', 'tipo', 'unidade', 'quilometragem', 'observacoes',
            'latitude', 'longitude', 'precisao_metros',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'unidade': {'required': True, 'allow_null': False},
            'latitude': {'required': False, 'allow_null': True},
            'longitude': {'required': False, 'allow_null': True},
            'precisao_metros': {'required': False, 'allow_null': True},
        }
        validators = []

    def validate(self, data):
        reserva = self.context.get('reserva_bloqueada') or data['reserva']
        data['reserva'] = reserva
        tipo = data['tipo']
        veiculo = reserva.veiculo
        request = self.context.get('request')

        if reserva.status == 'cancelada':
            raise serializers.ValidationError(
                'Não é possível registrar vistoria em reserva cancelada.'
            )

        if request and not request.user.is_admin and reserva.usuario != request.user:
            raise serializers.ValidationError(
                'Você só pode realizar vistorias das suas próprias reservas.'
            )

        if tipo == 'checkin':
            validar_janela_operacional()

            if reserva.status != 'aprovada':
                raise serializers.ValidationError(
                    'Check-in só é permitido para reservas aprovadas. '
                    f'Esta reserva está com o status "{reserva.get_status_display()}".'
                )
            if veiculo.status != 'disponivel':
                raise serializers.ValidationError(MSG_VEICULO_INDISPONIVEL)
            validar_checkin_horario_reserva(reserva)

            km_veiculo = veiculo.km_atual
            quilometragem_enviada = data.get('quilometragem')
            if km_veiculo and km_veiculo > 0:
                data['quilometragem'] = km_veiculo
            else:
                ultima_km = Vistoria.get_ultima_quilometragem(
                    veiculo, excluir_reserva_id=reserva.pk
                )
                if ultima_km is not None:
                    data['quilometragem'] = ultima_km
                elif quilometragem_enviada is None:
                    raise serializers.ValidationError(
                        'Informe a quilometragem inicial (km) deste veículo '
                        '(ainda não há KM atual cadastrado).'
                    )

        elif tipo == 'checkout':
            if reserva.status != 'em_andamento':
                raise serializers.ValidationError(
                    'Check-out só é permitido para reservas em andamento. '
                    f'Esta reserva está com o status "{reserva.get_status_display()}".'
                )
            validar_checkout_horario_reserva(reserva)

            checkin = Vistoria.objects.filter(reserva=reserva, tipo='checkin').first()
            if checkin is None:
                raise serializers.ValidationError(
                    'Não é possível fazer check-out sem check-in prévio.'
                )
            unidade_enviada = data.get('unidade') or reserva.unidade_checkin or checkin.unidade
            unidade_esperada = reserva.unidade_checkin or checkin.unidade
            if unidade_esperada and unidade_enviada != unidade_esperada:
                raise serializers.ValidationError(MSG_CHECKOUT_UNIDADE)

            quilometragem_enviada = data.get('quilometragem')
            if quilometragem_enviada is None:
                raise serializers.ValidationError(
                    'Informe a quilometragem final (km) para concluir o check-out.'
                )

            km_inicial = checkin.quilometragem
            if km_inicial is None:
                km_inicial = veiculo.km_atual

            if km_inicial is not None and quilometragem_enviada < km_inicial:
                raise serializers.ValidationError(
                    f'A quilometragem final ({quilometragem_enviada} km) não pode ser menor que '
                    f'a quilometragem inicial ({km_inicial} km).'
                )

            if quilometragem_enviada < (veiculo.km_atual or 0):
                raise serializers.ValidationError(
                    f'A quilometragem final não pode ser menor que o KM atual '
                    f'do veículo ({veiculo.km_atual} km).'
                )
        else:
            raise serializers.ValidationError('Tipo de vistoria inválido.')

        aplicar_maiusculas(data, ['observacoes'])
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['realizada_por'] = request.user

        reserva = validated_data['reserva']
        tipo = validated_data['tipo']

        existente = Vistoria.objects.filter(reserva=reserva, tipo=tipo).first()
        if existente is not None:
            for campo, valor in validated_data.items():
                setattr(existente, campo, valor)
            existente.save()
            existente.fotos.all().delete()
            return existente

        return super().create(validated_data)
