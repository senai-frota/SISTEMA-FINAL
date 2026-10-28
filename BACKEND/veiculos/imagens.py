"""
Imagens de referência do veículo (galeria `FotoVeiculo` + capa `Veiculo.foto`).
Storage padrão do projeto: disco local ou S3/MinIO/Supabase conforme
USE_SUPABASE_STORAGE.

O tipo do arquivo é identificado pelo conteúdo (Pillow), não pela extensão nem
pelo Content-Type enviado pelo cliente. O arquivo é gravado com nome aleatório
e extensão correspondente ao formato real.
"""
import logging
import uuid

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

logger = logging.getLogger(__name__)

FORMATOS_PERMITIDOS = {
    'JPEG': 'jpg',
    'PNG': 'png',
    'WEBP': 'webp',
}
MAX_PIXELS = 40_000_000  # ~ 8000 x 5000

MSG_FORMATO = 'Envie uma imagem JPG, PNG ou WebP válida.'
MSG_VAZIO = 'O arquivo enviado está vazio.'


def tamanho_maximo_bytes():
    return int(getattr(settings, 'VEICULO_IMAGEM_TAMANHO_MAXIMO_MB', 5)) * 1024 * 1024


def maximo_fotos():
    return int(getattr(settings, 'VEICULO_IMAGEM_MAXIMO_FOTOS', 8))


def arquivos_enviados(request):
    """Aceita um ou vários arquivos nos campos `imagens` e/ou `imagem`."""
    arquivos = list(request.FILES.getlist('imagens')) + list(request.FILES.getlist('imagem'))
    vistos = set()
    unicos = []
    for arquivo in arquivos:
        chave = id(arquivo)
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(arquivo)
    return unicos


def garantir_galeria(veiculo):
    """Se só a capa antiga existir, passa a integrar a galeria sem duplicar o arquivo."""
    if veiculo.foto and not veiculo.fotos.exists():
        from .models import FotoVeiculo
        FotoVeiculo.objects.create(veiculo=veiculo, arquivo=veiculo.foto.name, ordem=0)


def sincronizar_capa(veiculo):
    """Mantém Veiculo.foto apontando para a primeira foto da galeria (mesmo arquivo)."""
    primeira = veiculo.fotos.order_by('ordem', 'id').first()
    nome_capa = primeira.arquivo.name if primeira and primeira.arquivo else ''
    nome_atual = veiculo.foto.name if veiculo.foto else ''
    if nome_capa == nome_atual:
        return
    if nome_capa:
        veiculo.foto.name = nome_capa
    else:
        veiculo.foto = None
    veiculo.save(update_fields=['foto', 'atualizado_em'])


def validar_imagem(arquivo):
    """Valida tamanho e conteúdo; devolve metadados {formato, extensao, largura, altura, tamanho_bytes}."""
    tamanho = getattr(arquivo, 'size', 0) or 0
    if tamanho <= 0:
        raise serializers.ValidationError(MSG_VAZIO)
    limite = tamanho_maximo_bytes()
    if tamanho > limite:
        raise serializers.ValidationError(
            f'A imagem deve ter no máximo {limite // (1024 * 1024)} MB.'
        )

    try:
        arquivo.seek(0)
        with Image.open(arquivo) as imagem:
            formato = imagem.format
            largura, altura = imagem.size
            if formato not in FORMATOS_PERMITIDOS:
                raise serializers.ValidationError(MSG_FORMATO)
            if largura * altura > MAX_PIXELS:
                raise serializers.ValidationError('A imagem tem resolução grande demais.')
            imagem.verify()
        # verify() não decodifica os pixels; load() detecta arquivos truncados.
        arquivo.seek(0)
        with Image.open(arquivo) as imagem:
            imagem.load()
    except serializers.ValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise serializers.ValidationError(MSG_FORMATO)
    finally:
        arquivo.seek(0)

    return {
        'formato': formato,
        'extensao': FORMATOS_PERMITIDOS[formato],
        'largura': largura,
        'altura': altura,
        'tamanho_bytes': tamanho,
    }


def nome_aleatorio(extensao):
    return f'{uuid.uuid4().hex}.{extensao}'


def apagar_do_storage(storage, nome):
    """Remove um arquivo antigo; falha no storage não desfaz a operação já gravada."""
    if not nome:
        return
    try:
        storage.delete(nome)
    except Exception:  # noqa: BLE001 - storage remoto pode falhar por rede/permissão
        logger.warning('Não foi possível remover o arquivo antigo %s do storage.', nome, exc_info=True)
