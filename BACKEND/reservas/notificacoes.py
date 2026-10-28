"""Alertas internos e e-mail complementar (desligado até a TI autorizar)."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError

from .models import EventoOperacional

logger = logging.getLogger('reservas.operacoes')


def _emails_validos(usuarios):
    vistos = set()
    resultado = []
    for usuario in usuarios:
        email = (getattr(usuario, 'email', None) or '').strip()
        if not email or '@' not in email or email in vistos:
            continue
        vistos.add(email)
        resultado.append((usuario, email))
    return resultado


def _administradores_ativos():
    from usuarios.models import Usuario

    return list(Usuario.objects.filter(is_admin=True, is_active=True))


def _registrar_evento(chave, tipo, reserva, destinatario=None, detalhes=None):
    try:
        evento, criado = EventoOperacional.objects.get_or_create(
            chave=chave,
            defaults={
                'tipo': tipo,
                'reserva': reserva,
                'destinatario': destinatario,
                'detalhes': detalhes or {},
            },
        )
        return criado
    except IntegrityError:
        return False


def tentar_enviar_email(chave, reserva, destinatarios, assunto, corpo, tipo):
    """
    Nunca impede o alerta interno. Só envia se FROTA_EMAIL_ENABLED=True
    e houver SMTP configurado. Falhas são registradas sem credenciais.
    """
    if not _registrar_evento(chave, tipo, reserva, detalhes={'assunto': assunto}):
        return 'ja_enviado'

    if not getattr(settings, 'FROTA_EMAIL_ENABLED', False):
        logger.info(
            'E-mail operacional desligado (FROTA_EMAIL_ENABLED=false) chave=%s reserva=%s',
            chave, reserva.id,
        )
        return 'desligado'

    pares = _emails_validos(destinatarios)
    if not pares:
        logger.info(
            'Nenhum endereço de e-mail válido para o evento chave=%s reserva=%s',
            chave, reserva.id,
        )
        return 'sem_destinatario'

    remetente = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or 'noreply@localhost'
    enviados = 0
    for _usuario, email in pares:
        try:
            send_mail(
                assunto,
                corpo,
                remetente,
                [email],
                fail_silently=False,
            )
            enviados += 1
        except Exception:
            logger.exception(
                'Falha ao enviar e-mail operacional chave=%s reserva=%s',
                chave, reserva.id,
            )
    return 'enviado' if enviados else 'falha'


def notificar_checkout_atrasado(reserva):
    destinatarios = _administradores_ativos() + [reserva.usuario]
    assunto = f'[FROTA SENAI] Check-out atrasado · {reserva.veiculo.placa}'
    corpo = (
        f'Reserva #{reserva.id} ({reserva.veiculo.placa}) de {reserva.usuario.nome} '
        f'ultrapassou o horário previsto de devolução e ainda não teve check-out.\n'
        f'Ação: registrar o check-out na mesma unidade do check-in.'
    )
    return tentar_enviar_email(
        chave=f'{EventoOperacional.Tipo.EMAIL_CHECKOUT_ATRASADO}:{reserva.id}',
        reserva=reserva,
        destinatarios=destinatarios,
        assunto=assunto,
        corpo=corpo,
        tipo=EventoOperacional.Tipo.EMAIL_CHECKOUT_ATRASADO,
    )


def notificar_cancelamento_automatico(reserva):
    destinatarios = _administradores_ativos() + [reserva.usuario]
    assunto = f'[FROTA SENAI] Reserva cancelada automaticamente · {reserva.veiculo.placa}'
    corpo = (
        f'Reserva #{reserva.id} ({reserva.veiculo.placa}) de {reserva.usuario.nome} '
        f'foi cancelada automaticamente por falta de check-in obrigatório.\n'
        f'O pernoite em outra unidade não dispensa o check-in normal.'
    )
    return tentar_enviar_email(
        chave=f'{EventoOperacional.Tipo.EMAIL_CANCELAMENTO}:{reserva.id}',
        reserva=reserva,
        destinatarios=destinatarios,
        assunto=assunto,
        corpo=corpo,
        tipo=EventoOperacional.Tipo.EMAIL_CANCELAMENTO,
    )
