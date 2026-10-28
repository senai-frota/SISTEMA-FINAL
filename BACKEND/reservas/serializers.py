from datetime import datetime, time, timedelta

from rest_framework import serializers
from django.utils import timezone

from usuarios.models import usuario_pode_reservar_com_cnh, resumo_cnh_usuario
from termos.models import usuario_possui_termo_valido
from termos.services_conta import sincronizar_status_conta, resumo_termo_usuario
from usuarios.text_utils import aplicar_maiusculas
from auditoria.services import exigir_justificativa
from .models import AutorizacaoCheckinAntecipado, Reserva

# Janela máxima: reserva até 14 dias à frente (inclusive).
ANTECEDENCIA_MAXIMA_DIAS = 14
MSG_ANTECEDENCIA = (
    'A reserva só pode ser feita para datas de até 14 dias à frente.'
)
MSG_PASSADO = 'A data de retirada não pode ser no passado.'
MSG_TURNO_ENCERRADO = 'Este turno já foi encerrado. Escolha outro turno ou data.'
MSG_CNH = (
    'É necessário possuir CNH aprovada e dentro da validade para solicitar uma reserva.'
)
MSG_PERNOITE_UNIDADE = (
    'Informe a unidade onde o veículo ficará durante o pernoite.'
)
MSG_PERNOITE_MESMO_DIA = (
    'Sem pernoite, a reserva deve começar e terminar no mesmo dia.'
)
MSG_PERNOITE_TURNO = (
    'Pernoite só é permitido com modalidade de horário personalizado.'
)
MSG_FIM_ANTECEDENCIA = (
    'A data de devolução não pode ultrapassar 14 dias à frente.'
)


def validar_janela_antecedencia(data_inicio, data_fim_turno=None):
    """
    data_inicio não pode ser no passado nem além de hoje+14 dias (calendário local).

    Em reserva por turno, o turno em andamento continua reservável até o seu fim;
    a disponibilidade real é decidida pela checagem de conflitos.
    """
    agora = timezone.now()
    if data_fim_turno is not None:
        if data_fim_turno <= agora:
            raise serializers.ValidationError({'turno': [MSG_TURNO_ENCERRADO]})
    elif data_inicio < agora:
        raise serializers.ValidationError({'data_inicio': [MSG_PASSADO]})

    data_retirada = timezone.localtime(data_inicio).date()
    data_maxima = timezone.localdate() + timedelta(days=ANTECEDENCIA_MAXIMA_DIAS)
    if data_retirada > data_maxima:
        raise serializers.ValidationError({'data_inicio': [MSG_ANTECEDENCIA]})


def validar_fim_dentro_janela(data_fim):
    data_devolucao = timezone.localtime(data_fim).date()
    data_maxima = timezone.localdate() + timedelta(days=ANTECEDENCIA_MAXIMA_DIAS)
    if data_devolucao > data_maxima:
        raise serializers.ValidationError({'data_fim': [MSG_FIM_ANTECEDENCIA]})


def validar_pernoite(data, modalidade):
    """
    Normaliza e valida campos de pernoite.
    Retorna (pernoite: bool, unidade_pernoite: str|None).
    """
    pernoite = bool(data.get('pernoite', False))
    unidade = data.get('unidade_pernoite') or ''
    if isinstance(unidade, str):
        unidade = unidade.strip()

    if pernoite:
        if modalidade == 'turno':
            raise serializers.ValidationError({'pernoite': [MSG_PERNOITE_TURNO]})
        if not unidade:
            raise serializers.ValidationError({
                'unidade_pernoite': [MSG_PERNOITE_UNIDADE],
            })
        data['unidade_pernoite'] = unidade
    else:
        data['unidade_pernoite'] = None
        data['pernoite'] = False

    data['pernoite'] = pernoite
    return pernoite


def validar_intervalo_dias(data_inicio, data_fim, pernoite):
    dia_inicio = timezone.localtime(data_inicio).date()
    dia_fim = timezone.localtime(data_fim).date()
    if dia_inicio != dia_fim and not pernoite:
        raise serializers.ValidationError({
            'pernoite': [MSG_PERNOITE_MESMO_DIA],
        })


