"""Regras operacionais: cancelamento automático, alertas e prazos."""
from datetime import datetime, time, timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from auditoria.services import registrar
from vistorias.regras import janela_reserva_com_tolerancia

from .models import (
    MOTIVO_CANCELAMENTO_FALTA_CHECKIN,
    EventoOperacional,
    Reserva,
)

MSG_CANCELAMENTO_AUTOMATICO = (
    'CANCELAMENTO AUTOMÁTICO POR FALTA DE CHECK-IN.'
)


def local_ou(momento=None):
    if momento is None:
        return timezone.localtime(timezone.now())
    if timezone.is_naive(momento):
        return timezone.make_aware(momento, timezone.get_current_timezone())
    return timezone.localtime(momento)


def fim_janela_checkin(reserva):
    _inicio, fim_tol = janela_reserva_com_tolerancia(reserva)
    return fim_tol


def momento_cancelamento_automatico(reserva):
    """
    Meia-noite civil do dia seguinte ao fim da janela de check-in.

    Ex.: janela termina segunda 12:30 → cancela terça 00:00 (fuso local).
    """
    fim = timezone.localtime(fim_janela_checkin(reserva))
    dia_seguinte = fim.date() + timedelta(days=1)
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(dia_seguinte, time.min), tz)


def deve_cancelar_por_falta_checkin(reserva, momento=None):
    momento = local_ou(momento)
    if reserva.status != 'aprovada':
        return False
    from vistorias.models import Vistoria

    if Vistoria.objects.filter(reserva=reserva, tipo='checkin').exists():
        return False
    return momento >= momento_cancelamento_automatico(reserva)


def checkin_proximo_do_cancelamento(reserva, momento=None):
    """Janela de check-in já venceu, mas a meia-noite do dia seguinte ainda não chegou."""
    momento = local_ou(momento)
    if reserva.status != 'aprovada':
        return False
    from vistorias.models import Vistoria

    if Vistoria.objects.filter(reserva=reserva, tipo='checkin').exists():
        return False
    fim = fim_janela_checkin(reserva)
    limite = momento_cancelamento_automatico(reserva)
    return momento > fim and momento < limite


def queryset_sem_checkin():
    from vistorias.models import Vistoria

    return Reserva.objects.filter(status='aprovada').exclude(
        Exists(Vistoria.objects.filter(reserva_id=OuterRef('pk'), tipo='checkin'))
    )


def _liberar_veiculo_se_livre(veiculo, reserva_id):
    outras_ativas = Reserva.objects.filter(
        veiculo=veiculo,
        status__in=['aprovada', 'em_andamento'],
    ).exclude(pk=reserva_id).exists()
    if not outras_ativas and veiculo.status == 'em_uso':
        veiculo.status = 'disponivel'
        veiculo.save(update_fields=['status', 'atualizado_em'])


