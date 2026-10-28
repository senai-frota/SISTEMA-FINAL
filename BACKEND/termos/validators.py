import re

from django.core.exceptions import ValidationError


def normalizar_documento(valor):
    """Retorna somente os dígitos de um CPF ou CNH."""
    return re.sub(r'\D', '', valor or '')


def _calcular_dv_cnh(base9):
    """
    Calcula os 2 dígitos verificadores da CNH a partir dos 9 primeiros
    dígitos, usando módulo 11 (mesmo princípio do dígito verificador do CPF).
    """
    dv1 = dv2 = 0
    peso1, peso2 = 9, 1
    for ch in base9:
        v = int(ch)
        dv1 += v * peso1
        dv2 += v * peso2
        peso1 -= 1
        peso2 += 1

    dv1 = dv1 % 11
    maior = False
    if dv1 > 9:
        dv1 = 0
        maior = True

    dv2 = dv2 % 11
    if maior:
        dv2 = dv2 + 9 if dv2 - 2 < 0 else dv2 - 2

    if dv2 > 9:
        dv2 = 0

    return f"{dv1}{dv2}"


def cnh_e_valida(valor):
    """
    Valida o número de registro da CNH (11 dígitos: 9 dígitos-base + 2
    dígitos verificadores calculados por módulo 11).

    Importante: esta é uma validação MATEMÁTICA/estrutural, igual à do CPF.
    Ela pega números digitados errado, incompletos ou inventados, mas NÃO
    confirma que a CNH existe de fato ou está com a habilitação ativa no
    Detran/Senatran — isso exigiria uma consulta paga (WSDenatran/SERPRO ou
    similar), já que não existe API pública gratuita para essa consulta.
    """
    if not valor:
        return False
    cnh = normalizar_documento(valor)
    if len(cnh) != 11:
        return False
    if cnh == cnh[0] * 11:  # ex: 00000000000, 11111111111 etc.
        return False
    return cnh[9:] == _calcular_dv_cnh(cnh[:9])


def validar_cnh(valor):
    """Validador de model/serializer: levanta ValidationError se inválida."""
    if not cnh_e_valida(valor):
        raise ValidationError(
            'Número de CNH inválido (dígito verificador não confere). '
            'Confira se digitou os 11 números corretamente.'
        )