def montar_intervalo_turno(data_ref, turno):
    """Converte data + turno nos datetimes de início/fim no fuso local."""
    if turno not in Reserva.TURNOS_HORARIOS:
        raise serializers.ValidationError({'turno': ['Turno inválido.']})
    h_ini, m_ini, h_fim, m_fim = Reserva.TURNOS_HORARIOS[turno]
    tz = timezone.get_current_timezone()
    if hasattr(data_ref, 'date'):
        dia = timezone.localtime(data_ref).date()
    else:
        dia = data_ref
    inicio = timezone.make_aware(datetime.combine(dia, time(h_ini, m_ini)), tz)
    fim = timezone.make_aware(datetime.combine(dia, time(h_fim, m_fim)), tz)
    return inicio, fim


def existem_conflitos(veiculo, data_inicio, data_fim, excluir_pk=None):
    qs = Reserva.objects.filter(
        veiculo=veiculo,
        status__in=['pendente', 'aprovada', 'em_andamento'],
        data_inicio__lt=data_fim,
        data_fim__gt=data_inicio,
    )
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    return qs.exists()


class ReservaListSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)
    usuario_matricula = serializers.CharField(source='usuario.matricula', read_only=True)
    veiculo_info = serializers.CharField(source='veiculo.__str__', read_only=True)
    veiculo_placa = serializers.CharField(source='veiculo.placa', read_only=True)
    admin_aprovador_nome = serializers.CharField(source='admin_aprovador.nome', read_only=True)
    turno_display = serializers.CharField(source='get_turno_display', read_only=True)
    modalidade_display = serializers.CharField(source='get_modalidade_display', read_only=True)
    unidade_checkin_display = serializers.CharField(
        source='get_unidade_checkin_display', read_only=True,
    )
    checkin_antecipado = serializers.SerializerMethodField()
    checkout_atrasado = serializers.SerializerMethodField()
    cancelamento_automatico = serializers.BooleanField(read_only=True)

    class Meta:
        model = Reserva
        fields = [
            'id', 'usuario', 'usuario_nome', 'usuario_matricula',
            'veiculo', 'veiculo_info', 'veiculo_placa',
            'data_inicio', 'data_fim', 'data_devolucao_real',
            'modalidade', 'modalidade_display', 'turno', 'turno_display',
            'motivo', 'destino', 'passageiros',
            'pernoite', 'unidade_pernoite',
            'unidade_checkin', 'unidade_checkin_display',
            'status', 'admin_aprovador', 'admin_aprovador_nome',
            'data_aprovacao', 'observacao_admin', 'motivo_cancelamento',
            'cancelamento_automatico', 'checkin_antecipado', 'checkout_atrasado',
            'criado_em', 'atualizado_em'
        ]
        read_only_fields = [
            'id', 'usuario', 'status', 'admin_aprovador',
            'data_aprovacao', 'unidade_checkin', 'motivo_cancelamento',
            'criado_em', 'atualizado_em'
        ]

    def get_checkin_antecipado(self, obj):
        auts = list(obj.autorizacoes_checkin.all())
        if not auts:
            return None
        pendente = next((a for a in auts if a.status == 'pendente'), None)
        aprovada = next((a for a in auts if a.status == 'aprovada'), None)
        atual = pendente or aprovada or max(auts, key=lambda a: a.pk)
        return {
            'id': atual.id,
            'status': atual.status,
            'justificativa': atual.justificativa,
            'observacao_admin': atual.observacao_admin,
            'admin_nome': atual.admin_decisor.nome if atual.admin_decisor_id else None,
            'criado_em': atual.criado_em,
            'decidido_em': atual.decidido_em,
        }

    def get_checkout_atrasado(self, obj):
        from vistorias.regras import checkout_esta_atrasado

        return checkout_esta_atrasado(obj)


