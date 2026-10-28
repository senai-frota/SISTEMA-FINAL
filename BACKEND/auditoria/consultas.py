"""Consulta paginável de arquivos já armazenados, sem copiar o arquivo."""
import os
from collections import defaultdict

from django.core.files.storage import default_storage
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    F,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Cast, Concat
from django.utils.dateparse import parse_date

from termos.models import TermoResponsabilidade
from usuarios.models import DocumentoCNH, Usuario
from veiculos.models import Veiculo
from vistorias.models import FotoVistoria, Vistoria
from reservas.models import Reserva

from .models import RegistroAuditoria

COLUNAS = (
    'tipo',
    'origem_id',
    'titulo',
    'caminho',
    'enviado_em',
    'autor_id',
    'autor_nome',
    'vinculo',
    'entidade_id',
    'entidade_rotulo',
    'registro_ativo',
)

EXTENSOES_IMAGEM = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

TIPOS_ARQUIVO = (
    ('cnh', 'CNH'),
    ('termo', 'Termo assinado'),
    ('foto_vistoria', 'Foto de vistoria'),
    ('foto_veiculo', 'Foto de veículo'),
)


def _inteiro(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _periodo(queryset, params, campo):
    inicio = parse_date(params.get('de') or '')
    fim = parse_date(params.get('ate') or '')
    if inicio:
        queryset = queryset.filter(**{f'{campo}__date__gte': inicio})
    if fim:
        queryset = queryset.filter(**{f'{campo}__date__lte': fim})
    return queryset


def _situacao(queryset, params):
    situacao = (params.get('situacao') or '').lower()
    if situacao == 'ativos':
        return queryset.filter(registro_ativo=True)
    if situacao == 'inativos':
        return queryset.filter(registro_ativo=False)
    return queryset


def _com_arquivo(queryset, campo):
    return queryset.exclude(**{campo: ''}).exclude(**{f'{campo}__isnull': True})


def _qs_cnh(params):
    qs = _com_arquivo(DocumentoCNH.objects.all(), 'arquivo')
    qs = _periodo(qs, params, 'criado_em')
    usuario_id = _inteiro(params.get('usuario'))
    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)
    busca = (params.get('busca') or '').strip()
    if busca:
        qs = qs.filter(
            Q(usuario__nome__icontains=busca) | Q(usuario__matricula__icontains=busca)
        )
    qs = qs.annotate(
        tipo=Value('cnh', output_field=CharField()),
        origem_id=F('id'),
        titulo=Value('CNH', output_field=CharField()),
        caminho=F('arquivo'),
        enviado_em=F('criado_em'),
        autor_id=F('usuario_id'),
        autor_nome=F('usuario__nome'),
        vinculo=Value('usuario', output_field=CharField()),
        entidade_id=F('usuario_id'),
        entidade_rotulo=Concat(
            F('usuario__nome'),
            Value(' ('),
            F('usuario__matricula'),
            Value(')'),
            output_field=CharField(),
        ),
        registro_ativo=F('usuario__is_active'),
    )
    return _situacao(qs, params).order_by().values(*COLUNAS)


def _qs_termo(params):
    qs = _com_arquivo(TermoResponsabilidade.objects.all(), 'arquivo_pdf')
    qs = _periodo(qs, params, 'criado_em')
    usuario_id = _inteiro(params.get('usuario'))
    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)
    busca = (params.get('busca') or '').strip()
    if busca:
        qs = qs.filter(
            Q(usuario__nome__icontains=busca) | Q(usuario__matricula__icontains=busca)
        )
    qs = qs.annotate(
        tipo=Value('termo', output_field=CharField()),
        origem_id=F('id'),
        titulo=Value('Termo assinado', output_field=CharField()),
        caminho=F('arquivo_pdf'),
        enviado_em=F('criado_em'),
        autor_id=F('usuario_id'),
        autor_nome=F('usuario__nome'),
        vinculo=Value('usuario', output_field=CharField()),
        entidade_id=F('usuario_id'),
        entidade_rotulo=Concat(
            F('usuario__nome'),
            Value(' ('),
            F('usuario__matricula'),
            Value(')'),
            output_field=CharField(),
        ),
        registro_ativo=F('usuario__is_active'),
    )
    return _situacao(qs, params).order_by().values(*COLUNAS)


