import logging

import requests

logger = logging.getLogger(__name__)

PARALLELUM_BASE_URL = "https://parallelum.com.br/fipe/api/v1/carros"

MSG_FIPE_INDISPONIVEL = (
    'Consulta FIPE indisponível no momento. Cadastre o veículo manualmente.'
)


class FipeIndisponivel(Exception):
    """API FIPE Parallelum inacessível ou recusou a consulta."""


def _get_json(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.warning('Consulta FIPE falhou: %s', exc)
        raise FipeIndisponivel(MSG_FIPE_INDISPONIVEL) from exc


def buscar_marcas():
    return _get_json(f"{PARALLELUM_BASE_URL}/marcas")


def buscar_modelos(codigo_marca):
    return _get_json(f"{PARALLELUM_BASE_URL}/marcas/{codigo_marca}/modelos")


def buscar_anos(codigo_marca, codigo_modelo):
    return _get_json(
        f"{PARALLELUM_BASE_URL}/marcas/{codigo_marca}/modelos/{codigo_modelo}/anos"
    )


def buscar_detalhes(codigo_marca, codigo_modelo, codigo_ano):
    return _get_json(
        f"{PARALLELUM_BASE_URL}/marcas/{codigo_marca}/modelos/"
        f"{codigo_modelo}/anos/{codigo_ano}"
    )
