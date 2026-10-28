from django.urls import path

from .views import (
    AcaoAuditoriaListView,
    ArquivoAuditoriaListView,
    IntegridadeAuditoriaView,
    OpcoesAuditoriaView,
)

urlpatterns = [
    path('acoes/', AcaoAuditoriaListView.as_view(), name='auditoria-acoes'),
    path('arquivos/', ArquivoAuditoriaListView.as_view(), name='auditoria-arquivos'),
    path('integridade/', IntegridadeAuditoriaView.as_view(), name='auditoria-integridade'),
    path('opcoes/', OpcoesAuditoriaView.as_view(), name='auditoria-opcoes'),
]
