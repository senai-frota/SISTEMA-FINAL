import calendar as calendar_module
from datetime import date, timedelta

from rest_framework import generics, permissions, status, filters
from usuarios.permissions import AuthenticatedAndPasswordSet
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from .models import (
    MOTIVO_CANCELAMENTO_ADMIN,
    MOTIVO_CANCELAMENTO_USUARIO,
    AutorizacaoCheckinAntecipado,
    Reserva,
)
from .serializers import (
    ReservaListSerializer, ReservaCreateSerializer,
    ReservaUpdateSerializer, ReservaAprovacaoSerializer,
    AutorizacaoCheckinSerializer, AutorizacaoCheckinCreateSerializer,
    AutorizacaoCheckinDecisaoSerializer,
    existem_conflitos,
)
from veiculos.models import Veiculo
from auditoria.services import exigir_justificativa, registrar
from usuarios.text_utils import para_maiusculas

MSG_ADMIN_NAO_RESERVA = 'Administradores não podem solicitar reservas de veículos.'


class DisponibilidadeReservaView(APIView):
    """
    GET /api/reservas/disponibilidade/?veiculo=&data_inicio=&data_fim=

    Indica se o intervalo está livre (sem sobreposição com reservas ativas).
    """
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request):
        veiculo_id = request.query_params.get('veiculo')
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        if not veiculo_id or not data_inicio or not data_fim:
            return Response(
                {'detail': 'Informe veiculo, data_inicio e data_fim.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            veiculo = Veiculo.objects.get(pk=veiculo_id)
        except (Veiculo.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'Veículo não encontrado.'}, status=404)

        from django.utils.dateparse import parse_datetime
        inicio = parse_datetime(data_inicio)
        fim = parse_datetime(data_fim)
        if inicio is None or fim is None:
            return Response(
                {'detail': 'Datas inválidas. Use ISO 8601.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio, timezone.get_current_timezone())
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim, timezone.get_current_timezone())

        conflito = existem_conflitos(veiculo, inicio, fim)
        bloqueado_status = veiculo.status in ('manutencao', 'inativo')
        return Response({
            'veiculo': veiculo.id,
            'data_inicio': inicio,
            'data_fim': fim,
            'disponivel': (not conflito) and (not bloqueado_status),
            'conflito_horario': conflito,
            'status_veiculo': veiculo.status,
        })


class ReservaListCreateView(generics.ListCreateAPIView):
    permission_classes = AuthenticatedAndPasswordSet
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'veiculo']
    ordering_fields = ['data_inicio', 'criado_em']
    ordering = ['-criado_em']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReservaCreateSerializer
        return ReservaListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Reserva.objects.select_related(
            'usuario', 'veiculo', 'admin_aprovador',
        ).prefetch_related('autorizacoes_checkin__admin_decisor')
        if user.is_admin:
            return qs
        return qs.filter(usuario=user)

    def create(self, request, *args, **kwargs):
        if request.user.is_admin:
            raise PermissionDenied(MSG_ADMIN_NAO_RESERVA)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        reserva = serializer.save()
        registrar(
            ator=self.request.user,
            acao='criar_reserva',
            entidade='reserva',
            entidade_id=reserva.id,
            identificacao=f'Reserva #{reserva.id} · {reserva.veiculo.placa}',
            descricao=f'{reserva.usuario.nome} solicitou o veículo {reserva.veiculo.placa}.',
            detalhes={'destino': reserva.destino or '', 'status': reserva.status},
        )


class ReservaDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = AuthenticatedAndPasswordSet

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ReservaUpdateSerializer
        return ReservaListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Reserva.objects.select_related(
            'usuario', 'veiculo', 'admin_aprovador',
        ).prefetch_related('autorizacoes_checkin__admin_decisor')
        if user.is_admin:
            return qs
        return qs.filter(usuario=user)

    def perform_update(self, serializer):
        reserva = self.get_object()
        # Só pode editar se estiver pendente
        if not reserva.pode_editar():
            raise PermissionDenied(
                'Só é possível editar reservas com status "Pendente".'
            )
        # Usuário comum só edita a própria reserva
        if not self.request.user.is_admin and reserva.usuario != self.request.user:
            raise PermissionDenied(
                'Você não tem permissão para editar esta reserva.'
            )
        serializer.save()

    def perform_destroy(self, instance):
        if not instance.pode_cancelar():
            raise PermissionDenied(
                'Só é possível cancelar reservas com status "Pendente" ou "Aprovada".'
            )
        if not self.request.user.is_admin and instance.usuario != self.request.user:
            raise PermissionDenied(
                'Você não tem permissão para cancelar esta reserva.'
            )
        cancelada_por_admin = instance.usuario_id != self.request.user.id
        justificativa = ''
        campos = ['status', 'motivo_cancelamento', 'atualizado_em']
        if cancelada_por_admin:
            justificativa = para_maiusculas(
                exigir_justificativa(self.request.data.get('justificativa'), campo='justificativa')
            )
            instance.observacao_admin = justificativa
            instance.motivo_cancelamento = MOTIVO_CANCELAMENTO_ADMIN
            campos.append('observacao_admin')
        else:
            instance.motivo_cancelamento = MOTIVO_CANCELAMENTO_USUARIO
        estava_aprovada = instance.status == 'aprovada'
        instance.status = 'cancelada'
        instance.save(update_fields=campos)

        if estava_aprovada:
            from .models import Reserva as ReservaModel
            outras_ativas = ReservaModel.objects.filter(
                veiculo=instance.veiculo,
                status__in=['aprovada', 'em_andamento'],
            ).exclude(pk=instance.pk).exists()
            if not outras_ativas and instance.veiculo.status == 'em_uso':
                instance.veiculo.status = 'disponivel'
                instance.veiculo.save(update_fields=['status', 'atualizado_em'])
        registrar(
            ator=self.request.user,
            acao='cancelar_reserva',
            entidade='reserva',
            entidade_id=instance.id,
            identificacao=f'Reserva #{instance.id} · {instance.veiculo.placa}',
            descricao=(
                f'A reserva #{instance.id} do veículo {instance.veiculo.placa} '
                f'de {instance.usuario.nome} foi cancelada pelo administrador.'
                if cancelada_por_admin else
                f'A reserva #{instance.id} do veículo {instance.veiculo.placa} foi cancelada.'
            ),
            justificativa=justificativa,
            usuario_afetado=instance.usuario,
        )


class ReservaAprovacaoView(generics.UpdateAPIView):
    """
    PATCH /api/reservas/<id>/aprovar/
    Apenas admin. Aprova ou rejeita (negada) uma reserva pendente.
    """
    queryset = Reserva.objects.all()
    serializer_class = ReservaAprovacaoSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def update(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem aprovar ou rejeitar reservas.'
            )
        return super().update(request, *args, **kwargs)

    def get_object(self):
        obj = super().get_object()
        if obj.status == 'cancelada':
            raise PermissionDenied(
                'Não é possível analisar uma reserva cancelada.'
            )
        if obj.status != 'pendente':
            raise PermissionDenied(
                'Só é possível aprovar ou rejeitar reservas com status "Pendente".'
            )
        return obj

    def perform_update(self, serializer):
        reserva = serializer.save()
        aprovada = reserva.status == 'aprovada'
        registrar(
            ator=self.request.user,
            acao='aprovar_reserva' if aprovada else 'rejeitar_reserva',
            entidade='reserva',
            entidade_id=reserva.id,
            identificacao=f'Reserva #{reserva.id} · {reserva.veiculo.placa}',
            descricao=(
                f'A reserva #{reserva.id} do veículo {reserva.veiculo.placa} foi '
                f'{"aprovada" if aprovada else "rejeitada"}.'
            ),
            justificativa='' if aprovada else reserva.observacao_admin,
            usuario_afetado=reserva.usuario,
        )


class RelatorioCalendarioReservasView(APIView):
    """
    GET /api/reservas/relatorio/calendario/?mes=9&ano=2026

    Relatório para montar um calendário indicando, dia a dia, quantas
    reservas estavam em uso naquele dia (contando também reservas que
    atravessam mais de um dia) e um nível de movimento (sem_reservas /
    baixa / media / alta) relativo ao dia de maior movimento do mês,
    para facilitar a coloração do calendário no front-end.

    Parâmetros opcionais:
      - mes: 1-12 (padrão: mês atual)
      - ano: ano com 4 dígitos (padrão: ano atual)

    Apenas administradores têm acesso a este relatório.
    """
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request):
        if not request.user.is_admin:
            return Response(
                {'detail': 'Apenas administradores podem acessar este relatório.'},
                status=status.HTTP_403_FORBIDDEN
            )

        hoje = timezone.localdate()
        try:
            mes = int(request.query_params.get('mes', hoje.month))
            ano = int(request.query_params.get('ano', hoje.year))
        except ValueError:
            return Response(
                {'detail': 'Os parâmetros "mes" e "ano" devem ser números inteiros.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if mes < 1 or mes > 12:
            return Response(
                {'detail': 'O parâmetro "mes" deve estar entre 1 e 12.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        primeiro_dia = date(ano, mes, 1)
        ultimo_dia_num = calendar_module.monthrange(ano, mes)[1]
        ultimo_dia = date(ano, mes, ultimo_dia_num)

        # Considera reservas que tenham qualquer interseção com o mês
        # (inclui reservas em andamento/concluídas que começaram antes
        # ou terminam depois do mês consultado).
        status_relevantes = ['pendente', 'aprovada', 'em_andamento', 'concluida']
        reservas_no_periodo = Reserva.objects.filter(
            status__in=status_relevantes,
            data_inicio__date__lte=ultimo_dia,
            data_fim__date__gte=primeiro_dia,
        )

        # Inicializa a contagem de todos os dias do mês com zero
        contagem_por_dia = {}
        dia_cursor = primeiro_dia
        while dia_cursor <= ultimo_dia:
            contagem_por_dia[dia_cursor] = 0
            dia_cursor += timedelta(days=1)

        # Para cada reserva, soma 1 em cada dia do mês que ela ocupa
        for reserva in reservas_no_periodo:
            inicio = max(reserva.data_inicio.date(), primeiro_dia)
            fim = min(reserva.data_fim.date(), ultimo_dia)
            dia_cursor = inicio
            while dia_cursor <= fim:
                contagem_por_dia[dia_cursor] += 1
                dia_cursor += timedelta(days=1)

        maximo = max(contagem_por_dia.values()) if contagem_por_dia else 0

        def classificar(quantidade):
            if quantidade == 0 or maximo == 0:
                return 'sem_reservas'
            proporcao = quantidade / maximo
            if proporcao <= 0.33:
                return 'baixa'
            if proporcao <= 0.66:
                return 'media'
            return 'alta'

        dias_semana = [
            'Segunda-feira', 'Terça-feira', 'Quarta-feira',
            'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
        ]

        dias = [
            {
                'data': dia.isoformat(),
                'dia_semana': dias_semana[dia.weekday()],
                'total_reservas': quantidade,
                'nivel': classificar(quantidade),
            }
            for dia, quantidade in sorted(contagem_por_dia.items())
        ]

        total_reservas_no_periodo = sum(contagem_por_dia.values())
        dia_com_mais_reservas = max(dias, key=lambda d: d['total_reservas']) if dias else None
        media_diaria = round(total_reservas_no_periodo / len(dias), 2) if dias else 0

        return Response({
            'mes': mes,
            'ano': ano,
            'total_dias': len(dias),
            'total_reservas_no_periodo': total_reservas_no_periodo,
            'media_diaria': media_diaria,
            'dia_com_mais_reservas': dia_com_mais_reservas,
            'dias': dias,
        })


def _vistoria_com_fotos(reserva, tipo):
    """Retorna a vistoria do tipo indicado se existir e tiver ao menos 1 foto."""
    from vistorias.models import Vistoria

    vistoria = Vistoria.objects.filter(reserva=reserva, tipo=tipo).first()
    if vistoria is None or not vistoria.fotos.exists():
        return None
    return vistoria


@api_view(['POST'])
@permission_classes(AuthenticatedAndPasswordSet)
def iniciar_reserva(request, pk):
    """
    POST /api/reservas/<id>/iniciar/

    Endpoint legado. Mantido por compatibilidade: só altera o status
    para em_andamento se já existir vistoria de check-in com fotos.
    O fluxo atual do frontend usa POST /api/vistorias/registrar/.
    """
    from vistorias.dispositivo import exigir_cliente_mobile
    exigir_cliente_mobile(request)

    try:
        reserva = Reserva.objects.get(pk=pk)
    except Reserva.DoesNotExist:
        return Response(
            {'detail': 'Reserva não encontrada.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # O check-in pertence exclusivamente ao dono da reserva.
    if reserva.usuario != request.user:
        return Response(
            {'detail': 'Apenas o solicitante da reserva pode realizar o check-in.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if reserva.status != 'aprovada':
        return Response(
            {'detail': 'Só é possível iniciar reservas aprovadas.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Impede pular a vistoria: iniciar sem check-in deixava a reserva
    # em_andamento sem fotos/km, inconsistente com /vistorias/registrar/.
    if _vistoria_com_fotos(reserva, 'checkin') is None:
        return Response(
            {
                'detail': (
                    'É necessário registrar a vistoria de check-in com fotos '
                    'antes de iniciar a reserva. Use POST /api/vistorias/registrar/.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    reserva.status = 'em_andamento'
    reserva.save(update_fields=['status', 'atualizado_em'])

    veiculo = reserva.veiculo
    if veiculo.status == 'disponivel':
        veiculo.status = 'em_uso'
        veiculo.save(update_fields=['status', 'atualizado_em'])

    serializer = ReservaListSerializer(reserva)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes(AuthenticatedAndPasswordSet)
def finalizar_reserva(request, pk):
    """
    POST /api/reservas/<id>/finalizar/

    Endpoint legado. Mantido por compatibilidade: só conclui a reserva
    se já existir vistoria de check-out com fotos.
    O fluxo atual do frontend usa POST /api/vistorias/registrar/.
    """
    from vistorias.dispositivo import exigir_cliente_mobile
    exigir_cliente_mobile(request)

    try:
        reserva = Reserva.objects.get(pk=pk)
    except Reserva.DoesNotExist:
        return Response(
            {'detail': 'Reserva não encontrada.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # O check-out pertence exclusivamente ao dono da reserva.
    if reserva.usuario != request.user:
        return Response(
            {'detail': 'Apenas o solicitante da reserva pode realizar o check-out.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if reserva.status != 'em_andamento':
        return Response(
            {'detail': 'Só é possível finalizar reservas em andamento.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if _vistoria_com_fotos(reserva, 'checkout') is None:
        return Response(
            {
                'detail': (
                    'É necessário registrar a vistoria de check-out com fotos '
                    'antes de finalizar a reserva. Use POST /api/vistorias/registrar/.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    from vistorias.models import Vistoria
    checkout = Vistoria.objects.filter(reserva=reserva, tipo='checkout').first()

    with transaction.atomic():
        veiculo = Veiculo.objects.select_for_update().get(pk=reserva.veiculo_id)
        if checkout and checkout.quilometragem is not None:
            if checkout.quilometragem < (veiculo.km_atual or 0):
                return Response(
                    {
                        'detail': (
                            f'A quilometragem final não pode ser menor que o KM atual '
                            f'do veículo ({veiculo.km_atual} km).'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            veiculo.km_atual = checkout.quilometragem
        veiculo.status = 'disponivel'
        veiculo.save(update_fields=['km_atual', 'status', 'atualizado_em'])

        reserva.status = 'concluida'
        reserva.data_devolucao_real = timezone.now()
        reserva.save(update_fields=['status', 'data_devolucao_real', 'atualizado_em'])

    serializer = ReservaListSerializer(reserva)
    return Response(serializer.data)


class AlertasOperacionaisView(APIView):
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request):
        from .operacoes import listar_alertas_operacionais

        return Response(listar_alertas_operacionais(request.user))


@api_view(['POST'])
@permission_classes(AuthenticatedAndPasswordSet)
def solicitar_checkin_antecipado(request, pk):
    from vistorias.regras import agora_local, janela_reserva_com_tolerancia

    try:
        reserva = Reserva.objects.select_related('usuario', 'veiculo').get(pk=pk)
    except Reserva.DoesNotExist:
        return Response({'detail': 'Reserva não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if reserva.usuario != request.user:
        return Response(
            {'detail': 'Apenas o solicitante da reserva pode pedir check-in antecipado.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if reserva.status != 'aprovada':
        return Response(
            {'detail': 'Só é possível antecipar o check-in de reservas aprovadas.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    inicio_tol, fim_tol = janela_reserva_com_tolerancia(reserva)
    agora = agora_local()
    if agora > fim_tol:
        return Response(
            {'detail': 'O prazo de check-in desta reserva já encerrou.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if agora >= inicio_tol:
        return Response(
            {'detail': 'O check-in já está dentro da janela permitida. Não é necessário antecipar.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if AutorizacaoCheckinAntecipado.objects.filter(reserva=reserva, status='aprovada').exists():
        return Response(
            {'detail': 'Esta reserva já possui autorização de check-in antecipado.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if AutorizacaoCheckinAntecipado.objects.filter(reserva=reserva, status='pendente').exists():
        return Response(
            {'detail': 'Já existe uma solicitação de check-in antecipado aguardando decisão.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = AutorizacaoCheckinCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    autorizacao = AutorizacaoCheckinAntecipado.objects.create(
        reserva=reserva,
        solicitante=request.user,
        justificativa=para_maiusculas(serializer.validated_data['justificativa']),
    )
    registrar(
        ator=request.user,
        acao='solicitar_checkin_antecipado',
        entidade='reserva',
        entidade_id=reserva.id,
        identificacao=f'Reserva #{reserva.id} · {reserva.veiculo.placa}',
        descricao=(
            f'{request.user.nome} solicitou autorização para check-in antecipado '
            f'da reserva #{reserva.id}.'
        ),
        detalhes={'autorizacao_id': autorizacao.id},
    )
    return Response(
        AutorizacaoCheckinSerializer(autorizacao).data,
        status=status.HTTP_201_CREATED,
    )


class AutorizacaoCheckinListView(generics.ListAPIView):
    permission_classes = AuthenticatedAndPasswordSet
    serializer_class = AutorizacaoCheckinSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'reserva']

    def get_queryset(self):
        qs = AutorizacaoCheckinAntecipado.objects.select_related(
            'reserva__usuario', 'reserva__veiculo', 'solicitante', 'admin_decisor',
        )
        if self.request.user.is_admin:
            return qs
        return qs.filter(solicitante=self.request.user)


@api_view(['PATCH'])
@permission_classes(AuthenticatedAndPasswordSet)
def decidir_checkin_antecipado(request, pk):
    if not request.user.is_admin:
        return Response(
            {'detail': 'Apenas administradores podem decidir o check-in antecipado.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        autorizacao = AutorizacaoCheckinAntecipado.objects.select_related(
            'reserva__usuario', 'reserva__veiculo', 'solicitante',
        ).get(pk=pk)
    except AutorizacaoCheckinAntecipado.DoesNotExist:
        return Response({'detail': 'Solicitação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if autorizacao.status != 'pendente':
        return Response(
            {
                'detail': (
                    'Esta solicitação já foi decidida. '
                    f'Status atual: {autorizacao.get_status_display()}.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = AutorizacaoCheckinDecisaoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    aprovada = serializer.validated_data['status'] == 'aprovada'
    autorizacao.status = serializer.validated_data['status']
    autorizacao.observacao_admin = serializer.validated_data.get('observacao_admin') or ''
    autorizacao.admin_decisor = request.user
    autorizacao.decidido_em = timezone.now()
    autorizacao.save(update_fields=[
        'status', 'observacao_admin', 'admin_decisor', 'decidido_em',
    ])
    registrar(
        ator=request.user,
        acao='aprovar_checkin_antecipado' if aprovada else 'rejeitar_checkin_antecipado',
        entidade='reserva',
        entidade_id=autorizacao.reserva_id,
        identificacao=f'Reserva #{autorizacao.reserva_id} · {autorizacao.reserva.veiculo.placa}',
        descricao=(
            f'A solicitação de check-in antecipado da reserva #{autorizacao.reserva_id} '
            f'foi {"aprovada" if aprovada else "rejeitada"}.'
        ),
        justificativa='' if aprovada else autorizacao.observacao_admin,
        usuario_afetado=autorizacao.solicitante,
        detalhes={'autorizacao_id': autorizacao.id, 'status': autorizacao.status},
    )
    return Response(AutorizacaoCheckinSerializer(autorizacao).data)