class ReservaCreateSerializer(serializers.ModelSerializer):
    data = serializers.DateField(
        required=False,
        write_only=True,
        help_text='Data do dia da reserva (obrigatória com modalidade turno).',
    )

    class Meta:
        model = Reserva
        fields = [
            'veiculo', 'data_inicio', 'data_fim',
            'modalidade', 'turno', 'data',
            'motivo', 'destino', 'passageiros',
            'pernoite', 'unidade_pernoite',
        ]
        extra_kwargs = {
            'data_inicio': {'required': False},
            'data_fim': {'required': False},
            'modalidade': {'required': False},
            'turno': {'required': False},
            'pernoite': {'required': False},
            'unidade_pernoite': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate(self, data):
        request = self.context['request']
        sincronizar_status_conta(request.user)
        request.user.refresh_from_db(fields=['is_active'])

        if not request.user.is_active and not request.user.is_admin:
            resumo = resumo_termo_usuario(request.user)
            raise serializers.ValidationError({
                'non_field_errors': [
                    resumo.get('mensagem')
                    or 'Sua conta está inativa. Renove o termo de responsabilidade.'
                ],
            })

        if not usuario_possui_termo_valido(request.user) and not request.user.is_admin:
            resumo = resumo_termo_usuario(request.user)
            raise serializers.ValidationError({
                'non_field_errors': [
                    resumo.get('mensagem')
                    or 'É necessário um termo de responsabilidade válido para reservar.'
                ],
            })

        if not usuario_pode_reservar_com_cnh(request.user):
            resumo = resumo_cnh_usuario(request.user)
            raise serializers.ValidationError({
                'non_field_errors': [resumo.get('mensagem') or MSG_CNH],
            })

        modalidade = data.get('modalidade') or 'horario'
        data['modalidade'] = modalidade

        if modalidade == 'turno':
            turno = data.get('turno')
            if not turno:
                raise serializers.ValidationError({'turno': ['Selecione um turno.']})
            data_dia = data.get('data')
            if not data_dia:
                if data.get('data_inicio'):
                    data_dia = timezone.localtime(data['data_inicio']).date()
                else:
                    raise serializers.ValidationError({
                        'data': ['Informe a data da reserva para o turno.'],
                    })
            inicio, fim = montar_intervalo_turno(data_dia, turno)
            data['data_inicio'] = inicio
            data['data_fim'] = fim
            data['turno'] = turno
        else:
            data['turno'] = None
            if not data.get('data_inicio') or not data.get('data_fim'):
                raise serializers.ValidationError(
                    'Informe data/hora de início e fim para horário personalizado.'
                )

        data.pop('data', None)

        if data['data_inicio'] >= data['data_fim']:
            raise serializers.ValidationError(
                'A data/hora de retirada deve ser anterior à de devolução.'
            )

        validar_janela_antecedencia(
            data['data_inicio'],
            data_fim_turno=data['data_fim'] if modalidade == 'turno' else None,
        )
        validar_fim_dentro_janela(data['data_fim'])

        pernoite = validar_pernoite(data, modalidade)
        validar_intervalo_dias(data['data_inicio'], data['data_fim'], pernoite)

        veiculo = data['veiculo']
        if veiculo.status in ('manutencao', 'inativo'):
            raise serializers.ValidationError(
                f'O veículo {veiculo} não está disponível '
                f'(status: {veiculo.get_status_display()}).'
            )

        if existem_conflitos(veiculo, data['data_inicio'], data['data_fim']):
            raise serializers.ValidationError(
                'Este veículo já possui uma reserva no período solicitado.'
            )

        aplicar_maiusculas(data, ['motivo', 'destino', 'unidade_pernoite'])
        return data

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)


