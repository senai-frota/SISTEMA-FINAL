"""
Validação de contexto de dispositivo para check-in/check-out.

Não depende exclusivamente do User-Agent: combina
Client Hints (Sec-CH-UA-Mobile), cabeçalho explícito do cliente
(X-Client-Form-Factor) e, como defesa adicional, sinais do UA.
"""
import re

from rest_framework.exceptions import ValidationError

MSG_SOMENTE_MOBILE = (
    'Check-in e check-out só podem ser realizados em dispositivo móvel '
    '(smartphone ou tablet).'
)

# Ângulos já definidos em FotoVistoria.DESCRICAO_CHOICES
FOTOS_OBRIGATORIAS = (
    'frente',
    'tras',
    'lateral_esq',
    'lateral_dir',
    'painel',
)

_UA_MOBILE = re.compile(
    r'Android|iPhone|iPod|iPad|Mobile|webOS|BlackBerry|IEMobile|Opera Mini|Tablet',
    re.IGNORECASE,
)
_UA_DESKTOP_CLARO = re.compile(
    r'Windows NT|Macintosh|X11|CrOS',
    re.IGNORECASE,
)


def _header(request, name, meta_fallback):
    # DRF Request expõe .headers; WSGI usa META
    if hasattr(request, 'headers'):
        valor = request.headers.get(name)
        if valor is not None:
            return valor.strip()
    return (request.META.get(meta_fallback) or '').strip()


def cliente_parece_mobile(request):
    """
    Retorna True se o pedido aparenta vir de um cliente móvel.

    Critérios (em ordem):
    1. Sec-CH-UA-Mobile == ?1 → mobile
    2. Sec-CH-UA-Mobile == ?0 → não mobile
    3. X-Client-Form-Factor deve ser "mobile"
    4. Se o UA é claramente desktop sem tokens móveis → rejeita
    5. Caso contrário, aceita se form-factor=mobile (ex.: tablet / UA atípico)
    """
    sec = _header(request, 'Sec-CH-UA-Mobile', 'HTTP_SEC_CH_UA_MOBILE')
    if sec == '?1':
        return True
    if sec == '?0':
        return False

    form_factor = _header(
        request, 'X-Client-Form-Factor', 'HTTP_X_CLIENT_FORM_FACTOR'
    ).lower()
    if form_factor != 'mobile':
        return False

    ua = _header(request, 'User-Agent', 'HTTP_USER_AGENT')
    if not ua:
        # Sem UA e sem Client Hint: exige apenas o form-factor do cliente.
        return True

    if _UA_MOBILE.search(ua):
        return True

    if _UA_DESKTOP_CLARO.search(ua):
        return False

    # UA desconhecido + form-factor mobile: aceita (tablets / WebViews).
    return True


def exigir_cliente_mobile(request):
    if not cliente_parece_mobile(request):
        raise ValidationError({'detail': MSG_SOMENTE_MOBILE})


def validar_fotos_obrigatorias(arquivos, descricoes):
    """
    Exige exatamente as 5 fotos com os ângulos já modelados em FotoVistoria.
    """
    if len(arquivos) != len(FOTOS_OBRIGATORIAS):
        raise ValidationError({
            'fotos': [
                f'Envie exatamente {len(FOTOS_OBRIGATORIAS)} fotos '
                f'(frente, traseira, laterais e painel).'
            ],
        })

    normalizadas = [(d or '').strip() for d in descricoes]
    if len(normalizadas) < len(arquivos):
        normalizadas.extend([''] * (len(arquivos) - len(normalizadas)))

    faltando = [angulo for angulo in FOTOS_OBRIGATORIAS if angulo not in normalizadas]
    if faltando:
        raise ValidationError({
            'descricoes': [
                'Todas as fotos obrigatórias devem ser enviadas com o ângulo correto: '
                + ', '.join(FOTOS_OBRIGATORIAS)
                + '.'
            ],
        })

    # Sem ângulos duplicados
    if len(set(normalizadas[: len(arquivos)])) != len(arquivos):
        raise ValidationError({
            'descricoes': ['Cada ângulo obrigatório deve aparecer uma única vez.'],
        })
