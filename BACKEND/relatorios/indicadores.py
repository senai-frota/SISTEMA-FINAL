"""
Indicadores calculados exclusivamente a partir dos dados gravados.

Convenções:
- Reservas entram no período pela data de retirada (`data_inicio`).
- Vistorias entram pela data/hora do registro; Termos e CNHs pela data de envio.
- Situação atual de frota, usuários, CNH e Termo é uma fotografia do momento
  da consulta (não depende do período).
- Taxa de aprovação = reservas aprovadas (aprovada, em andamento, concluída)
  ÷ (aprovadas + negadas). Pendentes e canceladas ficam fora do cálculo.
- Km rodados = km do check-out − km do check-in da mesma reserva, somente
  quando as duas vistorias têm quilometragem e o resultado não é negativo.
"""
from django.db.models import Count, F, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from reservas.models import Reserva
from termos.models import TermoResponsabilidade
from termos.services_conta import situacao_termo
from usuarios.models import DocumentoCNH, Usuario, resumo_cnh_usuario
from veiculos.models import Veiculo
from vistorias.models import Vistoria

STATUS_APROVADOS = ('aprovada', 'em_andamento', 'concluida')

SITUACOES_CNH = [
    ('aprovada', 'Válida'),
    ('proxima_vencimento', 'Vence em até 30 dias'),
    ('pendente', 'Aguardando análise'),
    ('vencida', 'Vencida'),
    ('rejeitada', 'Rejeitada'),
    ('sem_cnh', 'Sem CNH'),
]

SITUACOES_TERMO = [
    ('valido', 'Válido'),
    ('pendente', 'Aguardando análise'),
    ('vencido', 'Vencido'),
    ('rejeitado', 'Rejeitado'),
    ('sem_termo', 'Sem termo'),
]


def _contagem(qs, campo, choices):
    brutos = dict(qs.order_by().values_list(campo).annotate(total=Count('id')))
    return [
        {'valor': valor, 'rotulo': rotulo, 'total': brutos.get(valor, 0)}
        for valor, rotulo in choices
    ]


def _mapa(itens):
    return {item['valor']: item['total'] for item in itens}


def _percentual(parte, total):
    return round(parte * 100 / total, 1) if total else None


def km_por_reserva(reservas_qs):
    """{reserva_id: (veiculo_id, km_rodados)} para reservas com check-in e check-out."""
    linhas = (
        Vistoria.objects
        .filter(reserva__in=reservas_qs.order_by().values('id'), quilometragem__isnull=False)
        .values_list('reserva_id', 'reserva__veiculo_id', 'tipo', 'quilometragem')
    )
    leituras = {}
    for reserva_id, veiculo_id, tipo, km in linhas:
        leituras.setdefault(reserva_id, {'veiculo': veiculo_id})[tipo] = km
    resultado = {}
    for reserva_id, dados in leituras.items():
        inicio, fim = dados.get('checkin'), dados.get('checkout')
        if inicio is not None and fim is not None and fim >= inicio:
            resultado[reserva_id] = (dados['veiculo'], fim - inicio)
    return resultado


