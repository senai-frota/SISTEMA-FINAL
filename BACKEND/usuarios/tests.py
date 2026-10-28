from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from reservas.models import Reserva
from termos.models import TermoResponsabilidade, VALIDADE_DIAS
from termos.services_conta import sincronizar_status_conta
from usuarios.models import DocumentoCNH, CNH_DIAS_ALERTA_VENCIMENTO, resumo_cnh_usuario
from veiculos.models import Veiculo
from vistorias.models import Vistoria

Usuario = get_user_model()


def _pdf(name='doc.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake', content_type='application/pdf')


def _make_cnh(usuario, admin=None, dias_validade=365):
    return DocumentoCNH.objects.create(
        usuario=usuario,
        data_validade=timezone.localdate() + timedelta(days=dias_validade),
        arquivo=_pdf('cnh.pdf'),
        status='aprovado',
        admin_aprovador=admin,
        data_decisao=timezone.now(),
    )


def _make_termo(usuario, *, status_doc='aprovado', admin=None, data_validade=None, cpf_suffix='9'):
    validade = data_validade
    if status_doc == 'aprovado' and validade is None:
        validade = timezone.localdate() + timedelta(days=VALIDADE_DIAS)
    return TermoResponsabilidade.objects.create(
        usuario=usuario,
        entidade='SENAI',
        cpf=f'1111111111{cpf_suffix}'[-11:],
        cnh=f'2222222222{cpf_suffix}'[-11:],
        data_solicitacao=timezone.localdate(),
        arquivo_pdf=_pdf('termo.pdf'),
        status=status_doc,
        data_validade=validade,
        admin_aprovador=admin if status_doc != 'pendente' else None,
        data_decisao=timezone.now() if status_doc != 'pendente' else None,
    )


class UsuarioListagemPermissoesTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin01', nome='Admin Teste', password='senha123', is_admin=True,
        )
        self.funcionario = Usuario.objects.create_user(
            matricula='func01', nome='Funcionario Teste', password='senha123', is_admin=False,
        )
        self.url = '/api/usuarios/'

    def test_funcionario_nao_lista_usuarios(self):
        self.client.force_authenticate(user=self.funcionario)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_lista_usuarios(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resultados = response.data.get('results', response.data)
        matriculas = {u['matricula'] for u in resultados}
        self.assertIn('admin01', matriculas)
        self.assertIn('func01', matriculas)

    def test_funcionario_ainda_acessa_proprio_perfil(self):
        self.client.force_authenticate(user=self.funcionario)
        response = self.client.get('/api/usuarios/perfil/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['matricula'], 'func01')
        self.assertIn('cnh', response.data)
        self.assertIn('termo', response.data)

    def test_funcionario_nao_altera_proprio_is_active(self):
        self.client.force_authenticate(user=self.funcionario)
        resp = self.client.patch(
            f'/api/usuarios/{self.funcionario.id}/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.is_active)


class PendenciasAdminTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin01', nome='Admin', password='senha123', is_admin=True,
        )
        novo = lambda m, **kw: Usuario.objects.create_user(
            matricula=m, nome=m, password='senha123', is_admin=False, **kw,
        )
        self.ok = novo('ok')
        _make_cnh(self.ok)
        _make_termo(self.ok, cpf_suffix='1')
        DocumentoCNH.objects.create(usuario=self.ok, arquivo=_pdf(), status='pendente')

        self.vencida = novo('vencida')
        _make_cnh(self.vencida, dias_validade=-5)
        _make_termo(self.vencida, status_doc='pendente', cpf_suffix='2')

        self.proxima = novo('proxima')
        _make_cnh(self.proxima, dias_validade=10)
        _make_termo(
            self.proxima, cpf_suffix='3',
            data_validade=timezone.localdate() - timedelta(days=1),
        )

        self.sem_docs = novo('semdocs')
        self.inativo = novo('inativo', is_active=False)

    def _ids(self, response):
        return {u['matricula'] for u in response.data['results']}

    def test_funcionario_nao_acessa_pendencias(self):
        self.client.force_authenticate(user=self.ok)
        resp = self.client.get('/api/usuarios/pendencias/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_contadores_ignoram_admin_e_nao_alteram_contas(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/usuarios/pendencias/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['cnh'], {
            'pendentes_analise': 1,
            'vencidas': 1,
            'proximas_vencimento': 1,
            'sem_cnh_valida': 1,
            'dias_alerta': CNH_DIAS_ALERTA_VENCIMENTO,
        })
        self.assertEqual(resp.data['termo'], {
            'pendentes_analise': 1,
            'vencidos': 1,
            'sem_termo_valido': 2,
        })
        self.assertEqual(resp.data['contas_inativas'], 1)
        self.proxima.refresh_from_db()
        self.assertTrue(self.proxima.is_active)

    def test_filtros_da_listagem_aceitam_varias_situacoes(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(
            '/api/usuarios/', {'cnh_situacao': 'vencida,proxima_vencimento'},
        )
        self.assertEqual(self._ids(resp), {'vencida', 'proxima'})

        resp = self.client.get(
            '/api/usuarios/',
            {'termo_situacao': 'sem_termo,rejeitado', 'incluir_inativos': 'true'},
        )
        self.assertEqual(self._ids(resp), {'semdocs', 'inativo'})

        resp = self.client.get(
            '/api/usuarios/', {'termo_situacao': 'vencido', 'incluir_inativos': 'true'},
        )
        self.assertEqual(self._ids(resp), {'proxima'})


class RemocaoUsuarioTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_rm', nome='Admin', password='senha123', is_admin=True,
        )
        self.alvo = Usuario.objects.create_user(
            matricula='func_rm', nome='Func Remover', password='senha123', is_admin=False,
        )
        self.outro = Usuario.objects.create_user(
            matricula='func_rm2', nome='Outro', password='senha123', is_admin=False,
        )
        self.veiculo = Veiculo.objects.create(
            placa='RM01A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5,
            status='disponivel', km_atual=1000,
        )
        self.reserva = Reserva.objects.create(
            usuario=self.alvo,
            veiculo=self.veiculo,
            data_inicio=timezone.now() + timedelta(days=2),
            data_fim=timezone.now() + timedelta(days=2, hours=2),
            motivo='HISTORICO',
            status='concluida',
            modalidade='horario',
        )

    def test_admin_remove_usuario_por_exclusao_logica(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f'/api/usuarios/{self.alvo.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.alvo.refresh_from_db()
        self.assertFalse(self.alvo.is_active)
        self.assertTrue(Usuario.objects.filter(pk=self.alvo.pk).exists())
        self.assertTrue(Reserva.objects.filter(pk=self.reserva.pk).exists())

    def test_funcionario_nao_remove_usuario(self):
        self.client.force_authenticate(user=self.outro)
        resp = self.client.delete(f'/api/usuarios/{self.alvo.id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.alvo.refresh_from_db()
        self.assertTrue(self.alvo.is_active)

    def test_admin_nao_remove_a_propria_conta(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f'/api/usuarios/{self.admin.id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class CNHPermissoesTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_cnh2', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_cnh2', nome='Func', password='senha123', is_admin=False,
        )
        self.outro = Usuario.objects.create_user(
            matricula='func_cnh3', nome='Outro', password='senha123', is_admin=False,
        )

    def test_usuario_nao_aprova_propria_cnh(self):
        doc = DocumentoCNH.objects.create(
            usuario=self.usuario, arquivo=_pdf(), status='pendente',
        )
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(
            f'/api/usuarios/cnh/{doc.id}/decisao/',
            {
                'status': 'aprovado',
                'data_validade': (timezone.localdate() + timedelta(days=100)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_nao_aprova_cnh_de_outro(self):
        doc = DocumentoCNH.objects.create(
            usuario=self.outro, arquivo=_pdf(), status='pendente',
        )
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(
            f'/api/usuarios/cnh/{doc.id}/decisao/',
            {
                'status': 'aprovado',
                'data_validade': (timezone.localdate() + timedelta(days=100)).isoformat(),
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_nao_altera_dados_admin_de_outro(self):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(
            f'/api/usuarios/{self.outro.id}/',
            {'nome': 'Hackeado', 'is_active': False},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_alerta_vencimento_30_dias(self):
        DocumentoCNH.objects.create(
            usuario=self.usuario,
            arquivo=_pdf(),
            status='aprovado',
            data_validade=timezone.localdate() + timedelta(days=CNH_DIAS_ALERTA_VENCIMENTO),
            admin_aprovador=self.admin,
            data_decisao=timezone.now(),
        )
        resumo = resumo_cnh_usuario(self.usuario)
        self.assertTrue(resumo['proxima_do_vencimento'])
        self.assertEqual(resumo['situacao'], 'proxima_vencimento')
        self.assertTrue(resumo['pode_reservar'])

    def test_upload_cnh_persiste_e_pode_ser_lido(self):
        from django.core.files.storage import default_storage

        self.client.force_authenticate(user=self.usuario)
        conteudo = b'%PDF-1.4 conteudo-cnh-teste'
        arquivo = SimpleUploadedFile(
            'minha_cnh.pdf', conteudo, content_type='application/pdf'
        )
        resp = self.client.post(
            '/api/usuarios/cnh/',
            {'arquivo': arquivo},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data.get('arquivo_url'))
        doc = DocumentoCNH.objects.get(pk=resp.data['id'])
        self.assertTrue(default_storage.exists(doc.arquivo.name))
        with default_storage.open(doc.arquivo.name, 'rb') as fh:
            self.assertEqual(fh.read(), conteudo)
        media = self.client.get(doc.arquivo.url)
        self.assertEqual(media.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(media.streaming_content), conteudo)


class QuilometragemTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_km', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_km', nome='Func', password='senha123', is_admin=False,
        )
        _make_cnh(self.usuario, admin=self.admin)
        _make_termo(self.usuario, admin=self.admin, cpf_suffix='8')
        self.veiculo = Veiculo.objects.create(
            placa='KM01A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5,
            status='disponivel', km_atual=48520,
        )
        base = timezone.localtime(timezone.now()).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        self.reserva = Reserva.objects.create(
            usuario=self.usuario,
            veiculo=self.veiculo,
            data_inicio=base,
            data_fim=base + timedelta(hours=10),
            motivo='Teste KM',
            status='aprovada',
            modalidade='horario',
        )
        self.momento_ok = base.replace(hour=10, minute=0)
        self.client.force_authenticate(user=self.usuario)

    def _foto(self, name='foto.png'):
        png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
            b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return SimpleUploadedFile(name, png, content_type='image/png')

    def _mobile(self):
        return {
            'HTTP_X_CLIENT_FORM_FACTOR': 'mobile',
            'HTTP_USER_AGENT': (
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
                'AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1'
            ),
        }

    def _registrar_payload(self, reserva_id, tipo, **extra):
        from vistorias.dispositivo import FOTOS_OBRIGATORIAS
        data = {
            'reserva': reserva_id,
            'tipo': tipo,
            'unidade': 'gama',
            'fotos': [self._foto(f'{a}.png') for a in FOTOS_OBRIGATORIAS],
            'descricoes': list(FOTOS_OBRIGATORIAS),
        }
        data.update(extra)
        return data

    def test_checkin_usa_km_atual(self):
        resp = self.client.get('/api/vistorias/ultima-quilometragem/', {
            'veiculo': self.veiculo.id,
            'reserva': self.reserva.id,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['quilometragem'], 48520)

        with patch('vistorias.regras.agora_local', return_value=self.momento_ok):
            resp = self.client.post(
                '/api/vistorias/registrar/',
                self._registrar_payload(self.reserva.id, 'checkin'),
                format='multipart',
                **self._mobile(),
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['quilometragem'], 48520)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'em_andamento')
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'em_uso')

    def test_checkout_km_menor_rejeitado_e_valido_atualiza(self):
        Vistoria.objects.create(
            reserva=self.reserva,
            tipo='checkin',
            unidade='gama',
            quilometragem=48520,
            realizada_por=self.usuario,
        )
        self.reserva.status = 'em_andamento'
        self.reserva.save()
        self.veiculo.status = 'em_uso'
        self.veiculo.save()

        with patch('vistorias.regras.agora_local', return_value=self.momento_ok):
            resp = self.client.post(
                '/api/vistorias/registrar/',
                self._registrar_payload(self.reserva.id, 'checkout', quilometragem=48000),
                format='multipart',
                **self._mobile(),
            )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        with patch('vistorias.regras.agora_local', return_value=self.momento_ok):
            resp = self.client.post(
                '/api/vistorias/registrar/',
                self._registrar_payload(self.reserva.id, 'checkout', quilometragem=48687),
                format='multipart',
                **self._mobile(),
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 48687)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'concluida')
        self.assertEqual(self.veiculo.status, 'disponivel')

    def test_proximo_checkin_usa_novo_km(self):
        self.veiculo.km_atual = 48687
        self.veiculo.status = 'disponivel'
        self.veiculo.save()
        inicio = timezone.now() + timedelta(days=3)
        reserva2 = Reserva.objects.create(
            usuario=self.usuario,
            veiculo=self.veiculo,
            data_inicio=inicio,
            data_fim=inicio + timedelta(hours=2),
            motivo='Segundo uso',
            status='aprovada',
            modalidade='horario',
        )
        self.veiculo.status = 'em_uso'
        self.veiculo.save()
        resp = self.client.get('/api/vistorias/ultima-quilometragem/', {
            'veiculo': self.veiculo.id,
            'reserva': reserva2.id,
        })
        self.assertEqual(resp.data['quilometragem'], 48687)


class ContaInativaLoginTests(APITestCase):
    def test_usuario_inativo_consegue_login(self):
        usuario = Usuario.objects.create_user(
            matricula='inativo01', nome='Inativo', password='senha123', is_admin=False,
        )
        usuario.is_active = False
        usuario.save()
        resp = self.client.post('/api/usuarios/login/', {
            'matricula': 'inativo01',
            'password': 'senha123',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)


class PrimeiroAcessoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_pa', nome='Admin', password='senhaAdmin1', is_admin=True,
        )
        self.existente = Usuario.objects.create_user(
            matricula='exist_pa', nome='Existente', password='senhaExist1', is_admin=False,
        )

    def test_admin_cria_usuario_sem_senha(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/usuarios/', {
            'matricula': 'novo_pa',
            'nome': 'Novo Usuario',
            'email': 'novo@senai.br',
            'is_admin': False,
            'is_active': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        novo = Usuario.objects.get(matricula='novo_pa')
        self.assertTrue(novo.precisa_definir_senha)
        self.assertFalse(novo.has_usable_password())

    def test_usuario_existente_com_senha_continua_funcionando(self):
        self.assertFalse(self.existente.precisa_definir_senha)
        resp = self.client.post('/api/usuarios/login/', {
            'matricula': 'exist_pa',
            'password': 'senhaExist1',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['precisa_definir_senha'])

    def test_primeiro_acesso_login_sem_senha_e_definir(self):
        novo = Usuario.objects.create_user(
            matricula='primeiro_pa', nome='Primeiro', password=None, is_admin=False,
        )
        self.assertTrue(novo.precisa_definir_senha)

        login = self.client.post('/api/usuarios/login/', {
            'matricula': 'primeiro_pa',
            'password': '',
        }, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertTrue(login.data['precisa_definir_senha'])
        token = login.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        bloqueado = self.client.get('/api/veiculos/')
        self.assertEqual(bloqueado.status_code, status.HTTP_403_FORBIDDEN)

        perfil = self.client.get('/api/usuarios/perfil/')
        self.assertEqual(perfil.status_code, status.HTTP_200_OK)

        falha_confirm = self.client.post('/api/usuarios/definir-senha/', {
            'password': 'NovaSenha1',
            'password_confirm': 'OutraSenha1',
        }, format='json')
        self.assertEqual(falha_confirm.status_code, status.HTTP_400_BAD_REQUEST)

        ok = self.client.post('/api/usuarios/definir-senha/', {
            'password': 'NovaSenha1',
            'password_confirm': 'NovaSenha1',
        }, format='json')
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        novo.refresh_from_db()
        self.assertFalse(novo.precisa_definir_senha)
        self.assertTrue(novo.has_usable_password())
        self.assertTrue(novo.check_password('NovaSenha1'))
        self.assertNotEqual(novo.password, 'NovaSenha1')

        liberado = self.client.get('/api/veiculos/')
        self.assertEqual(liberado.status_code, status.HTTP_200_OK)

        self.client.credentials()
        relogin = self.client.post('/api/usuarios/login/', {
            'matricula': 'primeiro_pa',
            'password': 'NovaSenha1',
        }, format='json')
        self.assertEqual(relogin.status_code, status.HTTP_200_OK)
        self.assertFalse(relogin.data['precisa_definir_senha'])

    def test_admin_e_superuser_existentes_continuam(self):
        resp = self.client.post('/api/usuarios/login/', {
            'matricula': 'admin_pa',
            'password': 'senhaAdmin1',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['is_admin'])

        su = Usuario.objects.create_superuser(
            matricula='super_pa', nome='Super', password='senhaSuper1',
        )
        self.assertFalse(su.precisa_definir_senha)
        resp2 = self.client.post('/api/usuarios/login/', {
            'matricula': 'super_pa',
            'password': 'senhaSuper1',
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)


class CadastroUsuarioValidacaoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_cad', nome='Admin Cadastro', password='senhaAdmin1', is_admin=True,
        )
        self.existente = Usuario.objects.create_user(
            matricula='exist_cad', nome='Já Existe', password='senhaExist1', is_admin=False,
        )

    def test_matricula_duplicada_retorna_mensagem_clara(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/usuarios/', {
            'matricula': 'exist_cad',
            'nome': 'Outro Nome',
            'is_admin': False,
            'is_active': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('matricula', resp.data)
        self.assertIn('já está cadastrada', str(resp.data['matricula'][0]).lower())


class RedefinirSenhaAdminTests(APITestCase):
    SENHA_ANTIGA = 'SenhaAntiga9'
    SENHA_NOVA = 'SenhaNovaForte9'

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_rs', nome='Admin Reset', password='senhaAdmin1', is_admin=True,
        )
        self.funcionario = Usuario.objects.create_user(
            matricula='func_rs', nome='Func Reset', password=self.SENHA_ANTIGA, is_admin=False,
        )
        self.url = f'/api/usuarios/{self.funcionario.id}/redefinir-senha/'

    def _payload(self, senha=None, confirm=None):
        valor = senha or self.SENHA_NOVA
        return {'password': valor, 'password_confirm': confirm if confirm is not None else valor}

    def test_admin_redefine_senha_com_sucesso(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get('detail'), 'Senha redefinida com sucesso.')
        self.assertNotIn('password', resp.data)
        self.assertNotIn(self.SENHA_NOVA, str(resp.data))

        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.check_password(self.SENHA_NOVA))
        self.assertFalse(self.funcionario.check_password(self.SENHA_ANTIGA))
        self.assertFalse(self.funcionario.precisa_definir_senha)
        self.assertEqual(self.funcionario.matricula, 'func_rs')
        self.assertEqual(self.funcionario.nome, 'Func Reset')
        self.assertFalse(self.funcionario.is_admin)
        self.assertTrue(self.funcionario.is_active)

        self.client.credentials()
        antigo = self.client.post('/api/usuarios/login/', {
            'matricula': 'func_rs',
            'password': self.SENHA_ANTIGA,
        }, format='json')
        self.assertIn(antigo.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED))

        novo = self.client.post('/api/usuarios/login/', {
            'matricula': 'func_rs',
            'password': self.SENHA_NOVA,
        }, format='json')
        self.assertEqual(novo.status_code, status.HTTP_200_OK)

    def test_confirmacao_divergente_e_recusada(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self.url, self._payload(confirm='OutraSenha9'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', resp.data)
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.check_password(self.SENHA_ANTIGA))

    def test_senha_incompativel_com_validadores_e_recusada(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self.url, self._payload(senha='123', confirm='123'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.check_password(self.SENHA_ANTIGA))

        numerica = self.client.post(self.url, self._payload(senha='12345678', confirm='12345678'), format='json')
        self.assertEqual(numerica.status_code, status.HTTP_400_BAD_REQUEST)

    def test_usuario_inexistente(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/usuarios/999999/redefinir-senha/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_nao_autenticado_nao_redefine(self):
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.check_password(self.SENHA_ANTIGA))

    def test_funcionario_nao_redefine_senha_de_terceiro(self):
        outro = Usuario.objects.create_user(
            matricula='func_rs2', nome='Outro Func', password='SenhaOutro9', is_admin=False,
        )
        self.client.force_authenticate(user=self.funcionario)
        resp = self.client.post(
            f'/api/usuarios/{outro.id}/redefinir-senha/',
            self._payload(),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        outro.refresh_from_db()
        self.assertTrue(outro.check_password('SenhaOutro9'))
        self.assertFalse(outro.is_admin)

    def test_auditoria_nao_registra_senha(self):
        from auditoria.models import RegistroAuditoria

        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        registro = RegistroAuditoria.objects.filter(
            acao='definir_senha', entidade_id=self.funcionario.id,
        ).latest('criado_em')
        dump = f'{registro.descricao} {registro.detalhes} {registro.identificacao}'
        self.assertNotIn(self.SENHA_NOVA, dump)
        self.assertNotIn(self.SENHA_ANTIGA, dump)
