from django.urls import path
from .views import (
    ReservaListCreateView, ReservaDetailView,
    ReservaAprovacaoView, iniciar_reserva, finalizar_reserva,
    RelatorioCalendarioReservasView, DisponibilidadeReservaView,
    AlertasOperacionaisView, AutorizacaoCheckinListView,
    solicitar_checkin_antecipado, decidir_checkin_antecipado,
)

urlpatterns = [
    path('', ReservaListCreateView.as_view(), name='reserva-list-create'),
    path('disponibilidade/', DisponibilidadeReservaView.as_view(), name='reserva-disponibilidade'),
    path('relatorio/calendario/', RelatorioCalendarioReservasView.as_view(), name='reserva-relatorio-calendario'),
    path('alertas-operacionais/', AlertasOperacionaisView.as_view(), name='reserva-alertas-operacionais'),
    path('autorizacoes-checkin/', AutorizacaoCheckinListView.as_view(), name='reserva-autorizacao-checkin-list'),
    path(
        'autorizacoes-checkin/<int:pk>/',
        decidir_checkin_antecipado,
        name='reserva-autorizacao-checkin-decidir',
    ),
    path('<int:pk>/', ReservaDetailView.as_view(), name='reserva-detail'),
    path('<int:pk>/aprovar/', ReservaAprovacaoView.as_view(), name='reserva-aprovacao'),
    path('<int:pk>/iniciar/', iniciar_reserva, name='reserva-iniciar'),
    path('<int:pk>/finalizar/', finalizar_reserva, name='reserva-finalizar'),
    path(
        '<int:pk>/checkin-antecipado/',
        solicitar_checkin_antecipado,
        name='reserva-checkin-antecipado',
    ),
]
