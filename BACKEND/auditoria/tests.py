from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from reservas.models import Reserva
from usuarios.models import Usuario
from veiculos.models import Veiculo

from .models import RegistroAuditoria
from .services import limpar_detalhes, registrar


class AuditoriaPermissaoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='aud_admin', nome='Admin Auditoria', password='senha123', is_admin=True,
        )
        self.funcionario = Usuario.objects.create_user(
            matricula='aud_func', nome='Func Auditoria', password='senha123', is_admin=False,
        )

    def test_funcionario_nao_consulta_acoes_nem_arquivos(self):
        self.client.force_authenticate(user=self.funcionario)
        acoes = self.client.get('/api/auditoria/acoes/')
        arquivos = self.client.get('/api/auditoria/arquivos/')
        self.assertEqual(acoes.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(arquivos.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_consulta_acoes(self):
        registrar(
            ator=self.admin,
            acao='criar_usuario',
            entidade='usuario',
            entidade_id=self.funcionario.id,
            identificacao='Func Auditoria (aud_func)',
            descricao='Usuário cadastrado.',
            detalhes={'password': 'nao-gravar', 'setor': 'TI'},
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/auditoria/acoes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        item = resp.data['results'][0]
        self.assertEqual(item['acao'], 'criar_usuario')
        self.assertNotIn('password', item['detalhes'])
        self.assertEqual(item['detalhes'].get('setor'), 'TI')
        self.assertTrue(item['registro_ativo'])


class AuditoriaListagemInativosTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='aud_adm2', nome='Admin', password='senha123', is_admin=True,
        )
        self.ativo = Usuario.objects.create_user(
            matricula='aud_ativo', nome='Ativo', password='senha123',
        )
        self.inativo = Usuario.objects.create_user(
            matricula='aud_inativo', nome='Inativo', password='senha123', is_active=False,
        )
        self.veiculo = Veiculo.objects.create(
            placa='AUD1A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5, status='disponivel',
        )
        self.veiculo_inativo = Veiculo.objects.create(
            placa='AUD9Z99', modelo='Gol', marca='Volkswagen', ano=2020,
            cor='Branco', tipo_combustivel='flex', capacidade=5, status='inativo',
        )

    def test_lista_de_usuarios_oculta_inativos_por_padrao(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/usuarios/')
        matriculas = {u['matricula'] for u in resp.data['results']}
        self.assertIn('aud_ativo', matriculas)
        self.assertNotIn('aud_inativo', matriculas)

        com_inativos = self.client.get('/api/usuarios/', {'incluir_inativos': 'true'})
        matriculas = {u['matricula'] for u in com_inativos.data['results']}
        self.assertIn('aud_inativo', matriculas)

    def test_lista_de_veiculos_oculta_inativos_e_funcionario_nao_forca_exibicao(self):
        self.client.force_authenticate(user=self.admin)
        placas = {v['placa'] for v in self.client.get('/api/veiculos/').data['results']}
        self.assertIn('AUD1A23', placas)
        self.assertNotIn('AUD9Z99', placas)

        placas = {
            v['placa']
            for v in self.client.get('/api/veiculos/', {'incluir_inativos': 'true'}).data['results']
        }
        self.assertIn('AUD9Z99', placas)

        self.client.force_authenticate(user=self.ativo)
        placas = {
            v['placa']
            for v in self.client.get('/api/veiculos/', {'incluir_inativos': 'true'}).data['results']
        }
        self.assertNotIn('AUD9Z99', placas)

    def test_inativar_usuario_preserva_reserva_e_o_log(self):
        reserva = Reserva.objects.create(
            usuario=self.ativo,
            veiculo=self.veiculo,
            data_inicio=timezone.now() + timedelta(days=3),
            data_fim=timezone.now() + timedelta(days=3, hours=2),
            motivo='HISTORICO',
            status='concluida',
            modalidade='horario',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f'/api/usuarios/{self.ativo.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.ativo.refresh_from_db()
        self.assertFalse(self.ativo.is_active)
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())

        logs = self.client.get('/api/auditoria/acoes/', {'busca': 'aud_ativo'})
        self.assertEqual(logs.status_code, status.HTTP_200_OK)
        self.assertTrue(logs.data['results'])
        self.assertEqual(logs.data['results'][0]['acao'], 'inativar_usuario')
        self.assertFalse(logs.data['results'][0]['registro_ativo'])

    def test_remover_veiculo_inativa_e_mantem_a_reserva(self):
        reserva = Reserva.objects.create(
            usuario=self.ativo,
            veiculo=self.veiculo,
            data_inicio=timezone.now() + timedelta(days=4),
            data_fim=timezone.now() + timedelta(days=4, hours=2),
            motivo='HISTORICO',
            status='concluida',
            modalidade='horario',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f'/api/veiculos/{self.veiculo.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'inativo')
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                acao='inativar_veiculo', entidade_id=self.veiculo.id
            ).exists()
        )


class AuditoriaArquivoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='aud_adm3', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='aud_cnh', nome='Dono CNH', password='senha123', is_active=False,
        )

    def test_cnh_de_usuario_inativo_continua_consultavel(self):
        from usuarios.models import DocumentoCNH

        DocumentoCNH.objects.create(
            usuario=self.usuario,
            arquivo=SimpleUploadedFile('cnh.png', b'png', content_type='image/png'),
            status='pendente',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/auditoria/arquivos/', {'tipo': 'cnh', 'situacao': 'inativos'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)
        item = resp.data['results'][0]
        self.assertTrue(item['imagem'])
        self.assertFalse(item['registro_ativo'])
        self.assertTrue(item['url'])
        self.assertNotIn('password', item)
        todos = self.client.get('/api/auditoria/arquivos/')
        self.assertEqual(todos.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(todos.data['count'], 1)


class LimpezaDetalhesTests(APITestCase):
    def test_remove_segredos(self):
        limpo = limpar_detalhes({
            'password': 'abc',
            'refresh': 'tok',
            'setor': 'TI',
            'arquivo': 'cnh/x.pdf',
        })
        self.assertEqual(limpo, {'setor': 'TI'})