def _qs_foto_vistoria(params):
    qs = _com_arquivo(FotoVistoria.objects.all(), 'foto')
    qs = _periodo(qs, params, 'upload_em')
    usuario_id = _inteiro(params.get('usuario'))
    if usuario_id:
        qs = qs.filter(vistoria__realizada_por_id=usuario_id)
    busca = (params.get('busca') or '').strip()
    if busca:
        qs = qs.filter(
            Q(vistoria__realizada_por__nome__icontains=busca)
            | Q(vistoria__reserva__veiculo__placa__icontains=busca)
            | Q(vistoria__reserva__usuario__nome__icontains=busca)
        )
    qs = qs.annotate(
        tipo=Value('foto_vistoria', output_field=CharField()),
        origem_id=F('id'),
        titulo=Case(
            When(descricao='frente', then=Value('Frente')),
            When(descricao='tras', then=Value('Traseira')),
            When(descricao='lateral_esq', then=Value('Lateral esquerda')),
            When(descricao='lateral_dir', then=Value('Lateral direita')),
            When(descricao='painel', then=Value('Painel / interior')),
            default=Value('Foto da vistoria'),
            output_field=CharField(),
        ),
        caminho=F('foto'),
        enviado_em=F('upload_em'),
        autor_id=F('vistoria__realizada_por_id'),
        autor_nome=F('vistoria__realizada_por__nome'),
        vinculo=Value('vistoria', output_field=CharField()),
        entidade_id=F('vistoria_id'),
        entidade_rotulo=Concat(
            Value('Reserva #'),
            Cast('vistoria__reserva_id', CharField()),
            Value(' · '),
            F('vistoria__reserva__veiculo__placa'),
            output_field=CharField(),
        ),
        registro_ativo=Case(
            When(
                Q(vistoria__reserva__usuario__is_active=True)
                & ~Q(vistoria__reserva__veiculo__status='inativo'),
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )
    return _situacao(qs, params).order_by().values(*COLUNAS)


def _qs_foto_veiculo(params):
    if _inteiro(params.get('usuario')):
        return None
    qs = _com_arquivo(Veiculo.objects.all(), 'foto')
    qs = _periodo(qs, params, 'criado_em')
    busca = (params.get('busca') or '').strip()
    if busca:
        qs = qs.filter(
            Q(placa__icontains=busca)
            | Q(modelo__icontains=busca)
            | Q(marca__icontains=busca)
        )
    qs = qs.annotate(
        tipo=Value('foto_veiculo', output_field=CharField()),
        origem_id=F('id'),
        titulo=Value('Foto do veículo', output_field=CharField()),
        caminho=F('foto'),
        enviado_em=F('criado_em'),
        autor_id=Value(None, output_field=IntegerField()),
        autor_nome=Value('', output_field=CharField()),
        vinculo=Value('veiculo', output_field=CharField()),
        entidade_id=F('id'),
        entidade_rotulo=Concat(
            F('marca'),
            Value(' '),
            F('modelo'),
            Value(' ('),
            F('placa'),
            Value(')'),
            output_field=CharField(),
        ),
        registro_ativo=Case(
            When(status='inativo', then=Value(False)),
            default=Value(True),
            output_field=BooleanField(),
        ),
    )
    return _situacao(qs, params).order_by().values(*COLUNAS)


def consulta_arquivos(params):
    tipo = (params.get('tipo') or '').strip()
    construtores = {
        'cnh': _qs_cnh,
        'termo': _qs_termo,
        'foto_vistoria': _qs_foto_vistoria,
        'foto_veiculo': _qs_foto_veiculo,
    }
    if tipo in construtores:
        escolhidos = [construtores[tipo]]
    else:
        escolhidos = list(construtores.values())

    partes = [construir(params) for construir in escolhidos]
    partes = [parte for parte in partes if parte is not None]
    if not partes:
        return DocumentoCNH.objects.none().annotate(
            tipo=Value('cnh', output_field=CharField()),
            origem_id=F('id'),
            titulo=Value('', output_field=CharField()),
            caminho=F('arquivo'),
            enviado_em=F('criado_em'),
            autor_id=F('usuario_id'),
            autor_nome=F('usuario__nome'),
            vinculo=Value('usuario', output_field=CharField()),
            entidade_id=F('usuario_id'),
            entidade_rotulo=Value('', output_field=CharField()),
            registro_ativo=F('usuario__is_active'),
        ).order_by().values(*COLUNAS)

    consulta = partes[0]
    for parte in partes[1:]:
        consulta = consulta.union(parte, all=True)
    return consulta.order_by('-enviado_em')


def serializar_arquivo(linha, request):
    caminho = linha.get('caminho') or ''
    extensao = os.path.splitext(str(caminho))[1].lower()
    url = None
    if caminho:
        try:
            url = default_storage.url(caminho)
        except Exception:
            url = None
        if url and request is not None and not str(url).startswith(('http://', 'https://')):
            url = request.build_absolute_uri(url)
    autor = (linha.get('autor_nome') or '').strip()
    return {
        'tipo': linha.get('tipo'),
        'id': linha.get('origem_id'),
        'titulo': linha.get('titulo') or 'Arquivo',
        'nome_arquivo': os.path.basename(str(caminho)) if caminho else '',
        'enviado_em': linha.get('enviado_em'),
        'autor_id': linha.get('autor_id'),
        'autor_nome': autor or '—',
        'entidade': linha.get('vinculo'),
        'entidade_id': linha.get('entidade_id'),
        'entidade_rotulo': linha.get('entidade_rotulo') or '',
        'registro_ativo': linha.get('registro_ativo'),
        'imagem': extensao in EXTENSOES_IMAGEM,
        'url': url,
    }


def _ids(modelo, **filtro):
    return modelo.objects.filter(**filtro).values('id')


def filtrar_situacao_acoes(queryset, situacao):
    """Mantém logs cujo registro relacionado está ativo ou inativo agora."""
    ativos = situacao == 'ativos'
    if situacao not in ('ativos', 'inativos'):
        return queryset

    usuario_ids = _ids(Usuario, is_active=ativos)
    if ativos:
        veiculo_ids = Veiculo.objects.exclude(status='inativo').values('id')
    else:
        veiculo_ids = _ids(Veiculo, status='inativo')
    cnh_ids = _ids(DocumentoCNH, usuario__is_active=ativos)
    termo_ids = _ids(TermoResponsabilidade, usuario__is_active=ativos)
    reserva_ids = _ids(Reserva, usuario__is_active=ativos)
    vistoria_ids = _ids(Vistoria, reserva__usuario__is_active=ativos)
    foto_ids = _ids(FotoVistoria, vistoria__reserva__usuario__is_active=ativos)

    return queryset.filter(
        Q(entidade=RegistroAuditoria.Entidade.USUARIO, entidade_id__in=usuario_ids)
        | Q(entidade=RegistroAuditoria.Entidade.VEICULO, entidade_id__in=veiculo_ids)
        | Q(entidade=RegistroAuditoria.Entidade.CNH, entidade_id__in=cnh_ids)
        | Q(entidade=RegistroAuditoria.Entidade.TERMO, entidade_id__in=termo_ids)
        | Q(entidade=RegistroAuditoria.Entidade.RESERVA, entidade_id__in=reserva_ids)
        | Q(entidade=RegistroAuditoria.Entidade.VISTORIA, entidade_id__in=vistoria_ids)
        | Q(entidade=RegistroAuditoria.Entidade.FOTO, entidade_id__in=foto_ids)
    )


def mapa_registro_ativo(registros):
    por_entidade = defaultdict(set)
    for registro in registros:
        if registro.entidade_id:
            por_entidade[registro.entidade].add(registro.entidade_id)

    mapa = {}

    def marcar(entidade, linhas, ativo):
        for linha in linhas:
            mapa[(entidade, linha['id'])] = bool(linha[ativo]) if not isinstance(linha[ativo], bool) else linha[ativo]

    if por_entidade['usuario']:
        marcar(
            'usuario',
            Usuario.objects.filter(id__in=por_entidade['usuario']).values('id', 'is_active'),
            'is_active',
        )
    if por_entidade['veiculo']:
        for linha in Veiculo.objects.filter(id__in=por_entidade['veiculo']).values('id', 'status'):
            mapa[('veiculo', linha['id'])] = linha['status'] != 'inativo'
    if por_entidade['cnh']:
        for linha in DocumentoCNH.objects.filter(id__in=por_entidade['cnh']).values('id', 'usuario__is_active'):
            mapa[('cnh', linha['id'])] = linha['usuario__is_active']
    if por_entidade['termo']:
        for linha in TermoResponsabilidade.objects.filter(id__in=por_entidade['termo']).values('id', 'usuario__is_active'):
            mapa[('termo', linha['id'])] = linha['usuario__is_active']
    if por_entidade['reserva']:
        for linha in Reserva.objects.filter(id__in=por_entidade['reserva']).values('id', 'usuario__is_active'):
            mapa[('reserva', linha['id'])] = linha['usuario__is_active']
    if por_entidade['vistoria']:
        for linha in Vistoria.objects.filter(id__in=por_entidade['vistoria']).values('id', 'reserva__usuario__is_active'):
            mapa[('vistoria', linha['id'])] = linha['reserva__usuario__is_active']
    if por_entidade['foto']:
        for linha in FotoVistoria.objects.filter(id__in=por_entidade['foto']).values(
            'id', 'vistoria__reserva__usuario__is_active'
        ):
            mapa[('foto', linha['id'])] = linha['vistoria__reserva__usuario__is_active']
    return mapa
