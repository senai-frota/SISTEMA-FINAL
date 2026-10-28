from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from reservas.models import Reserva
from usuarios.models import DocumentoCNH
from termos.models import TermoResponsabilidade, VALIDADE_DIAS
from veiculos.models import Veiculo
from vistorias.dispositivo import FOTOS_OBRIGATORIAS, MSG_SOMENTE_MOBILE
from vistorias.models import Vistoria
from vistorias.regras import (
    MSG_FORA_JANELA_OPERACIONAL,
    MSG_CHECKIN_ANTES,
    MSG_CHECKIN_DEPOIS,
    MSG_CHECKOUT_ANTES,
    MSG_CHECKOUT_DEPOIS,
    TOLERANCIA_RESERVA_MINUTOS,
    janela_reserva_com_tolerancia,
    validar_checkin_horario_reserva,
    validar_checkout_horario_reserva,
)

Usuario = get_user_model()

MOBILE_UA = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
)
DESKTOP_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def _pdf(name='doc.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake', content_type='application/pdf')


def _foto(name='foto.png'):
    png = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
        b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return SimpleUploadedFile(name, png, content_type='image/png')


def _payload_registrar(reserva_id, tipo, **extra):
    data = {
        'reserva': reserva_id,
        'tipo': tipo,
        'unidade': extra.pop('unidade', 'gama'),
        'fotos': [_foto(f'{angulo}.png') for angulo in FOTOS_OBRIGATORIAS],
        'descricoes': list(FOTOS_OBRIGATORIAS),
        'observacoes_fotos': [''] * len(FOTOS_OBRIGATORIAS),
    }
    data.update(extra)
    return data


def _mobile_kw():
    return {
        'HTTP_X_CLIENT_FORM_FACTOR': 'mobile',
        'HTTP_USER_AGENT': MOBILE_UA,
    }


def _desktop_kw():
    return {
        'HTTP_X_CLIENT_FORM_FACTOR': 'desktop',
        'HTTP_USER_AGENT': DESKTOP_UA,
        'HTTP_SEC_CH_UA_MOBILE': '?0',
    }


class StatusVeiculoAprovacaoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='adm_st', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_st', nome='Func', password='senha123', is_admin=False,
        )
        DocumentoCNH.objects.create(
            usuario=self.usuario, arquivo=_pdf(), status='aprovado',
            data_validade=timezone.localdate() + timedelta(days=200),
            admin_aprovador=self.admin, data_decisao=timezone.now(),
        )
        TermoResponsabilidade.objects.create(
            usuario=self.usuario, entidade='SENAI', cpf='55555555551',
            cnh='12345678900', data_solicitacao=timezone.localdate(),
            arquivo_pdf=_pdf(), status='aprovado',
            data_validade=timezone.localdate() + timedelta(days=VALIDADE_DIAS),
            admin_aprovador=self.admin, data_decisao=timezone.now(),
        )
        self.veiculo = Veiculo.objects.create(
            placa='ST01A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5,
            status='disponivel', km_atual=10000,
        )
        inicio = timezone.now() + timedelta(days=2)
        self.reserva = Reserva.objects.create(
            usuario=self.usuario, veiculo=self.veiculo,
            data_inicio=inicio, data_fim=inicio + timedelta(hours=2),
            motivo='Teste', status='pendente', modalidade='horario',
        )

    def test_aprovar_nao_coloca_veiculo_em_uso(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'aprovada'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.reserva.refresh_from_db()
        self.veiculo.refresh_from_db()
        self.assertEqual(self.reserva.status, 'aprovada')
        self.assertEqual(self.veiculo.status, 'disponivel')

    def test_rejeitar_nao_coloca_veiculo_em_uso(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'negada', 'observacao_admin': 'Veículo reservado para outra demanda.'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'disponivel')

    def test_cancelar_aprovada_nao_coloca_em_uso(self):
        self.reserva.status = 'aprovada'
        self.reserva.save()
        self.client.force_authenticate(user=self.usuario)
        self.client.delete(f'/api/reservas/{self.reserva.id}/')
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'disponivel')


class CheckinCheckoutRegrasTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='adm_ck', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_ck', nome='Func', password='senha123', is_admin=False,
        )
        self.outro = Usuario.objects.create_user(
            matricula='outro_ck', nome='Outro', password='senha123', is_admin=False,
        )
        DocumentoCNH.objects.create(
            usuario=self.usuario, arquivo=_pdf(), status='aprovado',
            data_validade=timezone.localdate() + timedelta(days=200),
            admin_aprovador=self.admin, data_decisao=timezone.now(),
        )
        self.veiculo = Veiculo.objects.create(
            placa='CK01A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5,
            status='disponivel', km_atual=50000,
        )
        base = timezone.localtime(timezone.now()).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        self.reserva = Reserva.objects.create(
            usuario=self.usuario, veiculo=self.veiculo,
            data_inicio=base, data_fim=base + timedelta(hours=2),
            motivo='Uso', status='aprovada', modalidade='horario',
        )
        self.client.force_authenticate(user=self.usuario)

    def _momento(self, hora, minuto=0):
        local = timezone.localtime(self.reserva.data_inicio).replace(
            hour=hora, minute=minuto, second=0, microsecond=0,
        )
        return local

    def _post(self, data, momento=None, headers=None):
        momento = momento or self._momento(10, 30)
        kw = dict(_mobile_kw())
        if headers:
            kw.update(headers)
        with patch('vistorias.regras.agora_local', return_value=momento):
            return self.client.post(
                '/api/vistorias/registrar/', data, format='multipart', **kw
            )

    def test_checkin_valido_coloca_em_uso(self):
        resp = self._post(_payload_registrar(self.reserva.id, 'checkin'))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['quilometragem'], 50000)
        self.reserva.refresh_from_db()
        self.veiculo.refresh_from_db()
        self.assertEqual(self.reserva.status, 'em_andamento')
        self.assertEqual(self.veiculo.status, 'em_uso')
        self.assertEqual(len(resp.data['fotos']), 5)

    def test_checkin_desktop_bloqueado(self):
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkin'),
            headers=_desktop_kw(),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(MSG_SOMENTE_MOBILE, str(resp.data))
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'disponivel')

    def test_checkin_sem_todas_fotos_bloqueado(self):
        data = _payload_registrar(self.reserva.id, 'checkin')
        data['fotos'] = [_foto('so_uma.png')]
        data['descricoes'] = ['frente']
        resp = self._post(data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkin_antes_horario_bloqueado(self):
        # Mais de 30 min antes do início (10:00) → bloqueado
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkin'),
            momento=self._momento(9, 29),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'disponivel')

    def test_checkin_exatamente_30min_antes_permitido(self):
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkin'),
            momento=self._momento(9, 30),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_checkin_depois_horario_bloqueado(self):
        # Mais de 30 min após o fim (12:00) → bloqueado
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkin'),
            momento=self._momento(12, 31),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkin_exatamente_30min_depois_permitido(self):
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkin'),
            momento=self._momento(12, 30),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_checkin_fora_janela_operacional_bloqueado(self):
        momento = self._momento(5, 30)
        self.reserva.data_inicio = momento - timedelta(hours=1)
        self.reserva.data_fim = momento + timedelta(hours=2)
        self.reserva.save()
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkin'),
            momento=momento,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(MSG_FORA_JANELA_OPERACIONAL, str(resp.data))

    def test_checkin_nao_aprovada_bloqueado(self):
        self.reserva.status = 'pendente'
        self.reserva.save()
        resp = self._post(_payload_registrar(self.reserva.id, 'checkin'))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkin_outro_usuario_bloqueado(self):
        self.client.force_authenticate(user=self.outro)
        resp = self._post(_payload_registrar(self.reserva.id, 'checkin'))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_valido_devolve_disponivel_e_atualiza_km(self):
        self._post(_payload_registrar(self.reserva.id, 'checkin'))
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkout', quilometragem=50120),
            momento=self._momento(11, 0),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.veiculo.refresh_from_db()
        self.reserva.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'disponivel')
        self.assertEqual(self.veiculo.km_atual, 50120)
        self.assertEqual(self.reserva.status, 'concluida')

    def test_checkout_sem_checkin_bloqueado(self):
        self.reserva.status = 'em_andamento'
        self.reserva.save()
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkout', quilometragem=50100),
            momento=self._momento(11, 0),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_fora_janela_operacional_permitido(self):
        Vistoria.objects.create(
            reserva=self.reserva, tipo='checkin', unidade='gama',
            quilometragem=50000, realizada_por=self.usuario,
        )
        self.reserva.status = 'em_andamento'
        self.reserva.unidade_checkin = 'gama'
        self.reserva.save()
        self.veiculo.status = 'em_uso'
        self.veiculo.save()
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkout', quilometragem=50100),
            momento=self._momento(22, 30),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'concluida')
        self.assertIsNotNone(self.reserva.data_devolucao_real)

    def test_checkout_km_menor_bloqueado(self):
        Vistoria.objects.create(
            reserva=self.reserva, tipo='checkin', unidade='gama',
            quilometragem=50000, realizada_por=self.usuario,
        )
        self.reserva.status = 'em_andamento'
        self.reserva.save()
        self.veiculo.status = 'em_uso'
        self.veiculo.save()
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkout', quilometragem=49900),
            momento=self._momento(11, 0),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_geo_opcional_aceita_sem_bloquear(self):
        data = _payload_registrar(
            self.reserva.id, 'checkin',
            latitude='-15.780100',
            longitude='-47.929200',
            precisao_metros='12.5',
        )
        resp = self._post(data)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(resp.data.get('latitude'))

    def test_checkout_exatamente_30min_depois_permitido(self):
        self._post(_payload_registrar(self.reserva.id, 'checkin'))
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkout', quilometragem=50120),
            momento=self._momento(12, 30),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_checkout_mais_de_30min_depois_permitido(self):
        self._post(_payload_registrar(self.reserva.id, 'checkin'))
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkout', quilometragem=50120),
            momento=self._momento(12, 31),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'concluida')
        self.assertIsNotNone(self.reserva.data_devolucao_real)

    def test_checkout_unidade_diferente_bloqueado(self):
        self._post(_payload_registrar(self.reserva.id, 'checkin', unidade='gama'))
        resp = self._post(
            _payload_registrar(self.reserva.id, 'checkout', unidade='sig', quilometragem=50120),
            momento=self._momento(11, 0),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mesma unidade', str(resp.data).lower())

    def test_retry_apos_checkin_concluido_nao_duplica(self):
        from auditoria.models import RegistroAuditoria
        from vistorias.models import FotoVistoria

        primeiro = self._post(_payload_registrar(self.reserva.id, 'checkin'))
        self.assertEqual(primeiro.status_code, status.HTTP_201_CREATED)
        segundo = self._post(_payload_registrar(self.reserva.id, 'checkin'))
        self.assertEqual(segundo.status_code, status.HTTP_200_OK)
        self.assertTrue(segundo.data.get('idempotente'))
        self.assertEqual(
            Vistoria.objects.filter(reserva=self.reserva, tipo='checkin').count(), 1,
        )
        self.assertEqual(
            FotoVistoria.objects.filter(vistoria_id=primeiro.data['id']).count(), 5,
        )
        self.assertEqual(
            RegistroAuditoria.objects.filter(acao='registrar_vistoria').count(), 1,
        )
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'em_andamento')
        self.assertEqual(self.reserva.unidade_checkin, 'gama')

    def test_fotos_vistoria_persistem_no_storage(self):
        resp = self._post(_payload_registrar(self.reserva.id, 'checkin'))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        from django.core.files.storage import default_storage
        from vistorias.models import FotoVistoria
        fotos = FotoVistoria.objects.filter(vistoria_id=resp.data['id'])
        self.assertEqual(fotos.count(), 5)
        for foto in fotos:
            self.assertTrue(default_storage.exists(foto.foto.name))
            media = self.client.get(foto.foto.url)
            self.assertEqual(media.status_code, status.HTTP_200_OK)
            self.assertGreater(len(b''.join(media.streaming_content)), 0)


