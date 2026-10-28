import logging
import time

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from usuarios.permissions import AuthenticatedAndPasswordSet
from auditoria.services import registrar
from veiculos.models import Veiculo
from .dispositivo import exigir_cliente_mobile, validar_fotos_obrigatorias
from .models import Vistoria, FotoVistoria
from .serializers import (
    VistoriaSerializer, VistoriaCreateSerializer,
    FotoVistoriaSerializer, FotoUploadSerializer
)

logger = logging.getLogger('vistorias.desempenho')

MAX_FOTOS_POR_VISTORIA = 5


class VistoriaListCreateView(generics.ListCreateAPIView):
    queryset = Vistoria.objects.all()
    permission_classes = AuthenticatedAndPasswordSet
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reserva', 'tipo', 'unidade']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VistoriaCreateSerializer
        return VistoriaSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Vistoria.objects.all()
        # Usuário comum vê só as vistorias das próprias reservas
        return Vistoria.objects.filter(reserva__usuario=user)


class VistoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Vistoria.objects.all()
    serializer_class = VistoriaSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Vistoria.objects.all()
        return Vistoria.objects.filter(reserva__usuario=user)

    def perform_destroy(self, instance):
        if not self.request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem remover vistorias.'
            )
        instance.delete()


class FotoVistoriaListCreateView(generics.ListCreateAPIView):
    queryset = FotoVistoria.objects.all()
    serializer_class = FotoVistoriaSerializer
    permission_classes = AuthenticatedAndPasswordSet
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return FotoVistoria.objects.all()
        return FotoVistoria.objects.filter(vistoria__reserva__usuario=user)

    def perform_create(self, serializer):
        vistoria_id = self.request.data.get('vistoria')
        try:
            vistoria = Vistoria.objects.get(pk=vistoria_id)
        except (Vistoria.DoesNotExist, ValueError, TypeError):
            raise PermissionDenied('Vistoria não encontrada.')

        # Verifica permissão
        if not self.request.user.is_admin and vistoria.reserva.usuario != self.request.user:
            raise PermissionDenied(
                'Você só pode adicionar fotos às suas próprias vistorias.'
            )

        serializer.save(vistoria=vistoria)
        registrar(
            ator=self.request.user,
            acao='enviar_foto',
            entidade='vistoria',
            entidade_id=vistoria.id,
            identificacao=f'Vistoria #{vistoria.id}',
            descricao=f'Uma foto foi enviada para a vistoria #{vistoria.id}.',
        )


class FotoVistoriaDetailView(generics.RetrieveDestroyAPIView):
    queryset = FotoVistoria.objects.all()
    serializer_class = FotoVistoriaSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return FotoVistoria.objects.all()
        return FotoVistoria.objects.filter(vistoria__reserva__usuario=user)

    def perform_destroy(self, instance):
        if not self.request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem remover fotos.'
            )
        instance.delete()


def _salvar_fotos(vistoria, arquivos, descricoes, observacoes):
    """Cria os registros de FotoVistoria para uma vistoria."""
    criadas = []
    for i, arquivo in enumerate(arquivos):
        descricao = descricoes[i] if i < len(descricoes) else None
        observacao = observacoes[i] if i < len(observacoes) else None
        criadas.append(
            FotoVistoria.objects.create(
                vistoria=vistoria,
                foto=arquivo,
                descricao=descricao or None,
                observacao=observacao or None,
            )
        )
    return criadas


