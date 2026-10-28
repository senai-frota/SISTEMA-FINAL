from datetime import time, timedelta

from django.utils import timezone
from rest_framework import serializers

HORA_INICIO_OPERACAO = time(6, 0, 0)
HORA_FIM_OPERACAO = time(22, 0, 0)

# Janela permitida para check-in/check-out em relação aos horários
# oficiais da reserva (turnos e pernoite usam data_inicio/data_fim).
TOLERANCIA_RESERVA_MINUTOS = 30

MSG_FORA_JANELA_OPERACIONAL = (
    'Operação permitida apenas entre 06:00 e 22:00.'
)
MSG_CHECKIN_ANTES = (
    'Check-in só é permitido a partir de 30 minutos antes do horário '
    'de início da reserva.'
)
MSG_CHECKIN_DEPOIS = (
    'Check-in não é permitido após 30 minutos do horário de '
    'encerramento da reserva.'
)
MSG_CHECKOUT_ANTES = (
    'Check-out só é permitido a partir de 30 minutos antes do horário '
    'de início da reserva.'
)
MSG_CHECKOUT_DEPOIS = (
    'Check-out não é permitido após 30 minutos do horário de '
    'encerramento da reserva.'
)
MSG_CHECKOUT_UNIDADE = (
    'O check-out deve ser realizado na mesma unidade em que foi feito '
    'o check-in desta reserva.'
)
MSG_VEICULO_INDISPONIVEL = (
    'O veículo não está disponível para check-in no momento.'
)


def agora_local():
    return timezone.localtime(timezone.now())


def dentro_janela_operacional(momento=None):
    momento = momento or agora_local()
    hora = momento.time()
    return HORA_INICIO_OPERACAO <= hora <= HORA_FIM_OPERACAO


def validar_janela_operacional(momento=None):
    if not dentro_janela_operacional(momento):
        raise serializers.ValidationError(MSG_FORA_JANELA_OPERACIONAL)


def janela_reserva_com_tolerancia(reserva):
    """Retorna (início, fim) locais com ±TOLERANCIA_RESERVA_MINUTOS."""
    inicio = timezone.localtime(reserva.data_inicio)
    fim = timezone.localtime(reserva.data_fim)
    delta = timedelta(minutes=TOLERANCIA_RESERVA_MINUTOS)
    return inicio - delta, fim + delta


def checkin_antecipado_autorizado(reserva):
    from reservas.models import AutorizacaoCheckinAntecipado

    return AutorizacaoCheckinAntecipado.objects.filter(
        reserva=reserva,
        status='aprovada',
    ).exists()


def validar_checkin_horario_reserva(reserva, momento=None, antecipado_autorizado=None):
    momento = momento or agora_local()
    inicio_tol, fim_tol = janela_reserva_com_tolerancia(reserva)
    if momento < inicio_tol:
        if antecipado_autorizado is None:
            antecipado_autorizado = checkin_antecipado_autorizado(reserva)
        if not antecipado_autorizado:
            raise serializers.ValidationError(MSG_CHECKIN_ANTES)
    if momento > fim_tol:
        raise serializers.ValidationError(MSG_CHECKIN_DEPOIS)


def validar_checkout_horario_reserva(reserva, momento=None):
    """
    Check-out de reserva em andamento: permitido 24 h.

    A restrição de horário da reserva não impede a devolução depois do
    prazo. Continua bloqueado apenas se for cedo demais (antes da janela
    de início com tolerância).
    """
    momento = momento or agora_local()
    inicio_tol, _fim_tol = janela_reserva_com_tolerancia(reserva)
    if momento < inicio_tol:
        raise serializers.ValidationError(MSG_CHECKOUT_ANTES)


def checkout_esta_atrasado(reserva, momento=None):
    momento = momento or agora_local()
    _inicio_tol, fim_tol = janela_reserva_com_tolerancia(reserva)
    return reserva.status == 'em_andamento' and momento > fim_tol
