from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auditoria.services import registrar
from usuarios.permissions import ExigeSenhaDefinida, IsAdmin

from .exportacao import gerar_planilha
from .filtros import STATUS_RESERVA, TURNOS, ler_filtros
from .indicadores import calcular_indicadores

PERMISSAO_ADMIN = [IsAuthenticated, ExigeSenhaDefinida, IsAdmin]
TIPO_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


class IndicadoresView(APIView):
    """GET /api/relatorios/indicadores/ — somente administrador."""

    permission_classes = PERMISSAO_ADMIN

    def get(self, request):
        return Response(calcular_indicadores(ler_filtros(request.query_params)))


class OpcoesRelatorioView(APIView):
    """GET /api/relatorios/opcoes/ — listas dos filtros. Somente administrador."""

    permission_classes = PERMISSAO_ADMIN

    def get(self, request):
        from usuarios.models import Usuario
        from veiculos.models import Veiculo

        return Response({
            'status': [{'value': v, 'label': r} for v, r in STATUS_RESERVA.items()],
            'turnos': [{'value': v, 'label': r} for v, r in TURNOS.items()],
            'veiculos': [
                {'value': v.id, 'label': f'{v.placa} · {v.marca} {v.modelo}'}
                for v in Veiculo.objects.order_by('placa')
            ],
            'usuarios': [
                {'value': u.id, 'label': f'{u.nome} ({u.matricula})'}
                for u in Usuario.objects.filter(is_admin=False).order_by('nome')
            ],
        })


class ExportarExcelView(APIView):
    """GET /api/relatorios/exportar/ — planilha .xlsx com os mesmos filtros. Somente administrador."""

    permission_classes = PERMISSAO_ADMIN

    def get(self, request):
        filtros = ler_filtros(request.query_params)
        conteudo, contagens = gerar_planilha(filtros, request.user)

        registrar(
            ator=request.user,
            acao='exportar_dados',
            entidade='relatorio',
            entidade_id=None,
            identificacao='Exportação Excel',
            descricao=f'{request.user.nome} exportou os dados administrativos em Excel.',
            detalhes={
                'formato': 'xlsx',
                'filtros': filtros.como_dict(),
                'linhas': contagens,
            },
        )

        nome = f'relatorio-frota-{timezone.localtime():%Y%m%d-%H%M}.xlsx'
        resposta = HttpResponse(conteudo, content_type=TIPO_XLSX)
        resposta['Content-Disposition'] = f'attachment; filename="{nome}"'
        resposta['Cache-Control'] = 'no-store'
        return resposta
