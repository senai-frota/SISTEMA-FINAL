from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permissions import ExigeSenhaDefinida, IsAdmin

from .consultas import (
    TIPOS_ARQUIVO,
    consulta_arquivos,
    filtrar_situacao_acoes,
    mapa_registro_ativo,
    serializar_arquivo,
)
from .integridade import verificar_cadeia
from .models import RegistroAuditoria
from .serializers import RegistroAuditoriaSerializer

PERMISSAO_ADMIN = [IsAuthenticated, ExigeSenhaDefinida, IsAdmin]


def _periodo(queryset, params, campo):
    inicio = parse_date(params.get('de') or '')
    fim = parse_date(params.get('ate') or '')
    if inicio:
        queryset = queryset.filter(**{f'{campo}__date__gte': inicio})
    if fim:
        queryset = queryset.filter(**{f'{campo}__date__lte': fim})
    return queryset


class AcaoAuditoriaListView(APIView):
    """GET /api/auditoria/acoes/ — somente administrador."""

    permission_classes = PERMISSAO_ADMIN

    def get(self, request):
        params = request.query_params
        queryset = RegistroAuditoria.objects.all()
        acao = (params.get('acao') or '').strip()
        entidade = (params.get('entidade') or '').strip()
        if acao:
            queryset = queryset.filter(acao=acao)
        if entidade:
            queryset = queryset.filter(entidade=entidade)
        ator_id = params.get('usuario') or params.get('ator')
        if ator_id:
            try:
                queryset = queryset.filter(ator_id=int(ator_id))
            except (TypeError, ValueError):
                queryset = queryset.none()
        afetado_id = params.get('afetado')
        if afetado_id:
            try:
                queryset = queryset.filter(usuario_afetado_id=int(afetado_id))
            except (TypeError, ValueError):
                queryset = queryset.none()
        busca = (params.get('busca') or '').strip()
        if busca:
            queryset = queryset.filter(
                Q(descricao__icontains=busca)
                | Q(identificacao__icontains=busca)
                | Q(ator_nome__icontains=busca)
                | Q(ator_matricula__icontains=busca)
                | Q(justificativa__icontains=busca)
                | Q(usuario_afetado_nome__icontains=busca)
                | Q(usuario_afetado_matricula__icontains=busca)
            )
        queryset = _periodo(queryset, params, 'criado_em')
        queryset = filtrar_situacao_acoes(queryset, (params.get('situacao') or '').lower())
        queryset = queryset.order_by('-criado_em')

        paginator = PageNumberPagination()
        pagina = paginator.paginate_queryset(queryset, request, view=self)
        registros = pagina if pagina is not None else list(queryset[:20])
        serializer = RegistroAuditoriaSerializer(
            registros,
            many=True,
            context={'request': request, 'ativos': mapa_registro_ativo(registros)},
        )
        if pagina is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ArquivoAuditoriaListView(APIView):
    """GET /api/auditoria/arquivos/ — metadados e URL do storage já existente."""

    permission_classes = PERMISSAO_ADMIN

    def get(self, request):
        queryset = consulta_arquivos(request.query_params)
        paginator = PageNumberPagination()
        pagina = paginator.paginate_queryset(queryset, request, view=self)
        linhas = pagina if pagina is not None else list(queryset[:20])
        dados = [serializar_arquivo(linha, request) for linha in linhas]
        if pagina is not None:
            return paginator.get_paginated_response(dados)
        return Response(dados)


class IntegridadeAuditoriaView(APIView):
    """GET /api/auditoria/integridade/ — recalcula a cadeia de hash. Somente administrador."""

    permission_classes = PERMISSAO_ADMIN

    def get(self, request):
        return Response(verificar_cadeia())


class OpcoesAuditoriaView(APIView):
    """Listas usadas pelos filtros da tela. Somente administrador."""

    permission_classes = PERMISSAO_ADMIN

    def get(self, request):
        return Response({
            'acoes': [
                {'value': valor, 'label': rotulo}
                for valor, rotulo in RegistroAuditoria.Acao.choices
            ],
            'entidades': [
                {'value': valor, 'label': rotulo}
                for valor, rotulo in RegistroAuditoria.Entidade.choices
            ],
            'tipos_arquivo': [
                {'value': valor, 'label': rotulo}
                for valor, rotulo in TIPOS_ARQUIVO
            ],
        })