def indicadores_reservas(filtros):
    qs = filtros.reservas(Reserva.objects.all())
    por_status = _contagem(qs, 'status', Reserva.STATUS_CHOICES)
    status = _mapa(por_status)
    aprovadas = sum(status[s] for s in STATUS_APROVADOS)
    negadas = status['negada']

    por_turno = _contagem(qs.filter(modalidade='turno'), 'turno', Reserva.TURNO_CHOICES)
    por_turno.append({
        'valor': 'horario',
        'rotulo': 'Horário personalizado',
        'total': qs.filter(modalidade='horario').count(),
    })

    por_mes = [
        {
            'mes': linha['mes'].strftime('%Y-%m'),
            'total': linha['total'],
            'aprovadas': linha['aprovadas'],
            'negadas': linha['negadas'],
        }
        for linha in (
            qs.order_by()
            .annotate(mes=TruncMonth('data_inicio'))
            .values('mes')
            .annotate(
                total=Count('id'),
                aprovadas=Count('id', filter=Q(status__in=STATUS_APROVADOS)),
                negadas=Count('id', filter=Q(status='negada')),
            )
            .order_by('mes')
        )
        if linha['mes'] is not None
    ]

    concluidas = qs.filter(status='concluida', data_devolucao_real__isnull=False)
    com_atraso = concluidas.filter(data_devolucao_real__gt=F('data_fim')).count()
    agora = timezone.now()
    checkout_atrasado_aberto = qs.filter(
        status='em_andamento', data_fim__lt=agora,
    ).count()
    cancelamentos_automaticos = qs.filter(
        status='cancelada', motivo_cancelamento='falta_checkin',
    ).count()
    ids_com_checkin = set(
        Vistoria.objects.filter(
            reserva__in=qs.order_by().values('id'), tipo='checkin',
        ).values_list('reserva_id', flat=True)
    )
    falta_checkin_obrigatorio = qs.filter(
        Q(status='aprovada') | Q(status='cancelada', motivo_cancelamento='falta_checkin')
    ).exclude(id__in=list(ids_com_checkin)).count()
    pernoites_validas = qs.filter(pernoite=True).count()

    top_veiculos = [
        {
            'veiculo_id': linha['veiculo_id'],
            'rotulo': f"{linha['veiculo__placa']} · {linha['veiculo__marca']} {linha['veiculo__modelo']}",
            'total': linha['total'],
        }
        for linha in (
            qs.order_by()
            .values('veiculo_id', 'veiculo__placa', 'veiculo__marca', 'veiculo__modelo')
            .annotate(total=Count('id'))
            .order_by('-total', 'veiculo__placa')[:5]
        )
    ]
    top_usuarios = [
        {
            'usuario_id': linha['usuario_id'],
            'rotulo': f"{linha['usuario__nome']} ({linha['usuario__matricula']})",
            'total': linha['total'],
        }
        for linha in (
            qs.order_by()
            .values('usuario_id', 'usuario__nome', 'usuario__matricula')
            .annotate(total=Count('id'))
            .order_by('-total', 'usuario__nome')[:5]
        )
    ]

    return {
        'total': sum(status.values()),
        'pendentes': status['pendente'],
        'aprovadas': aprovadas,
        'negadas': negadas,
        'canceladas': status['cancelada'],
        'taxa_aprovacao': _percentual(aprovadas, aprovadas + negadas),
        'pernoites': pernoites_validas,
        'pernoites_validas': pernoites_validas,
        'devolucoes_registradas': concluidas.count(),
        'devolucoes_com_atraso': com_atraso,
        'checkout_atrasado_concluido': com_atraso,
        'checkout_atrasado_aberto': checkout_atrasado_aberto,
        'cancelamentos_automaticos': cancelamentos_automaticos,
        'falta_checkin_obrigatorio': falta_checkin_obrigatorio,
        'por_status': por_status,
        'por_turno': por_turno,
        'por_mes': por_mes,
        'top_veiculos': top_veiculos,
        'top_usuarios': top_usuarios,
    }


def indicadores_frota(filtros):
    veiculos = filtros.veiculos(Veiculo.objects.all())
    por_status = _contagem(veiculos, 'status', Veiculo.STATUS_CHOICES)
    status = _mapa(por_status)
    ativos = sum(status.values()) - status['inativo']

    reservas = filtros.reservas(Reserva.objects.all())
    efetivas = dict(
        reservas.filter(status__in=STATUS_APROVADOS)
        .order_by().values_list('veiculo_id').annotate(total=Count('id'))
    )
    km_por_veiculo = {}
    for veiculo_id, km in km_por_reserva(reservas).values():
        km_por_veiculo[veiculo_id] = km_por_veiculo.get(veiculo_id, 0) + km

    uso = [
        {
            'veiculo_id': v.id,
            'rotulo': f'{v.placa} · {v.marca} {v.modelo}',
            'status': v.status,
            'reservas': efetivas.get(v.id, 0),
            'km_rodados': km_por_veiculo.get(v.id, 0),
        }
        for v in veiculos.order_by('placa')
    ]
    uso.sort(key=lambda item: (-item['km_rodados'], -item['reservas'], item['rotulo']))

    return {
        'total': sum(status.values()),
        'ativos': ativos,
        'disponiveis': status['disponivel'],
        'em_uso': status['em_uso'],
        'manutencao': status['manutencao'],
        'inativos': status['inativo'],
        'percentual_disponivel': _percentual(status['disponivel'], ativos),
        'km_rodados_total': sum(km_por_veiculo.values()),
        'por_status': por_status,
        'uso_por_veiculo': uso[:10],
    }


