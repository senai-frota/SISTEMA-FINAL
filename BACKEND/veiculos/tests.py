import shutil
import tempfile
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from auditoria.integridade import verificar_cadeia
from auditoria.models import RegistroAuditoria
from veiculos.imagens import MSG_FORMATO
from veiculos.models import FotoVeiculo, Veiculo
from veiculos.services import FipeIndisponivel, MSG_FIPE_INDISPONIVEL

Usuario = get_user_model()


class VeiculoEdicaoPermissoesTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_veic', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_veic', nome='Func', password='senha123', is_admin=False,
        )
        self.veiculo = Veiculo.objects.create(
            placa='EDT1A23', modelo='Corolla', marca='Toyota', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5,
            status='disponivel', km_atual=15000,
            data_ultima_manutencao='2026-01-10',
        )

    def test_admin_edita_veiculo_patch_parcial(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/veiculos/{self.veiculo.id}/',
            {'modelo': 'Corolla XEi'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.modelo, 'COROLLA XEI')
        self.assertEqual(self.veiculo.marca, 'Toyota')
        self.assertEqual(self.veiculo.placa, 'EDT1A23')
        self.assertEqual(self.veiculo.ano, 2024)
        self.assertEqual(self.veiculo.km_atual, 15000)
        self.assertEqual(str(self.veiculo.data_ultima_manutencao), '2026-01-10')

    def test_cadastro_rejeita_manutencao_futura(self):
        self.client.force_authenticate(user=self.admin)
        futura = (timezone.localdate() + timedelta(days=1)).isoformat()
        resp = self.client.post('/api/veiculos/', {
            'placa': 'FUT1A23', 'modelo': 'Onix', 'marca': 'Chevrolet', 'ano': 2024,
            'cor': 'Prata', 'tipo_combustivel': 'flex', 'capacidade': 5,
            'status': 'disponivel', 'data_ultima_manutencao': futura,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_ultima_manutencao', resp.data)
        self.assertFalse(Veiculo.objects.filter(placa='FUT1A23').exists())

    def test_rejeita_data_manutencao_futura(self):
        self.client.force_authenticate(user=self.admin)
        futura = timezone.localdate() + timedelta(days=1)
        resp = self.client.patch(
            f'/api/veiculos/{self.veiculo.id}/',
            {'data_ultima_manutencao': futura.isoformat()},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('data_ultima_manutencao', resp.data)
        self.veiculo.refresh_from_db()
        self.assertEqual(str(self.veiculo.data_ultima_manutencao), '2026-01-10')

    def test_aceita_data_manutencao_hoje_e_passado(self):
        self.client.force_authenticate(user=self.admin)
        hoje = timezone.localdate()
        resp = self.client.patch(
            f'/api/veiculos/{self.veiculo.id}/',
            {'data_ultima_manutencao': hoje.isoformat()},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.data_ultima_manutencao, hoje)

        passado = hoje - timedelta(days=10)
        resp = self.client.patch(
            f'/api/veiculos/{self.veiculo.id}/',
            {'data_ultima_manutencao': passado.isoformat()},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.data_ultima_manutencao, passado)

    def test_usuario_comum_nao_edita_veiculo(self):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(
            f'/api/veiculos/{self.veiculo.id}/',
            {'modelo': 'Hackeado'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.modelo, 'Corolla')


def _imagem(formato='PNG', nome=None, tamanho=(16, 12), content_type=None):
    buffer = BytesIO()
    Image.new('RGB', tamanho, (200, 30, 30)).save(buffer, format=formato)
    extensao = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp', 'GIF': 'gif'}[formato]
    return SimpleUploadedFile(
        nome or f'carro.{extensao}',
        buffer.getvalue(),
        content_type=content_type or f'image/{extensao}',
    )


class VeiculoImagemTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media = tempfile.mkdtemp(prefix='frota-imagens-')
        cls._override = override_settings(
            MEDIA_ROOT=cls._media,
            STORAGES={
                'default': {
                    'BACKEND': 'django.core.files.storage.FileSystemStorage',
                    'OPTIONS': {'location': cls._media, 'base_url': '/media/'},
                },
                'staticfiles': {
                    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
                },
            },
        )
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_img', nome='Admin Imagem', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_img', nome='Func Imagem', password='senha123',
        )
        self.veiculo = Veiculo.objects.create(
            placa='IMG1A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5, status='disponivel',
        )
        self.url = f'/api/veiculos/{self.veiculo.id}/imagem/'

    def _enviar(self, arquivo, usuario=None):
        self.client.force_authenticate(user=usuario or self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.url, {'imagem': arquivo}, format='multipart')

    def _remover(self, usuario=None):
        self.client.force_authenticate(user=usuario or self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.delete(self.url)

    def _log(self, acao):
        return RegistroAuditoria.objects.filter(acao=acao).order_by('-sequencia').first()

    def test_veiculo_sem_imagem_funciona_normalmente(self):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.get(f'/api/veiculos/{self.veiculo.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data['foto_url'])
        self.assertIsNone(resp.data['foto'])
        self.assertEqual(resp.data['fotos'], [])
        lista = self.client.get('/api/veiculos/')
        self.assertEqual(lista.status_code, status.HTTP_200_OK)

    def test_admin_adiciona_imagem(self):
        resp = self._enviar(_imagem('PNG'))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.veiculo.refresh_from_db()
        nome = self.veiculo.foto.name
        self.assertTrue(nome.startswith('veiculos/'))
        self.assertTrue(nome.endswith('.png'))
        self.assertNotIn('carro', nome)
        self.assertTrue(default_storage.exists(nome))
        self.assertTrue(resp.data['foto_url'].startswith('http://testserver/media/veiculos/'))
        self.assertTrue(resp.data['foto_url'].endswith('.png'))
        self.assertEqual(len(resp.data['fotos']), 1)
        self.assertEqual(resp.data['fotos'][0]['url'], resp.data['foto_url'])
        self.assertEqual(FotoVeiculo.objects.filter(veiculo=self.veiculo).count(), 1)

        log = self._log('adicionar_imagem_veiculo')
        self.assertIsNotNone(log)
        self.assertEqual(log.ator_id, self.admin.id)
        self.assertEqual(log.entidade, 'veiculo')
        self.assertEqual(log.entidade_id, self.veiculo.id)
        self.assertIn('IMG1A23', log.descricao)
        self.assertEqual(log.detalhes['formato'], 'PNG')
        self.assertIsNotNone(log.criado_em)
        self.assertTrue(verificar_cadeia()['integra'])

    def test_listagem_informa_imagem(self):
        self._enviar(_imagem('JPEG'))
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.get('/api/veiculos/')
        itens = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        item = next(v for v in itens if v['id'] == self.veiculo.id)
        self.assertTrue(item['foto_url'].endswith('.jpg'))
        self.assertEqual(len(item['fotos']), 1)

    def test_admin_adiciona_segunda_imagem_sem_apagar_a_antiga(self):
        self._enviar(_imagem('PNG'))
        self.veiculo.refresh_from_db()
        antigo = self.veiculo.foto.name

        resp = self._enviar(_imagem('WEBP'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.fotos.count(), 2)
        self.assertEqual(self.veiculo.foto.name, antigo)
        self.assertTrue(default_storage.exists(antigo))
        self.assertTrue(resp.data['foto_url'].endswith('.png'))
        self.assertEqual(len(resp.data['fotos']), 2)
        urls = [foto['url'] for foto in resp.data['fotos']]
        self.assertTrue(any(url.endswith('.webp') for url in urls))
        self.assertTrue(any(url.endswith('.png') for url in urls))
        self.assertEqual(
            RegistroAuditoria.objects.filter(acao='adicionar_imagem_veiculo').count(), 2,
        )

    def test_admin_envia_varias_imagens_de_uma_vez(self):
        self.client.force_authenticate(user=self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                self.url,
                {'imagens': [_imagem('PNG'), _imagem('JPEG')]},
                format='multipart',
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(len(resp.data['fotos']), 2)
        self.assertEqual(FotoVeiculo.objects.filter(veiculo=self.veiculo).count(), 2)

    def test_admin_remove_foto_especifica_mantem_as_demais(self):
        self._enviar(_imagem('PNG'))
        self._enviar(_imagem('JPEG'))
        fotos = list(FotoVeiculo.objects.filter(veiculo=self.veiculo).order_by('ordem', 'id'))
        self.assertEqual(len(fotos), 2)
        primeira, segunda = fotos
        self.client.force_authenticate(user=self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.delete(f'{self.url}?foto={segunda.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(len(resp.data['fotos']), 1)
        self.assertEqual(resp.data['fotos'][0]['id'], primeira.id)
        self.assertFalse(default_storage.exists(segunda.arquivo.name))
        self.assertTrue(default_storage.exists(primeira.arquivo.name))

    def test_admin_remove_imagem_e_apaga_arquivo(self):
        self._enviar(_imagem('PNG'))
        self.veiculo.refresh_from_db()
        antigo = self.veiculo.foto.name

        resp = self._remover()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data['foto_url'])
        self.veiculo.refresh_from_db()
        self.assertFalse(self.veiculo.foto)
        self.assertFalse(default_storage.exists(antigo))

        log = self._log('remover_imagem_veiculo')
        self.assertIsNotNone(log)
        self.assertEqual(log.ator_id, self.admin.id)
        self.assertEqual(log.entidade_id, self.veiculo.id)
        self.assertTrue(verificar_cadeia()['integra'])

    def test_remover_sem_imagem_retorna_404(self):
        resp = self._remover()
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(RegistroAuditoria.objects.filter(acao='remover_imagem_veiculo').exists())

    def test_usuario_comum_nao_altera_imagem(self):
        self._enviar(_imagem('PNG'))
        self.veiculo.refresh_from_db()
        atual = self.veiculo.foto.name

        resp = self._enviar(_imagem('JPEG'), usuario=self.usuario)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        resp = self._remover(usuario=self.usuario)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.foto.name, atual)
        self.assertTrue(default_storage.exists(atual))
        self.assertEqual(RegistroAuditoria.objects.filter(acao__contains='imagem_veiculo').count(), 1)

    def test_anonimo_nao_altera_imagem(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(self.url, {'imagem': _imagem('PNG')}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_generico_nao_altera_imagem(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/veiculos/{self.veiculo.id}/', {'foto': _imagem('PNG')}, format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.veiculo.refresh_from_db()
        self.assertFalse(self.veiculo.foto)

    def test_arquivos_invalidos_sao_rejeitados(self):
        casos = {
            'texto com extensão .png': SimpleUploadedFile(
                'falso.png', b'isto nao e uma imagem', content_type='image/png',
            ),
            'gif renomeado': _imagem('GIF', nome='animacao.png', content_type='image/png'),
            'png truncado': SimpleUploadedFile(
                'quebrado.png', _imagem('PNG', tamanho=(64, 64)).read()[:60],
                content_type='image/png',
            ),
            'arquivo vazio': SimpleUploadedFile('vazio.jpg', b'', content_type='image/jpeg'),
        }
        for descricao, arquivo in casos.items():
            resp = self._enviar(arquivo)
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, descricao)
            self.assertIn('imagem', resp.data, descricao)

        resp = self._enviar(SimpleUploadedFile('falso.png', b'x' * 10, content_type='image/png'))
        self.assertEqual(resp.data['imagem'], [MSG_FORMATO])

        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self.url, {}, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        self.veiculo.refresh_from_db()
        self.assertFalse(self.veiculo.foto)
        self.assertFalse(RegistroAuditoria.objects.filter(acao__contains='imagem_veiculo').exists())

    @override_settings(VEICULO_IMAGEM_TAMANHO_MAXIMO_MB=1)
    def test_arquivo_acima_do_limite_e_rejeitado(self):
        grande = SimpleUploadedFile(
            'grande.png', b'\x89PNG' + b'0' * (1024 * 1024 + 1), content_type='image/png',
        )
        resp = self._enviar(grande)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data['imagem'], ['A imagem deve ter no máximo 1 MB.'])
        self.veiculo.refresh_from_db()
        self.assertFalse(self.veiculo.foto)

    def test_veiculo_inexistente_retorna_404(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            '/api/veiculos/999999/imagem/', {'imagem': _imagem('PNG')}, format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_delete_mantem_imagem(self):
        self._enviar(_imagem('PNG'))
        self.veiculo.refresh_from_db()
        nome = self.veiculo.foto.name
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f'/api/veiculos/{self.veiculo.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'inativo')
        self.assertEqual(self.veiculo.foto.name, nome)
        self.assertTrue(default_storage.exists(nome))


class FipeConsultaTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            matricula='func_fipe', nome='Func Fipe', password='senha123', is_admin=False,
        )

    @patch('veiculos.views.buscar_marcas', side_effect=FipeIndisponivel(MSG_FIPE_INDISPONIVEL))
    def test_marcas_quando_fipe_fora_retorna_503(self, _mock):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.get('/api/veiculos/marcas/')
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('FIPE', resp.data['detail'])