class ReservaUpdateSerializer(serializers.ModelSerializer):
    data = serializers.DateField(required=False, write_only=True)

    class Meta:
        model = Reserva
        fields = [
            'data_inicio', 'data_fim', 'modalidade', 'turno', 'data',
            'motivo', 'destino', 'passageiros',
            'pernoite', 'unidade_pernoite',
        ]
        extra_kwargs = {
            'data_inicio': {'required': False},
            'data_fim': {'required': False},
            'modalidade': {'required': False},
            'turno': {'required': False},
            'pernoite': {'required': False},
            'unidade_pernoite': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def validate(self, data):
        instance = self.instance
        modalidade = data.get('modalidade', instance.modalidade)

        if modalidade == 'turno':
            turno = data.get('turno', instance.turno)
            if not turno:
                raise serializers.ValidationError({'turno': ['Selecione um turno.']})
            data_dia = data.get('data')
            if data_dia is None:
                base = data.get('data_inicio', instance.data_inicio)
                data_dia = timezone.localtime(base).date()
            inicio, fim = montar_intervalo_turno(data_dia, turno)
            data['data_inicio'] = inicio
            data['data_fim'] = fim
            data['turno'] = turno
            data['modalidade'] = 'turno'
        else:
            data['modalidade'] = 'horario'
            data['turno'] = None
            data_inicio = data.get('data_inicio', instance.data_inicio)
            data_fim = data.get('data_fim', instance.data_fim)
            data['data_inicio'] = data_inicio
            data['data_fim'] = data_fim

        data.pop('data', None)

        if data['data_inicio'] >= data['data_fim']:
            raise serializers.ValidationError(
                'A data/hora de retirada deve ser anterior à de devolução.'
            )

        validar_janela_antecedencia(
            data['data_inicio'],
            data_fim_turno=data['data_fim'] if data['modalidade'] == 'turno' else None,
        )
        validar_fim_dentro_janela(data['data_fim'])

        if 'pernoite' not in data:
            data['pernoite'] = instance.pernoite
        if 'unidade_pernoite' not in data:
            data['unidade_pernoite'] = instance.unidade_pernoite

        pernoite = validar_pernoite(data, modalidade)
        validar_intervalo_dias(data['data_inicio'], data['data_fim'], pernoite)

        if existem_conflitos(
            instance.veiculo,
            data['data_inicio'],
            data['data_fim'],
            excluir_pk=instance.pk,
        ):
            raise serializers.ValidationError(
                'Este veículo já possui uma reserva no período solicitado.'
            )

        aplicar_maiusculas(data, ['motivo', 'destino', 'unidade_pernoite'])
        return data


class ReservaAprovacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = ['status', 'observacao_admin']
        extra_kwargs = {
            'status': {'required': True},
        }

    def validate_status(self, value):
        if value not in ['aprovada', 'negada']:
            raise serializers.ValidationError(
                'O status deve ser "aprovada" ou "negada".'
            )
        return value

    def validate(self, data):
        instance = self.instance
        if instance is None:
            return data
        if instance.status == 'cancelada':
            raise serializers.ValidationError(
                'Não é possível analisar uma reserva cancelada.'
            )
        if instance.status != 'pendente':
            raise serializers.ValidationError(
                'Somente reservas pendentes podem ser aprovadas ou rejeitadas.'
            )
        if data.get('status') == 'negada':
            data['observacao_admin'] = exigir_justificativa(data.get('observacao_admin'))
        if data.get('status') == 'aprovada':
            if existem_conflitos(
                instance.veiculo,
                instance.data_inicio,
                instance.data_fim,
                excluir_pk=instance.pk,
            ):
                raise serializers.ValidationError(
                    'Não é possível aprovar: já existe outra reserva neste horário.'
                )
        aplicar_maiusculas(data, ['observacao_admin'])
        return data

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.observacao_admin = validated_data.get(
            'observacao_admin', instance.observacao_admin
        )
        instance.admin_aprovador = self.context['request'].user
        instance.data_aprovacao = timezone.now()
        instance.save()
        # Aprovação NÃO altera o status do veículo.
        # EM USO ocorre somente no check-in.
        return instance


class AutorizacaoCheckinSerializer(serializers.ModelSerializer):
    solicitante_nome = serializers.CharField(source='solicitante.nome', read_only=True)
    admin_nome = serializers.CharField(source='admin_decisor.nome', read_only=True)
    reserva_info = ReservaListSerializer(source='reserva', read_only=True)

    class Meta:
        model = AutorizacaoCheckinAntecipado
        fields = [
            'id', 'reserva', 'reserva_info', 'solicitante', 'solicitante_nome',
            'justificativa', 'status', 'admin_decisor', 'admin_nome',
            'observacao_admin', 'criado_em', 'decidido_em',
        ]
        read_only_fields = [
            'id', 'solicitante', 'status', 'admin_decisor',
            'criado_em', 'decidido_em',
        ]


class AutorizacaoCheckinCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutorizacaoCheckinAntecipado
        fields = ['justificativa']

    def validate_justificativa(self, value):
        texto = (value or '').strip()
        if not texto:
            raise serializers.ValidationError('Informe a justificativa do check-in antecipado.')
        return texto


class AutorizacaoCheckinDecisaoSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['aprovada', 'rejeitada'])
    observacao_admin = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        if data['status'] == 'rejeitada':
            data['observacao_admin'] = exigir_justificativa(
                data.get('observacao_admin'), campo='observacao_admin',
            )
        aplicar_maiusculas(data, ['observacao_admin'])
        return data