def situacao_documentos_usuarios(usuarios):
    """Situação atual de CNH e Termo por funcionário (sem alterar contas)."""
    cnh, termo = {}, {}
    for usuario in usuarios:
        cnh[usuario.pk] = resumo_cnh_usuario(usuario)
        termo[usuario.pk] = situacao_termo(usuario)
    return cnh, termo


def indicadores_usuarios(filtros, situacoes=None):
    base = filtros.usuarios(Usuario.objects.all())
    funcionarios = base.filter(is_admin=False)
    cnh, termo = situacoes or situacao_documentos_usuarios(funcionarios)

    contagem_cnh = {valor: 0 for valor, _ in SITUACOES_CNH}
    for resumo in cnh.values():
        contagem_cnh[resumo['situacao']] = contagem_cnh.get(resumo['situacao'], 0) + 1
    contagem_termo = {valor: 0 for valor, _ in SITUACOES_TERMO}
    for situacao, _ in termo.values():
        contagem_termo[situacao] = contagem_termo.get(situacao, 0) + 1

    return {
        'funcionarios': funcionarios.count(),
        'funcionarios_ativos': funcionarios.filter(is_active=True).count(),
        'funcionarios_inativos': funcionarios.filter(is_active=False).count(),
        'administradores': base.filter(is_admin=True).count(),
        'primeiro_acesso_pendente': funcionarios.filter(precisa_definir_senha=True).count(),
        'cnh_por_situacao': [
            {'valor': v, 'rotulo': r, 'total': contagem_cnh[v]} for v, r in SITUACOES_CNH
        ],
        'termo_por_situacao': [
            {'valor': v, 'rotulo': r, 'total': contagem_termo[v]} for v, r in SITUACOES_TERMO
        ],
        'cnh_enviadas_periodo': _contagem(
            filtros.documentos(DocumentoCNH.objects.all()), 'status', DocumentoCNH.STATUS_CHOICES,
        ),
        'termos_enviados_periodo': _contagem(
            filtros.documentos(TermoResponsabilidade.objects.all()),
            'status', TermoResponsabilidade.STATUS_CHOICES,
        ),
    }


def indicadores_vistorias(filtros):
    qs = filtros.vistorias(Vistoria.objects.all())
    por_tipo = _mapa(_contagem(qs, 'tipo', Vistoria.TIPO_CHOICES))
    por_unidade = _contagem(qs, 'unidade', Vistoria.UNIDADE_CHOICES)
    sem_unidade = qs.filter(Q(unidade__isnull=True) | Q(unidade='')).count()
    if sem_unidade:
        por_unidade.append({'valor': '', 'rotulo': 'Não informada', 'total': sem_unidade})

    reservas = filtros.reservas(Reserva.objects.all())
    km = km_por_reserva(reservas)
    checkins = (
        qs.filter(tipo='checkin')
        .values('unidade')
        .annotate(total=Count('id'))
    )
    por_unidade_checkin = [
        {
            'valor': item['unidade'] or '',
            'rotulo': dict(Vistoria.UNIDADE_CHOICES).get(item['unidade'], item['unidade'] or 'Não informada'),
            'total': item['total'],
        }
        for item in checkins
    ]
    return {
        'total': sum(por_tipo.values()),
        'checkins': por_tipo['checkin'],
        'checkouts': por_tipo['checkout'],
        'com_observacoes': qs.exclude(observacoes__isnull=True).exclude(observacoes='').count(),
        'com_fotos': qs.filter(fotos__isnull=False).distinct().count(),
        'em_andamento_sem_checkout': (
            reservas.filter(status='em_andamento')
            .exclude(vistorias__tipo='checkout').count()
        ),
        'km_rodados_total': sum(valor for _, valor in km.values()),
        'viagens_com_km': len(km),
        'por_unidade': por_unidade,
        'por_unidade_checkin': por_unidade_checkin,
    }


def calcular_indicadores(filtros, situacoes=None):
    return {
        'filtros': filtros.como_dict(),
        'gerado_em': timezone.now(),
        'frota': indicadores_frota(filtros),
        'reservas': indicadores_reservas(filtros),
        'usuarios': indicadores_usuarios(filtros, situacoes),
        'vistorias': indicadores_vistorias(filtros),
    }
