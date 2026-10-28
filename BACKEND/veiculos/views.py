from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from rest_framework import generics, filters, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from usuarios.permissions import AuthenticatedAndPasswordSet, ExigeSenhaDefinida, IsAdmin
from auditoria.services import registrar

from .imagens import (
    apagar_do_storage, arquivos_enviados, garantir_galeria, maximo_fotos,
    nome_aleatorio, sincronizar_capa, validar_imagem,
)
from .models import FotoVeiculo, Veiculo
from .serializers import VeiculoSerializer
from .services import (
    FipeIndisponivel,
    buscar_anos,
    buscar_detalhes,
    buscar_marcas,
    buscar_modelos,
)


# ============================================================
# VEÍCULOS
# ============================================================

class VeiculoListCreateView(generics.ListCreateAPIView):
    queryset = Veiculo.objects.all()
    serializer_class = VeiculoSerializer
    permission_classes = AuthenticatedAndPasswordSet

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        'status',
        'marca',
        'tipo_combustivel',
        'ano',
    ]

    search_fields = [
        'placa',
        'modelo',
        'marca',
    ]

    ordering_fields = [
        'marca',
        'modelo',
        'ano',
        'status',
    ]

    ordering = ['marca', 'modelo']

    def get_queryset(self):
        queryset = Veiculo.objects.all().prefetch_related('fotos')
        usuario = self.request.user
        incluir = (self.request.query_params.get('incluir_inativos') or '').lower() in (
            '1', 'true', 'sim',
        )
        status_pedido = self.request.query_params.get('status')
        if getattr(usuario, 'is_admin', False) and (incluir or status_pedido == 'inativo'):
            return queryset
        return queryset.exclude(status='inativo')

    def perform_create(self, serializer):
        if not self.request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem cadastrar veículos.'
            )

        veiculo = serializer.save()
        registrar(
            ator=self.request.user,
            acao='criar_veiculo',
            entidade='veiculo',
            entidade_id=veiculo.id,
            identificacao=f'{veiculo.marca} {veiculo.modelo} ({veiculo.placa})',
            descricao=f'Veículo {veiculo.placa} foi cadastrado.',
            detalhes={'status': veiculo.status},
        )


class VeiculoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Veiculo.objects.all().prefetch_related('fotos')
    serializer_class = VeiculoSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def perform_update(self, serializer):
        if not self.request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem editar veículos.'
            )

        anterior = serializer.instance
        status_anterior = anterior.status
        campos = []
        for campo in (
            'placa', 'modelo', 'marca', 'ano', 'cor', 'tipo_combustivel',
            'capacidade', 'renavam', 'chassi', 'status', 'observacoes',
            'km_atual', 'data_ultima_manutencao',
        ):
            if campo in serializer.validated_data and serializer.validated_data[campo] != getattr(anterior, campo):
                campos.append(campo)
        veiculo = serializer.save()
        if not campos:
            return
        if status_anterior != 'inativo' and veiculo.status == 'inativo':
            acao = 'inativar_veiculo'
            descricao = f'Veículo {veiculo.placa} foi inativado.'
        else:
            acao = 'alterar_veiculo'
            descricao = f'Veículo {veiculo.placa} foi atualizado.'
        rotulos = {
            'placa': 'placa',
            'modelo': 'modelo',
            'marca': 'marca',
            'ano': 'ano',
            'cor': 'cor',
            'tipo_combustivel': 'combustível',
            'capacidade': 'capacidade',
            'renavam': 'renavam',
            'chassi': 'chassi',
            'status': 'status',
            'observacoes': 'observações',
            'km_atual': 'quilometragem',
            'data_ultima_manutencao': 'última manutenção',
        }
        registrar(
            ator=self.request.user,
            acao=acao,
            entidade='veiculo',
            entidade_id=veiculo.id,
            identificacao=f'{veiculo.marca} {veiculo.modelo} ({veiculo.placa})',
            descricao=descricao,
            detalhes={'campos': [rotulos.get(campo, campo) for campo in campos]},
        )

    def perform_destroy(self, instance):
        if not self.request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem remover veículos.'
            )

        if instance.status == 'inativo':
            return
        instance.status = 'inativo'
        instance.save(update_fields=['status', 'atualizado_em'])
        registrar(
            ator=self.request.user,
            acao='inativar_veiculo',
            entidade='veiculo',
            entidade_id=instance.id,
            identificacao=f'{instance.marca} {instance.modelo} ({instance.placa})',
            descricao=f'Veículo {instance.placa} foi inativado.',
        )


# ============================================================
# IMAGEM DO VEÍCULO
# ============================================================

