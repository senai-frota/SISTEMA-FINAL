"""
Sela os registros anteriores à cadeia de integridade, em ordem cronológica.

Cópia congelada do formato versão 1 de auditoria/integridade.py, para que esta
migração continue reproduzível mesmo se o formato evoluir.
"""
import hashlib
import hmac
import json
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import migrations

HASH_INICIAL = '0' * 64
CAMPOS = (
    'sequencia', 'hash_anterior', 'criado_em', 'ator_nome', 'ator_matricula',
    'acao', 'entidade', 'entidade_id', 'identificacao', 'descricao', 'detalhes',
    'justificativa', 'usuario_afetado_id', 'usuario_afetado_nome',
    'usuario_afetado_matricula',
)


def _hash_v1(registro):
    dados = {campo: getattr(registro, campo) for campo in CAMPOS}
    dados['criado_em'] = registro.criado_em.astimezone(dt_timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%S.%fZ'
    )
    dados['detalhes'] = registro.detalhes or {}
    dados['versao_hash'] = 1
    conteudo = json.dumps(
        dados, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
    ).encode('utf-8')
    chave = str(settings.AUDITORIA_CHAVE_INTEGRIDADE).encode('utf-8')
    return hmac.new(chave, conteudo, hashlib.sha256).hexdigest()


def selar(apps, schema_editor):
    Registro = apps.get_model('auditoria', 'RegistroAuditoria')
    anterior = HASH_INICIAL
    for sequencia, registro in enumerate(
        Registro.objects.order_by('criado_em', 'id').iterator(), start=1,
    ):
        registro.sequencia = sequencia
        registro.hash_anterior = anterior
        registro.versao_hash = 1
        registro.detalhes = registro.detalhes or {}
        registro.hash = _hash_v1(registro)
        Registro.objects.filter(pk=registro.pk).update(
            sequencia=registro.sequencia,
            hash_anterior=registro.hash_anterior,
            versao_hash=1,
            detalhes=registro.detalhes,
            hash=registro.hash,
        )
        anterior = registro.hash


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0002_integridade_campos'),
    ]

    operations = [
        migrations.RunPython(selar, migrations.RunPython.noop),
    ]
