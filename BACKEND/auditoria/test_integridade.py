from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import Usuario

from .integridade import HASH_INICIAL, calcular_hash, verificar_cadeia
from .models import RegistroAuditoria, RegistroAuditoriaImutavel
from .services import registrar


def _registrar(ator, n):
    return registrar(
        ator=ator,
        acao='alterar_usuario',
        entidade='usuario',
        entidade_id=n,
        identificacao=f'Registro {n}',
        descricao=f'Alteração número {n} — acentuação preservada.',
        detalhes={'campos': ['nome', 'setor'], 'ordem': n},
    )


class CadeiaIntegridadeTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='int_admin', nome='Admin Integridade', password='senha123', is_admin=True,
        )
        self.registros = [_registrar(self.admin, n) for n in range(1, 5)]

    def test_registros_sao_encadeados_em_sequencia(self):
        sequencias = [r.sequencia for r in self.registros]
        self.assertEqual(sequencias, [1, 2, 3, 4])
        self.assertEqual(self.registros[0].hash_anterior, HASH_INICIAL)
        for anterior, atual in zip(self.registros, self.registros[1:]):
            self.assertEqual(atual.hash_anterior, anterior.hash)
        resultado = verificar_cadeia()
        self.assertTrue(resultado['integra'])
        self.assertEqual(resultado['total'], 4)
        self.assertEqual(resultado['ultimo_hash'], self.registros[-1].hash)

    def test_hash_confere_apos_ler_do_banco(self):
        for registro in RegistroAuditoria.objects.all():
            self.assertEqual(registro.hash, calcular_hash(registro))
            self.assertEqual(len(registro.hash), 64)
            self.assertEqual(registro.versao_hash, 1)

    def test_data_informada_pelo_chamador_e_ignorada(self):
        antigo = timezone.now() - timedelta(days=365)
        registro = RegistroAuditoria.objects.create(
            ator_nome='X', acao='criar_usuario', entidade='usuario',
            descricao='Tentativa de retroagir a data.', criado_em=antigo,
        )
        self.assertGreater(registro.criado_em, antigo + timedelta(days=364))
        self.assertTrue(verificar_cadeia()['integra'])

    def test_nao_permite_salvar_registro_existente(self):
        registro = RegistroAuditoria.objects.get(pk=self.registros[0].pk)
        registro.descricao = 'Alterado'
        with self.assertRaises(RegistroAuditoriaImutavel):
            registro.save()

    def test_nao_permite_excluir_registro(self):
        with self.assertRaises(RegistroAuditoriaImutavel):
            self.registros[0].delete()
        with self.assertRaises(RegistroAuditoriaImutavel):
            RegistroAuditoria.objects.filter(pk=self.registros[0].pk).delete()
        with self.assertRaises(RegistroAuditoriaImutavel):
            RegistroAuditoria.objects.all().delete()
        self.assertEqual(RegistroAuditoria.objects.count(), 4)

    def test_nao_permite_update_nem_operacoes_em_massa(self):
        with self.assertRaises(RegistroAuditoriaImutavel):
            RegistroAuditoria.objects.filter(pk=self.registros[0].pk).update(descricao='x')
        with self.assertRaises(RegistroAuditoriaImutavel):
            RegistroAuditoria.objects.bulk_create([RegistroAuditoria(descricao='x')])
        with self.assertRaises(RegistroAuditoriaImutavel):
            RegistroAuditoria.objects.bulk_update(self.registros, ['descricao'])
        with self.assertRaises(RegistroAuditoriaImutavel):
            RegistroAuditoria.objects.update_or_create(pk=self.registros[0].pk, defaults={'descricao': 'x'})

    def _adulterar(self, registro, **campos):
        """Simula alteração direta no banco, contornando as travas do ORM."""
        RegistroAuditoria._base_manager.filter(pk=registro.pk).update(**campos)

    def test_alteracao_da_descricao_e_detectada(self):
        self._adulterar(self.registros[1], descricao='Descrição forjada')
        resultado = verificar_cadeia()
        self.assertFalse(resultado['integra'])
        falha = resultado['falhas'][0]
        self.assertEqual(falha['motivo'], 'hash_invalido')
        self.assertEqual(falha['sequencia'], 2)

    def test_alteracao_do_responsavel_e_detectada(self):
        self._adulterar(self.registros[2], ator_nome='Outra Pessoa', ator_matricula='999')
        resultado = verificar_cadeia()
        self.assertFalse(resultado['integra'])
        self.assertEqual(resultado['falhas'][0]['sequencia'], 3)

    def test_alteracao_da_data_e_detectada(self):
        self._adulterar(self.registros[0], criado_em=timezone.now() - timedelta(days=10))
        resultado = verificar_cadeia()
        self.assertFalse(resultado['integra'])
        self.assertEqual(resultado['falhas'][0]['sequencia'], 1)

    def test_alteracao_da_justificativa_e_detectada(self):
        self._adulterar(self.registros[3], justificativa='Inserida depois')
        self.assertFalse(verificar_cadeia()['integra'])

    def test_recalcular_hash_sem_a_chave_nao_esconde_a_alteracao(self):
        registro = RegistroAuditoria.objects.get(pk=self.registros[1].pk)
        registro.descricao = 'Forjado'
        with override_settings(AUDITORIA_CHAVE_INTEGRIDADE='chave-do-atacante'):
            hash_forjado = calcular_hash(registro)
        self._adulterar(registro, descricao='Forjado', hash=hash_forjado)
        resultado = verificar_cadeia()
        self.assertFalse(resultado['integra'])
        motivos = {f['motivo'] for f in resultado['falhas']}
        self.assertIn('hash_invalido', motivos)
        self.assertIn('encadeamento_quebrado', motivos)

    def test_remocao_de_registro_quebra_a_cadeia(self):
        RegistroAuditoria._base_manager.filter(pk=self.registros[1].pk)._raw_delete(using='default')
        resultado = verificar_cadeia()
        self.assertFalse(resultado['integra'])
        motivos = {f['motivo'] for f in resultado['falhas']}
        self.assertIn('sequencia_ausente', motivos)
        self.assertIn('encadeamento_quebrado', motivos)

    def test_exclusao_definitiva_do_responsavel_nao_quebra_a_cadeia(self):
        outro = Usuario.objects.create_user(matricula='int_tmp', nome='Temporário', password='senha123')
        _registrar(outro, 99)
        outro.delete()
        registro = RegistroAuditoria.objects.get(entidade_id=99)
        self.assertIsNone(registro.ator_id)
        self.assertEqual(registro.ator_nome, 'Temporário')
        self.assertTrue(verificar_cadeia()['integra'])


class AuditoriaApiSomenteLeituraTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='ro_admin', nome='Admin', password='senha123', is_admin=True,
        )
        self.funcionario = Usuario.objects.create_user(
            matricula='ro_func', nome='Func', password='senha123',
        )
        self.registro = _registrar(self.admin, 1)

    def test_admin_nao_edita_nem_exclui_pela_api(self):
        self.client.force_authenticate(user=self.admin)
        base = '/api/auditoria/acoes/'
        for metodo in ('post', 'put', 'patch', 'delete'):
            resp = getattr(self.client, metodo)(base, {'descricao': 'x'}, format='json')
            self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, metodo)
        for metodo in ('put', 'patch', 'delete'):
            resp = getattr(self.client, metodo)(f'{base}{self.registro.id}/', {'descricao': 'x'}, format='json')
            self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, metodo)
        for caminho in ('/api/auditoria/integridade/', '/api/auditoria/opcoes/', '/api/auditoria/arquivos/'):
            resp = self.client.delete(caminho)
            self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, caminho)
        self.registro.refresh_from_db()
        self.assertTrue(RegistroAuditoria.objects.filter(pk=self.registro.pk).exists())
        self.assertNotEqual(self.registro.descricao, 'x')

    def test_integridade_somente_admin(self):
        self.client.force_authenticate(user=self.funcionario)
        self.assertEqual(
            self.client.get('/api/auditoria/integridade/').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/auditoria/integridade/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['integra'])
        self.assertEqual(resp.data['algoritmo'], 'HMAC-SHA256')
        self.assertEqual(resp.data['total'], 1)