def cancelar_reserva_automaticamente(reserva, momento=None):
    """
    Cancela uma reserva aprovada sem check-in. Idempotente: se já estiver
    cancelada por este motivo, não grava de novo.
    """
    from .notificacoes import notificar_cancelamento_automatico

    momento = local_ou(momento)
    with transaction.atomic():
        reserva = Reserva.objects.select_for_update().select_related(
            'usuario', 'veiculo',
        ).get(pk=reserva.pk)
        if reserva.status != 'aprovada':
            return False
        from vistorias.models import Vistoria
        if Vistoria.objects.filter(reserva=reserva, tipo='checkin').exists():
            return False
        if momento < momento_cancelamento_automatico(reserva):
            return False

        evento, criado = EventoOperacional.objects.get_or_create(
            chave=f'{EventoOperacional.Tipo.CANCELAMENTO_AUTOMATICO}:{reserva.id}',
            defaults={
                'tipo': EventoOperacional.Tipo.CANCELAMENTO_AUTOMATICO,
                'reserva': reserva,
                'detalhes': {'motivo': MOTIVO_CANCELAMENTO_FALTA_CHECKIN},
            },
        )
        if not criado and reserva.status == 'cancelada':
            return False

        reserva.status = 'cancelada'
        reserva.motivo_cancelamento = MOTIVO_CANCELAMENTO_FALTA_CHECKIN
        reserva.observacao_admin = MSG_CANCELAMENTO_AUTOMATICO
        reserva.save(update_fields=[
            'status', 'motivo_cancelamento', 'observacao_admin', 'atualizado_em',
        ])
        _liberar_veiculo_se_livre(reserva.veiculo, reserva.id)

        if criado or not EventoOperacional.objects.filter(
            chave=f'{EventoOperacional.Tipo.CANCELAMENTO_AUTOMATICO}:{reserva.id}:auditado'
        ).exists():
            registrar(
                ator=None,
                acao='cancelar_reserva_auto',
                entidade='reserva',
                entidade_id=reserva.id,
                identificacao=f'Reserva #{reserva.id} · {reserva.veiculo.placa}',
                descricao=(
                    f'A reserva #{reserva.id} do veículo {reserva.veiculo.placa} '
                    f'de {reserva.usuario.nome} foi cancelada automaticamente '
                    f'por falta de check-in.'
                ),
                detalhes={
                    'automatico': True,
                    'motivo': MOTIVO_CANCELAMENTO_FALTA_CHECKIN,
                },
                justificativa=MSG_CANCELAMENTO_AUTOMATICO,
                usuario_afetado=reserva.usuario,
            )
            EventoOperacional.objects.get_or_create(
                chave=f'{EventoOperacional.Tipo.CANCELAMENTO_AUTOMATICO}:{reserva.id}:auditado',
                defaults={
                    'tipo': EventoOperacional.Tipo.CANCELAMENTO_AUTOMATICO,
                    'reserva': reserva,
                    'detalhes': {'fase': 'auditoria'},
                },
            )

    notificar_cancelamento_automatico(reserva)
    return True


def cancelar_reservas_sem_checkin(momento=None):
    momento = local_ou(momento)
    canceladas = []
    for reserva in queryset_sem_checkin().select_related('usuario', 'veiculo'):
        if deve_cancelar_por_falta_checkin(reserva, momento):
            if cancelar_reserva_automaticamente(reserva, momento):
                canceladas.append(reserva.id)
    return canceladas


def registrar_checkouts_atrasados(momento=None):
    from vistorias.regras import checkout_esta_atrasado
    from .notificacoes import notificar_checkout_atrasado

    momento = local_ou(momento)
    novos = []
    qs = Reserva.objects.filter(status='em_andamento').select_related('usuario', 'veiculo')
    for reserva in qs:
        if not checkout_esta_atrasado(reserva, momento):
            continue
        evento, criado = EventoOperacional.objects.get_or_create(
            chave=f'{EventoOperacional.Tipo.CHECKOUT_ATRASADO}:{reserva.id}',
            defaults={
                'tipo': EventoOperacional.Tipo.CHECKOUT_ATRASADO,
                'reserva': reserva,
                'detalhes': {'data_fim': reserva.data_fim.isoformat()},
            },
        )
        if criado:
            notificar_checkout_atrasado(reserva)
            novos.append(reserva.id)
    return novos


def executar_rotina(momento=None):
    canceladas = cancelar_reservas_sem_checkin(momento)
    atrasados = registrar_checkouts_atrasados(momento)
    return {
        'canceladas': canceladas,
        'checkouts_atrasados': atrasados,
    }


def montar_item_alerta(tipo, severidade, titulo, mensagem, reserva, acao, para='/reservas'):
    return {
        'id': f'{tipo}-{reserva.id}',
        'tipo': tipo,
        'severidade': severidade,
        'titulo': titulo,
        'mensagem': mensagem,
        'acao': acao,
        'para': para,
        'reserva_id': reserva.id,
        'veiculo_id': reserva.veiculo_id,
        'veiculo_placa': reserva.veiculo.placa,
        'usuario_id': reserva.usuario_id,
        'usuario_nome': reserva.usuario.nome,
        'data_inicio': reserva.data_inicio,
        'data_fim': reserva.data_fim,
    }


