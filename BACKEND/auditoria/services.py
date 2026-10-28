"""Registro de ações. Nunca persiste senha, token ou conteúdo de arquivo."""
from datetime import date, datetime

from .models import RegistroAuditoria

_BLOQUEADOS = (
    'password',
    'senha',
    'token',
    'secret',
    'credential',
    'authorization',
    'refresh',
    'arquivo',
    'foto',
    'file',
)


def _chave_permitida(chave):
    nome = str(chave).lower()
    return not any(parte in nome for parte in _BLOQUEADOS)


def _valor_simples(valor):
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return limpar_detalhes(valor)
    if isinstance(valor, (list, tuple)):
        return [_valor_simples(item) for item in valor]
    if hasattr(valor, 'read') or hasattr(valor, 'chunks'):
        return None
    if hasattr(valor, 'pk'):
        return valor.pk
    return str(valor)


def limpar_detalhes(detalhes):
    if not isinstance(detalhes, dict):
        return {}
    limpo = {}
    for chave, valor in detalhes.items():
        if not _chave_permitida(chave):
            continue
        convertido = _valor_simples(valor)
        if convertido is None and valor is not None:
            continue
        limpo[str(chave)] = convertido
    return limpo


MSG_JUSTIFICATIVA_OBRIGATORIA = 'Informe a justificativa da recusa.'


def normalizar_justificativa(valor):
    """Justificativa sem espaços nas extremidades; '' se vazia ou só espaços."""
    return (valor or '').strip() if isinstance(valor, str) else ''


def exigir_justificativa(valor, campo='observacao_admin'):
    from rest_framework import serializers

    texto = normalizar_justificativa(valor)
    if not texto:
        raise serializers.ValidationError({campo: [MSG_JUSTIFICATIVA_OBRIGATORIA]})
    return texto


def registrar(
    *, ator, acao, entidade, entidade_id, identificacao, descricao,
    detalhes=None, justificativa='', usuario_afetado=None,
):
    usuario = ator if getattr(ator, 'pk', None) else None
    afetado = usuario_afetado if getattr(usuario_afetado, 'pk', None) else None
    return RegistroAuditoria.objects.create(
        ator=usuario,
        ator_nome=(getattr(ator, 'nome', '') or 'Sistema')[:150],
        ator_matricula=(getattr(ator, 'matricula', '') or '')[:50],
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        identificacao=(identificacao or '')[:200],
        descricao=descricao,
        detalhes=limpar_detalhes(detalhes),
        justificativa=normalizar_justificativa(justificativa),
        usuario_afetado_id=afetado.pk if afetado else None,
        usuario_afetado_nome=(getattr(afetado, 'nome', '') or '')[:150],
        usuario_afetado_matricula=(getattr(afetado, 'matricula', '') or '')[:50],
    )