@api_view(['GET'])
@permission_classes(AuthenticatedAndPasswordSet)
def ultima_quilometragem(request):
    """
    GET /api/vistorias/ultima-quilometragem/?veiculo=<id>&reserva=<id>

    Devolve a quilometragem que será herdada como km inicial do próximo
    check-in deste veículo — ou seja, o km final do último check-out
    registrado (de qualquer usuário).

    Existe para que o formulário de check-in consiga MOSTRAR o valor já
    preenchido, em vez de o usuário digitar um número que o servidor vai
    descartar. `reserva` é opcional e exclui do cálculo os registros da
    própria reserva.

    Resposta:
      {
        "veiculo": 3,
        "quilometragem": 13480,      // null no primeiro uso do veículo
        "tipo_origem": "checkout",   // ou "checkin"
        "data_hora": "...",
        "primeiro_uso": false
      }
    """
    veiculo_id = request.query_params.get('veiculo')
    if not veiculo_id:
        return Response(
            {'detail': 'Informe o parâmetro "veiculo".'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        veiculo = Veiculo.objects.get(pk=veiculo_id)
    except (Veiculo.DoesNotExist, ValueError, TypeError):
        return Response(
            {'detail': 'Veículo não encontrado.'},
            status=status.HTTP_404_NOT_FOUND
        )

    reserva_id = request.query_params.get('reserva') or None
    try:
        reserva_id = int(reserva_id) if reserva_id else None
    except (ValueError, TypeError):
        reserva_id = None

    registro = Vistoria.get_ultimo_registro_quilometragem(
        veiculo, excluir_reserva_id=reserva_id
    )

    return Response({
        'veiculo': veiculo.pk,
        'quilometragem': veiculo.km_atual if veiculo.km_atual else (
            registro.quilometragem if registro else None
        ),
        'km_atual_veiculo': veiculo.km_atual,
        'tipo_origem': 'veiculo' if veiculo.km_atual else (registro.tipo if registro else None),
        'data_hora': registro.data_hora if registro else None,
        'primeiro_uso': (veiculo.km_atual or 0) == 0 and registro is None,
    })


@api_view(['POST'])
@permission_classes(AuthenticatedAndPasswordSet)
@parser_classes([MultiPartParser, FormParser, JSONParser])
def registrar_vistoria(request):
    """
    POST /api/vistorias/registrar/   (multipart/form-data)

    Registra o check-in ou o check-out INTEIRO em uma única requisição
    atômica: cria (ou reaproveita) a vistoria, grava as fotos e atualiza
    o status da reserva.

    Se qualquer etapa falhar, NADA é gravado (transaction.atomic) — o
    usuário pode simplesmente tentar de novo, sem ficar preso ao erro
    "Os campos reserva, tipo devem criar um set único".

    Campos:
      - reserva (id), tipo (checkin|checkout), unidade, quilometragem,
        observacoes
      - latitude / longitude / precisao_metros (opcionais)
      - fotos: exatamente 5 arquivos (frente, tras, laterais, painel)
      - descricoes: ângulo de cada foto (obrigatório, mesma ordem)
      - observacoes_fotos: observação de cada foto (opcional, mesma ordem)

    Somente dispositivos móveis (smartphone/tablet) podem registrar.
    """
    t0 = time.monotonic()
    exigir_cliente_mobile(request)

    arquivos = request.FILES.getlist('fotos')
    if not arquivos:
        return Response(
            {'detail': 'Adicione as fotos obrigatórias da vistoria.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if len(arquivos) > MAX_FOTOS_POR_VISTORIA:
        return Response(
            {'detail': f'Envie no máximo {MAX_FOTOS_POR_VISTORIA} fotos por vistoria.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    getlist = getattr(request.data, 'getlist', None)
    descricoes = list(getlist('descricoes') if getlist else [])
    observacoes_fotos = list(getlist('observacoes_fotos') if getlist else [])

    try:
        validar_fotos_obrigatorias(arquivos, descricoes)
    except ValidationError as exc:
        return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
    t_validacao = time.monotonic()

    from reservas.models import Reserva

    try:
        reserva_id = int(request.data.get('reserva'))
    except (TypeError, ValueError):
        return Response(
            {'detail': 'Informe a reserva da vistoria.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    tipo = request.data.get('tipo')

    def _resposta(vistoria, http_status, extra=None):
        vistoria.refresh_from_db()
        dados = VistoriaSerializer(vistoria, context={'request': request}).data
        if extra:
            dados = {**dados, **extra}
        return Response(dados, status=http_status)

    with transaction.atomic():
        try:
            reserva = Reserva.objects.select_for_update().select_related('veiculo', 'usuario').get(
                pk=reserva_id,
            )
        except Reserva.DoesNotExist:
            return Response(
                {'detail': 'Reserva não encontrada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        existente = (
            Vistoria.objects.select_for_update()
            .filter(reserva=reserva, tipo=tipo)
            .first()
        )
        fotos_existentes = existente.fotos.count() if existente else 0
        estado_ok = (
            existente is not None
            and fotos_existentes >= MAX_FOTOS_POR_VISTORIA
            and (
                (tipo == 'checkin' and reserva.status in ('em_andamento', 'concluida'))
                or (tipo == 'checkout' and reserva.status == 'concluida')
            )
        )
        if estado_ok:
            logger.info(
                'registrar_vistoria idempotente tipo=%s reserva=%s vistoria=%s total_ms=%.0f',
                tipo, reserva.id, existente.id, (time.monotonic() - t0) * 1000,
            )
            return _resposta(existente, status.HTTP_200_OK, extra={'idempotente': True})

        serializer = VistoriaCreateSerializer(
            data=request.data,
            context={'request': request, 'reserva_bloqueada': reserva},
        )
        serializer.is_valid(raise_exception=True)

        try:
            vistoria = serializer.save()
        except IntegrityError:
            vistoria = Vistoria.objects.select_for_update().get(reserva=reserva, tipo=tipo)
            if vistoria.fotos.count() >= MAX_FOTOS_POR_VISTORIA:
                return _resposta(vistoria, status.HTTP_200_OK, extra={'idempotente': True})
            raise

        t_vistoria = time.monotonic()
        _salvar_fotos(vistoria, arquivos, descricoes, observacoes_fotos)
        t_fotos = time.monotonic()

        if vistoria.tipo == 'checkin':
            if reserva.status != 'aprovada':
                raise ValidationError('Esta reserva não está mais disponível para check-in.')
            reserva.status = 'em_andamento'
            reserva.unidade_checkin = vistoria.unidade
            reserva.save(update_fields=['status', 'unidade_checkin', 'atualizado_em'])

            veiculo = Veiculo.objects.select_for_update().get(pk=reserva.veiculo_id)
            if veiculo.status != 'disponivel':
                raise ValidationError(
                    'O veículo não está disponível para check-in no momento.'
                )
            if (veiculo.km_atual or 0) == 0 and vistoria.quilometragem:
                veiculo.km_atual = vistoria.quilometragem
            veiculo.status = 'em_uso'
            veiculo.save(update_fields=['km_atual', 'status', 'atualizado_em'])
        else:
            if reserva.status != 'em_andamento':
                raise ValidationError('Esta reserva não está mais disponível para check-out.')
            reserva.status = 'concluida'
            reserva.data_devolucao_real = timezone.now()
            reserva.save(update_fields=['status', 'data_devolucao_real', 'atualizado_em'])

            veiculo = Veiculo.objects.select_for_update().get(pk=reserva.veiculo_id)
            if vistoria.quilometragem is not None:
                if vistoria.quilometragem < (veiculo.km_atual or 0):
                    raise ValidationError(
                        f'A quilometragem final não pode ser menor que o KM atual '
                        f'do veículo ({veiculo.km_atual} km).'
                    )
                veiculo.km_atual = vistoria.quilometragem
            veiculo.status = 'disponivel'
            veiculo.save(update_fields=['km_atual', 'status', 'atualizado_em'])

        registrar(
            ator=request.user,
            acao='registrar_vistoria',
            entidade='vistoria',
            entidade_id=vistoria.id,
            identificacao=f'Vistoria #{vistoria.id} · reserva #{reserva.id}',
            descricao=(
                f'{"Check-in" if vistoria.tipo == "checkin" else "Check-out"} '
                f'da reserva #{reserva.id} ({reserva.veiculo.placa}) '
                f'com {len(arquivos)} foto(s).'
            ),
            detalhes={'tipo': vistoria.tipo, 'reserva_id': reserva.id, 'fotos': len(arquivos)},
        )
        t_fim = time.monotonic()

    logger.info(
        'registrar_vistoria tipo=%s reserva=%s vistoria=%s '
        'validacao_ms=%.0f persistencia_ms=%.0f fotos_ms=%.0f commit_ms=%.0f total_ms=%.0f fotos=%s',
        tipo, reserva_id, vistoria.id,
        (t_validacao - t0) * 1000,
        (t_vistoria - t_validacao) * 1000,
        (t_fotos - t_vistoria) * 1000,
        (t_fim - t_fotos) * 1000,
        (t_fim - t0) * 1000,
        len(arquivos),
    )
    return _resposta(vistoria, status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes(AuthenticatedAndPasswordSet)
@parser_classes([MultiPartParser, FormParser])
def upload_multiplas_fotos(request, vistoria_id):
    """
    POST /api/vistorias/<vistoria_id>/upload-fotos/
    Upload de múltiplas fotos de uma vez para uma vistoria.
    (Mantido para compatibilidade; o fluxo novo usa /vistorias/registrar/.)
    """
    try:
        vistoria = Vistoria.objects.get(pk=vistoria_id)
    except (Vistoria.DoesNotExist, ValueError, TypeError):
        return Response({'detail': 'Vistoria não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    # Permissão
    if not request.user.is_admin and vistoria.reserva.usuario != request.user:
        return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)

    fotos = request.FILES.getlist('fotos')
    if not fotos:
        return Response({'detail': 'Nenhuma foto enviada.'}, status=status.HTTP_400_BAD_REQUEST)

    # Limita a 5 fotos por vistoria (regra de negócio)
    fotos_existentes = vistoria.fotos.count()
    if fotos_existentes + len(fotos) > MAX_FOTOS_POR_VISTORIA:
        return Response(
            {'detail': f'Limite de {MAX_FOTOS_POR_VISTORIA} fotos por vistoria. '
                       f'Já existem {fotos_existentes} fotos.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    getlist = getattr(request.data, 'getlist', None)
    descricoes = getlist('descricoes') if getlist else []
    observacoes = getlist('observacoes') if getlist else []

    with transaction.atomic():
        criadas = _salvar_fotos(vistoria, fotos, descricoes, observacoes)

    registrar(
        ator=request.user,
        acao='enviar_foto',
        entidade='vistoria',
        entidade_id=vistoria.id,
        identificacao=f'Vistoria #{vistoria.id}',
        descricao=f'{len(criadas)} foto(s) enviada(s) para a vistoria #{vistoria.id}.',
        detalhes={'fotos': len(criadas)},
    )

    serializer = FotoVistoriaSerializer(criadas, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)