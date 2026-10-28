from django.urls import path

from .views import ExportarExcelView, IndicadoresView, OpcoesRelatorioView

urlpatterns = [
    path('indicadores/', IndicadoresView.as_view(), name='relatorio-indicadores'),
    path('opcoes/', OpcoesRelatorioView.as_view(), name='relatorio-opcoes'),
    path('exportar/', ExportarExcelView.as_view(), name='relatorio-exportar'),
]