class ToleranciaHorarioReservaTests(APITestCase):
    """Limites de ±30 min (check-in/check-out) e overnight."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            matricula='tol_u', nome='Tol', password='senha123', is_admin=False,
        )
        self.veiculo = Veiculo.objects.create(
            placa='TOL1A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5,
            status='disponivel', km_atual=1000,
        )

    def _reserva(self, inicio, fim):
        return Reserva.objects.create(
            usuario=self.usuario, veiculo=self.veiculo,
            data_inicio=inicio, data_fim=fim,
            motivo='Tol', status='aprovada', modalidade='horario',
        )

    def test_constante_tolerancia_30(self):
        self.assertEqual(TOLERANCIA_RESERVA_MINUTOS, 30)

    def test_janela_overnight_com_tolerancia(self):
        tz = timezone.get_current_timezone()
        inicio = timezone.make_aware(datetime(2026, 9, 18, 20, 0, 0), tz)
        fim = timezone.make_aware(datetime(2026, 9, 19, 8, 0, 0), tz)
        reserva = self._reserva(inicio, fim)
        ini_tol, fim_tol = janela_reserva_com_tolerancia(reserva)
        self.assertEqual(ini_tol.hour, 19)
        self.assertEqual(ini_tol.minute, 30)
        self.assertEqual(fim_tol.day, 19)
        self.assertEqual(fim_tol.hour, 8)
        self.assertEqual(fim_tol.minute, 30)

    def test_limites_exatos_checkin(self):
        tz = timezone.get_current_timezone()
        inicio = timezone.make_aware(datetime(2026, 9, 18, 10, 0, 0), tz)
        fim = timezone.make_aware(datetime(2026, 9, 18, 12, 0, 0), tz)
        reserva = self._reserva(inicio, fim)

        validar_checkin_horario_reserva(reserva, inicio - timedelta(minutes=30))
        with self.assertRaises(Exception) as ctx:
            validar_checkin_horario_reserva(reserva, inicio - timedelta(minutes=31))
        self.assertIn(MSG_CHECKIN_ANTES, str(ctx.exception.detail))

        validar_checkin_horario_reserva(reserva, fim + timedelta(minutes=30))
        with self.assertRaises(Exception) as ctx2:
            validar_checkin_horario_reserva(reserva, fim + timedelta(minutes=31))
        self.assertIn(MSG_CHECKIN_DEPOIS, str(ctx2.exception.detail))

    def test_limites_exatos_checkout(self):
        tz = timezone.get_current_timezone()
        inicio = timezone.make_aware(datetime(2026, 9, 18, 10, 0, 0), tz)
        fim = timezone.make_aware(datetime(2026, 9, 18, 12, 0, 0), tz)
        reserva = self._reserva(inicio, fim)

        validar_checkout_horario_reserva(reserva, inicio - timedelta(minutes=30))
        with self.assertRaises(Exception) as ctx:
            validar_checkout_horario_reserva(reserva, inicio - timedelta(minutes=31))
        self.assertIn(MSG_CHECKOUT_ANTES, str(ctx.exception.detail))

        validar_checkout_horario_reserva(reserva, fim + timedelta(minutes=30))
        validar_checkout_horario_reserva(reserva, fim + timedelta(minutes=31))
        validar_checkout_horario_reserva(reserva, fim + timedelta(hours=5))


class CapsNormalizationTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='adm_caps', nome='Admin Caps', password='senha123', is_admin=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_veiculo_salvo_em_maiusculas(self):
        resp = self.client.post('/api/veiculos/', {
            'placa': 'abc1d23',
            'marca': 'toyota',
            'modelo': 'corolla xei',
            'ano': 2024,
            'cor': 'prata',
            'tipo_combustivel': 'flex',
            'capacidade': 5,
            'status': 'disponivel',
            'km_atual': 1000,
            'observacoes': 'veículo novo',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['marca'], 'TOYOTA')
        self.assertEqual(resp.data['modelo'], 'COROLLA XEI')
        self.assertEqual(resp.data['cor'], 'PRATA')
        self.assertEqual(resp.data['observacoes'], 'VEÍCULO NOVO')

    def test_usuario_nome_setor_maiusculas_email_intact(self):
        resp = self.client.post('/api/usuarios/', {
            'matricula': 'caps01',
            'nome': 'joão da silva',
            'email': 'Joao.Silva@Senai.br',
            'setor': 'desenvolvimento',
            'is_admin': False,
            'is_active': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = Usuario.objects.get(matricula='caps01')
        self.assertEqual(user.nome, 'JOÃO DA SILVA')
        self.assertEqual(user.setor, 'DESENVOLVIMENTO')
        self.assertEqual(user.email, 'Joao.Silva@Senai.br')
