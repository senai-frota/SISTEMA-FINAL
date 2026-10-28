"""
Cadeia de integridade da auditoria.

Formato versão 1 (versao_hash = 1)
-----------------------------------
hash = HMAC-SHA256(chave, conteudo_canonico), em hexadecimal (64 caracteres).

- chave: settings.AUDITORIA_CHAVE_INTEGRIDADE (padrão: SECRET_KEY). Sem a chave
  não é possível recalcular hashes válidos, mesmo com acesso de escrita ao banco.
- conteudo_canonico: JSON UTF-8 com chaves ordenadas e sem espaços contendo
  CAMPOS_PROTEGIDOS + versao_hash. `criado_em` é serializado em UTC com
  microssegundos (AAAA-MM-DDTHH:MM:SS.ffffffZ).
- hash_anterior: hash do registro de sequência imediatamente anterior
  (HASH_INICIAL no primeiro registro). Assim, alterar ou remover um registro
  quebra a verificação dele e/ou do seguinte.

Fica de fora do hash apenas `ator_id` (chave estrangeira que o banco zera se o
usuário for excluído definitivamente). O responsável continua protegido pelo
snapshot `ator_nome` + `ator_matricula`.

Limitações: quem tiver acesso direto ao banco E à chave consegue reescrever a
cadeia inteira; a remoção dos últimos registros só é detectável comparando com
uma contagem/hash conhecido guardado fora do banco (`ultima_sequencia` e
`ultimo_hash` retornados por verificar_cadeia).
"""
import hashlib
import hmac
import json
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

VERSAO_HASH = 1
HASH_INICIAL = '0' * 64
TENTATIVAS_GRAVACAO = 5

CAMPOS_PROTEGIDOS = (
    'sequencia',
    'hash_anterior',
    'criado_em',
    'ator_nome',
    'ator_matricula',
    'acao',
    'entidade',
    'entidade_id',
    'identificacao',
    'descricao',
    'detalhes',
    'justificativa',
    'usuario_afetado_id',
    'usuario_afetado_nome',
    'usuario_afetado_matricula',
)


def _data_utc(valor):
    return valor.astimezone(dt_timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def conteudo_canonico(registro):
    dados = {campo: getattr(registro, campo) for campo in CAMPOS_PROTEGIDOS}
    dados['criado_em'] = _data_utc(registro.criado_em)
    dados['detalhes'] = registro.detalhes or {}
    dados['versao_hash'] = registro.versao_hash
    return json.dumps(
        dados, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
    ).encode('utf-8')


def calcular_hash(registro):
    chave = str(settings.AUDITORIA_CHAVE_INTEGRIDADE).encode('utf-8')
    return hmac.new(chave, conteudo_canonico(registro), hashlib.sha256).hexdigest()


def gravar_encadeado(registro, inserir, using=None):
    """
    Define sequência, hash anterior, data/hora e hash e executa `inserir`.
    `sequencia` é única: se duas gravações concorrentes disputarem a mesma
    posição, a perdedora recebe IntegrityError e tenta de novo na próxima.
    """
    from .models import RegistroAuditoria

    for tentativa in range(TENTATIVAS_GRAVACAO):
        try:
            with transaction.atomic(using=using):
                ultimo = (
                    RegistroAuditoria.objects.using(using)
                    .order_by('-sequencia')
                    .only('sequencia', 'hash')
                    .first()
                )
                registro.sequencia = (ultimo.sequencia + 1) if ultimo else 1
                registro.hash_anterior = ultimo.hash if ultimo else HASH_INICIAL
                registro.criado_em = timezone.now()
                registro.versao_hash = VERSAO_HASH
                registro.detalhes = registro.detalhes or {}
                registro.hash = calcular_hash(registro)
                inserir()
                return registro
        except IntegrityError:
            registro.pk = None
            registro._state.adding = True
            if tentativa == TENTATIVAS_GRAVACAO - 1:
                raise


def verificar_cadeia():
    """
    Recalcula toda a cadeia em ordem de sequência.

    Retorna {'integra', 'total', 'ultimo_hash', 'ultima_sequencia', 'falhas'}.
    Cada falha traz sequência, id e motivo:
      - hash_invalido: conteúdo do registro foi alterado;
      - encadeamento_quebrado: hash_anterior não confere com o registro anterior;
      - sequencia_ausente: há lacuna na sequência (registro removido);
      - versao_desconhecida: formato de hash não suportado.
    """
    from .models import RegistroAuditoria

    falhas = []
    total = 0
    anterior_hash = HASH_INICIAL
    esperada = 1
    ultimo = None
    for registro in RegistroAuditoria.objects.order_by('sequencia').iterator(chunk_size=500):
        total += 1
        if registro.sequencia != esperada:
            falhas.append({
                'sequencia': esperada,
                'id': None,
                'motivo': 'sequencia_ausente',
                'detalhe': f'Esperada sequência {esperada}, encontrada {registro.sequencia}.',
            })
        if registro.versao_hash != VERSAO_HASH:
            falhas.append({
                'sequencia': registro.sequencia, 'id': registro.id,
                'motivo': 'versao_desconhecida',
                'detalhe': f'Versão {registro.versao_hash} não suportada.',
            })
        elif not hmac.compare_digest(registro.hash, calcular_hash(registro)):
            falhas.append({
                'sequencia': registro.sequencia, 'id': registro.id,
                'motivo': 'hash_invalido',
                'detalhe': 'O conteúdo do registro não confere com o hash gravado.',
            })
        if registro.hash_anterior != anterior_hash:
            falhas.append({
                'sequencia': registro.sequencia, 'id': registro.id,
                'motivo': 'encadeamento_quebrado',
                'detalhe': 'O hash anterior não confere com o registro precedente.',
            })
        anterior_hash = registro.hash
        esperada = registro.sequencia + 1
        ultimo = registro

    return {
        'integra': not falhas,
        'total': total,
        'ultima_sequencia': ultimo.sequencia if ultimo else 0,
        'ultimo_hash': ultimo.hash if ultimo else HASH_INICIAL,
        'versao_hash': VERSAO_HASH,
        'algoritmo': 'HMAC-SHA256',
        'falhas': falhas[:50],
        'total_falhas': len(falhas),
    }