class VeiculoImagemView(APIView):
    """
    POST   /api/veiculos/<id>/imagem/  (multipart, `imagem` e/ou `imagens`) — adiciona
    DELETE /api/veiculos/<id>/imagem/  — remove a capa, ou a foto `?foto=<id>`
    Somente administradores. Arquivos removidos são apagados do storage após o commit.
    """

    permission_classes = [IsAuthenticated, ExigeSenhaDefinida, IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def _responder(self, request, veiculo, codigo):
        veiculo = Veiculo.objects.prefetch_related('fotos').get(pk=veiculo.pk)
        return Response(
            VeiculoSerializer(veiculo, context={'request': request}).data, status=codigo,
        )

    def post(self, request, pk):
        arquivos = arquivos_enviados(request)
        if not arquivos:
            raise ValidationError({'imagem': 'Selecione uma imagem.'})

        from rest_framework.serializers import ValidationError as ErroArquivo
        try:
            validados = [(arquivo, validar_imagem(arquivo)) for arquivo in arquivos]
        except ErroArquivo as exc:
            raise ValidationError({'imagem': exc.detail}) from exc
        limite = maximo_fotos()

        with transaction.atomic():
            veiculo = get_object_or_404(Veiculo.objects.select_for_update(), pk=pk)
            garantir_galeria(veiculo)
            atuais = veiculo.fotos.count()
            if atuais + len(validados) > limite:
                raise ValidationError({
                    'imagem': [f'Cada veículo pode ter no máximo {limite} fotos.'],
                })
            proxima = veiculo.fotos.aggregate(m=Max('ordem')).get('m')
            proxima = (proxima if proxima is not None else -1) + 1
            gravados = []
            try:
                for i, (arquivo, metadados) in enumerate(validados):
                    foto = FotoVeiculo(veiculo=veiculo, ordem=proxima + i)
                    foto.arquivo.save(nome_aleatorio(metadados['extensao']), arquivo, save=False)
                    foto.save()
                    gravados.append(foto)
                    registrar(
                        ator=request.user,
                        acao='adicionar_imagem_veiculo',
                        entidade='veiculo',
                        entidade_id=veiculo.id,
                        identificacao=f'{veiculo.marca} {veiculo.modelo} ({veiculo.placa})',
                        descricao=f'Imagem do veículo {veiculo.placa} foi adicionada.',
                        detalhes={
                            'formato': metadados['formato'],
                            'largura': metadados['largura'],
                            'altura': metadados['altura'],
                            'tamanho_bytes': metadados['tamanho_bytes'],
                            'foto_id': foto.id,
                        },
                    )
                sincronizar_capa(veiculo)
            except Exception:
                for foto in gravados:
                    apagar_do_storage(foto.arquivo.storage, foto.arquivo.name)
                raise

        codigo = status.HTTP_201_CREATED if atuais == 0 else status.HTTP_200_OK
        return self._responder(request, veiculo, codigo)

    def delete(self, request, pk):
        foto_id = request.query_params.get('foto') or request.data.get('foto')
        with transaction.atomic():
            veiculo = get_object_or_404(Veiculo.objects.select_for_update(), pk=pk)
            garantir_galeria(veiculo)
            galeria = list(veiculo.fotos.order_by('ordem', 'id'))
            foto = None
            if foto_id:
                foto = next((item for item in galeria if str(item.id) == str(foto_id)), None)
                if foto is None:
                    return Response(
                        {'detail': 'Foto não encontrada neste veículo.'},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            elif galeria:
                foto = galeria[0]
            elif not veiculo.foto:
                return Response(
                    {'detail': 'Este veículo não possui imagem.'}, status=status.HTTP_404_NOT_FOUND,
                )

            if foto is not None:
                storage = foto.arquivo.storage
                nome_antigo = foto.arquivo.name
                foto.delete()
            else:
                storage = veiculo.foto.storage
                nome_antigo = veiculo.foto.name
            sincronizar_capa(veiculo)
            registrar(
                ator=request.user,
                acao='remover_imagem_veiculo',
                entidade='veiculo',
                entidade_id=veiculo.id,
                identificacao=f'{veiculo.marca} {veiculo.modelo} ({veiculo.placa})',
                descricao=f'Imagem do veículo {veiculo.placa} foi removida.',
                detalhes={'foto_id': foto.id if foto is not None else None},
            )
            transaction.on_commit(lambda: apagar_do_storage(storage, nome_antigo))

        return self._responder(request, veiculo, status.HTTP_200_OK)


def _resposta_fipe(obter):
    try:
        return Response(obter())
    except FipeIndisponivel as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class MarcaListView(APIView):
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request):
        return _resposta_fipe(buscar_marcas)


class ModeloListView(APIView):
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request, codigo_marca):
        return _resposta_fipe(lambda: buscar_modelos(codigo_marca))


class AnoListView(APIView):
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request, codigo_marca, codigo_modelo):
        return _resposta_fipe(lambda: buscar_anos(codigo_marca, codigo_modelo))


class DetalhesFipeView(APIView):
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request, codigo_marca, codigo_modelo, codigo_ano):
        return _resposta_fipe(
            lambda: buscar_detalhes(codigo_marca, codigo_modelo, codigo_ano),
        )