"""Regras de conta ativa/inativa vinculadas ao termo anual."""
from django.utils import timezone

from .models import TermoResponsabilidade, usuario_possui_termo_valido, VALIDADE_DIAS


def _registrar_status_conta(usuario, ativo):
    from auditoria.services import registrar

    if ativo:
        acao = 'ativar_usuario'
        descricao = (
            f'A conta de {usuario.nome} foi ativada porque o termo de responsabilidade está válido.'
        )
    else:
        acao = 'inativar_usuario'
        descricao = (
            f'A conta de {usuario.nome} foi inativada porque o termo de responsabilidade não está válido.'
        )
    registrar(
        ator=None,
        acao=acao,
        entidade='usuario',
        entidade_id=usuario.id,
        identificacao=f'{usuario.nome} ({usuario.matricula})',
        descricao=descricao,
        detalhes={'origem': 'termo'},
    )


def termo_vigente(usuario):
    return (
        TermoResponsabilidade.objects
        .filter(usuario=usuario, status='aprovado')
        .order_by('-data_decisao', '-id')
        .first()
    )


def sincronizar_status_conta(usuario):
    """
    Se o termo vigente venceu, marca a conta como inativa.
    Admins não são desativados automaticamente por termo.
    """
    if usuario.is_admin:
        return usuario

    vigente = termo_vigente(usuario)
    if vigente and vigente.esta_valido:
        if not usuario.is_active:
            usuario.is_active = True
            usuario.save(update_fields=['is_active', 'atualizado_em'])
            _registrar_status_conta(usuario, True)
        return usuario

    # Sem termo válido: conta deve ficar inativa (exceto se nunca teve termo e
    # ainda está no fluxo inicial — novos usuários começam ativos e precisam
    # enviar o termo; a primeira expiração/ausência após ter tido termo
    # inativa. Sem nenhum termo aprovado histórico, também inativa reservas
    # via checagem de termo, mas mantém login.)
    teve_aprovado = TermoResponsabilidade.objects.filter(
        usuario=usuario, status='aprovado'
    ).exists()
    if teve_aprovado and usuario.is_active:
        usuario.is_active = False
        usuario.save(update_fields=['is_active', 'atualizado_em'])
        _registrar_status_conta(usuario, False)
    elif not teve_aprovado and not TermoResponsabilidade.objects.filter(usuario=usuario).exists():
        # Usuário novo sem termo: permanece ativo para login, mas reservas
        # serão bloqueadas pela validação de termo.
        pass
    elif not usuario_possui_termo_valido(usuario) and teve_aprovado:
        if usuario.is_active:
            usuario.is_active = False
            usuario.save(update_fields=['is_active', 'atualizado_em'])
            _registrar_status_conta(usuario, False)
    return usuario


def ativar_conta(usuario):
    if not usuario.is_active:
        usuario.is_active = True
        usuario.save(update_fields=['is_active', 'atualizado_em'])
        _registrar_status_conta(usuario, True)


def desativar_conta(usuario):
    if usuario.is_admin:
        return
    if usuario.is_active:
        usuario.is_active = False
        usuario.save(update_fields=['is_active', 'atualizado_em'])
        _registrar_status_conta(usuario, False)


def situacao_termo(usuario):
    """(situacao, termo_de_referencia) sem alterar o status da conta."""
    vigente = termo_vigente(usuario)
    pendente = (
        TermoResponsabilidade.objects
        .filter(usuario=usuario, status='pendente')
        .order_by('-criado_em')
        .first()
    )
    ultimo = (
        TermoResponsabilidade.objects
        .filter(usuario=usuario)
        .order_by('-criado_em')
        .first()
    )

    if vigente and vigente.esta_valido:
        situacao = 'valido'
        ref = vigente
    elif pendente:
        situacao = 'pendente'
        ref = pendente
    elif vigente and not vigente.esta_valido:
        situacao = 'vencido'
        ref = vigente
    elif ultimo and ultimo.status == 'rejeitado':
        situacao = 'rejeitado'
        ref = ultimo
    else:
        situacao = 'sem_termo'
        ref = None
    return situacao, ref


def resumo_termo_usuario(usuario):
    sincronizar_status_conta(usuario)
    usuario.refresh_from_db(fields=['is_active'])

    situacao, ref = situacao_termo(usuario)
    return {
        'situacao': situacao,
        'conta_ativa': usuario.is_active,
        'pode_reservar': usuario.is_active and usuario_possui_termo_valido(usuario),
        'validade_dias': VALIDADE_DIAS,
        'data_validade': ref.data_validade if ref else None,
        'dias_restantes': ref.dias_restantes if ref and ref.status == 'aprovado' else None,
        'termo_id': ref.id if ref else None,
        'mensagem': _mensagem_termo(situacao, usuario, ref),
    }


def _mensagem_termo(situacao, usuario, ref):
    if situacao == 'valido':
        return (
            f'Termo válido até {ref.data_validade.strftime("%d/%m/%Y")}. '
            f'Conta ativa.'
        )
    if situacao == 'pendente':
        return (
            'Termo aguardando análise do gestor. '
            'A conta permanece restrita para novas reservas até a aprovação.'
        )
    if situacao == 'vencido':
        return (
            'Termo vencido. A conta está inativa. Retire o documento na secretaria, '
            'assine e envie o arquivo pelo sistema para renovação.'
        )
    if situacao == 'rejeitado':
        return (
            'Último termo foi rejeitado. A conta permanece inativa. '
            'Envie um novo documento assinado.'
        )
    return (
        'Nenhum termo de responsabilidade cadastrado. '
        'Retire o documento na secretaria, assine e envie pelo sistema.'
    )