def listar_alertas_operacionais(usuario, momento=None):
    from vistorias.regras import checkout_esta_atrasado
    from .models import AutorizacaoCheckinAntecipado

    momento = local_ou(momento)
    criticos = []
    comuns = []

    reservas = Reserva.objects.select_related('usuario', 'veiculo')
    if not usuario.is_admin:
        reservas = reservas.filter(usuario=usuario)

    for reserva in reservas.filter(status='aprovada'):
        if checkin_proximo_do_cancelamento(reserva, momento):
            criticos.append(montar_item_alerta(
                'checkin_proximo_cancelamento',
                'critico',
                'Check-in próximo do cancelamento automático',
                (
                    f'Reserva #{reserva.id} ({reserva.veiculo.placa}) ainda sem check-in. '
                    f'Será cancelada à meia-noite se o check-in não for feito.'
                ),
                reserva,
                'Registrar o check-in obrigatório ou cancelar a reserva.',
            ))

    for reserva in reservas.filter(status='em_andamento'):
        if checkout_esta_atrasado(reserva, momento):
            criticos.append(montar_item_alerta(
                'checkout_atrasado',
                'critico',
                'Check-out atrasado em aberto',
                (
                    f'Reserva #{reserva.id} ({reserva.veiculo.placa}) ultrapassou o horário '
                    f'previsto de devolução e ainda não teve check-out.'
                ),
                reserva,
                'Registrar o check-out na mesma unidade do check-in.',
            ))

    limite_historico = momento - timedelta(days=7)
    auto_qs = reservas.filter(
        status='cancelada',
        motivo_cancelamento=MOTIVO_CANCELAMENTO_FALTA_CHECKIN,
        atualizado_em__gte=limite_historico,
    )
    for reserva in auto_qs:
        criticos.append(montar_item_alerta(
            'cancelamento_automatico',
            'critico',
            'Reserva cancelada automaticamente',
            (
                f'Reserva #{reserva.id} ({reserva.veiculo.placa}) foi cancelada por '
                f'falta de check-in obrigatório.'
            ),
            reserva,
            'Conferir o histórico e a disponibilidade do veículo.',
        ))

    if usuario.is_admin:
        pendentes = Reserva.objects.filter(status='pendente').select_related(
            'usuario', 'veiculo',
        )
        for reserva in pendentes:
            comuns.append(montar_item_alerta(
                'reserva_pendente',
                'comum',
                'Nova solicitação de reserva',
                (
                    f'{reserva.usuario.nome} solicitou {reserva.veiculo.placa}.'
                ),
                reserva,
                'Aprovar ou rejeitar a solicitação.',
                para='/aprovacoes',
            ))
        antecipados = AutorizacaoCheckinAntecipado.objects.filter(
            status='pendente',
        ).select_related('reserva__usuario', 'reserva__veiculo', 'solicitante')
        for auth in antecipados:
            reserva = auth.reserva
            comuns.append(montar_item_alerta(
                'checkin_antecipado_pendente',
                'comum',
                'Check-in antecipado pendente',
                (
                    f'{auth.solicitante.nome} pediu autorização para check-in '
                    f'antecipado da reserva #{reserva.id} ({reserva.veiculo.placa}).'
                ),
                reserva,
                'Aprovar ou rejeitar a autorização.',
                para='/aprovacoes',
            ))
            comuns[-1]['id'] = f'checkin_antecipado_pendente-{auth.id}'
            comuns[-1]['autorizacao_id'] = auth.id

    return {
        'gerado_em': momento,
        'criticos': criticos,
        'comuns': comuns,
        'contagens': {
            'criticos': len(criticos),
            'comuns': len(comuns),
            'reservas_pendentes': sum(1 for i in comuns if i['tipo'] == 'reserva_pendente'),
            'checkin_antecipado_pendente': sum(
                1 for i in comuns if i['tipo'] == 'checkin_antecipado_pendente'
            ),
            'checkout_atrasado': sum(1 for i in criticos if i['tipo'] == 'checkout_atrasado'),
            'checkin_proximo_cancelamento': sum(
                1 for i in criticos if i['tipo'] == 'checkin_proximo_cancelamento'
            ),
            'canceladas_automaticamente': sum(
                1 for i in criticos if i['tipo'] == 'cancelamento_automatico'
            ),
        },
    }
