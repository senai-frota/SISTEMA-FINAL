from datetime import datetime, timedelta
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from auditoria.models import RegistroAuditoria
from reservas.models import (
    MOTIVO_CANCELAMENTO_FALTA_CHECKIN,
    AutorizacaoCheckinAntecipado,
    EventoOperacional,
    Reserva,
)
from reservas.operacoes import (
    executar_rotina,
    momento_cancelamento_automatico,
)
from usuarios.models import DocumentoCNH, Usuario
from veiculos.models import Veiculo
from vistorias.dispositivo import FOTOS_OBRIGATORIAS
from vistorias.models import FotoVistoria, Vistoria
from vistorias.tests import MOBILE_UA, _foto, _payload_registrar, _pdf


class OperacoesBase(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='op_adm', nome='Admin Op', password='senha123',
            is_admin=True, email='admin.op@example.com',
        )
        self.usuario = Usuario.objects.create_user(
            matricula='op_func', nome='Func Op', password='senha123',
            email='func.op@example.com',
        )
        DocumentoCNH.objects.create(
            usuario=self.usuario, arquivo=_pdf(), status='aprovado',
            data_validade=timezone.localdate() + timedelta(days=200),
            admin_aprovador=self.admin, data_decisao=timezone.now(),
        )
        self.veiculo = Veiculo.objects.create(
            placa='OP01A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5,
            status='disponivel', km_atual=1000,
        )

    def _reserva(self, **extra):
        tz = timezone.get_current_timezone()
        inicio = extra.pop(
            'data_inicio',
            timezone.make_aware(datetime(2026, 10, 20, 10, 0, 0), tz),
        )
        fim = extra.pop('data_fim', inicio + timedelta(hours=2))
        extra.setdefault('status', 'aprovada')
        extra.setdefault('motivo', 'SERVICO')
        extra.setdefault('modalidade', 'horario')
        return Reserva.objects.create(
            usuario=self.usuario, veiculo=self.veiculo,
            data_inicio=inicio, data_fim=fim, **extra,
        )

    def _momento(self, reserva, hora, minuto=0, dia_offset=0):
        local = timezone.localtime(reserva.data_inicio) + timedelta(days=dia_offset)
        return local.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    def _post_vistoria(self, reserva, tipo, momento, **extra):
        kw = {
            'HTTP_X_CLIENT_FORM_FACTOR': 'mobile',
            'HTTP_USER_AGENT': MOBILE_UA,
        }
        with patch('vistorias.regras.agora_local', return_value=momento):
            return self.client.post(
                '/api/vistorias/registrar/',
                _payload_registrar(reserva.id, tipo, **extra),
                format='multipart',
                **kw,
            )


class CheckinAntecipadoTests(OperacoesBase):
    def test_sem_autorizacao_antes_da_janela_bloqueado(self):
        reserva = self._reserva()
        self.client.force_authenticate(user=self.usuario)
        resp = self._post_vistoria(reserva, 'checkin', self._momento(reserva, 8, 0))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('30 minutos', str(resp.data))

    def test_solicitar_aprovar_e_fazer_checkin_antecipado(self):
        reserva = self._reserva()
        momento = self._momento(reserva, 8, 0)
        self.client.force_authenticate(user=self.usuario)
        with patch('vistorias.regras.agora_local', return_value=momento):
            pedido = self.client.post(
                f'/api/reservas/{reserva.id}/checkin-antecipado/',
                {'justificativa': 'Reunião na unidade Gama às 8h.'},
                format='json',
            )
        self.assertEqual(pedido.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pedido.data['status'], 'pendente')

        with patch('vistorias.regras.agora_local', return_value=momento):
            duplicado = self.client.post(
                f'/api/reservas/{reserva.id}/checkin-antecipado/',
                {'justificativa': 'Outro pedido.'},
                format='json',
            )
        self.assertEqual(duplicado.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(user=self.admin)
        decisao = self.client.patch(
            f'/api/reservas/autorizacoes-checkin/{pedido.data["id"]}/',
            {'status': 'aprovada'},
            format='json',
        )
        self.assertEqual(decisao.status_code, status.HTTP_200_OK)
        self.assertEqual(decisao.data['status'], 'aprovada')
        self.assertEqual(decisao.data['admin_nome'], 'Admin Op')
        self.assertIsNotNone(decisao.data['decidido_em'])

        self.client.force_authenticate(user=self.usuario)
        resp = self._post_vistoria(reserva, 'checkin', momento)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'em_andamento')
        self.assertEqual(
            RegistroAuditoria.objects.filter(acao='aprovar_checkin_antecipado').count(), 1,
        )

    def test_rejeitado_continua_bloqueado_e_permite_novo_pedido(self):
        reserva = self._reserva()
        momento = self._momento(reserva, 8, 0)
        self.client.force_authenticate(user=self.usuario)
        with patch('vistorias.regras.agora_local', return_value=momento):
            pedido = self.client.post(
                f'/api/reservas/{reserva.id}/checkin-antecipado/',
                {'justificativa': 'Chegada cedo.'},
                format='json',
            )
        self.client.force_authenticate(user=self.admin)
        rejeicao = self.client.patch(
            f'/api/reservas/autorizacoes-checkin/{pedido.data["id"]}/',
            {'status': 'rejeitada', 'observacao_admin': 'Horário da frota não permite.'},
            format='json',
        )
        self.assertEqual(rejeicao.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.usuario)
        resp = self._post_vistoria(reserva, 'checkin', momento)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        with patch('vistorias.regras.agora_local', return_value=momento):
            novo = self.client.post(
                f'/api/reservas/{reserva.id}/checkin-antecipado/',
                {'justificativa': 'Nova justificativa.'},
                format='json',
            )
        self.assertEqual(novo.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            AutorizacaoCheckinAntecipado.objects.filter(reserva=reserva).count(), 2,
        )

    def test_autorizacao_nao_abre_operacao_noturna(self):
        reserva = self._reserva()
        AutorizacaoCheckinAntecipado.objects.create(
            reserva=reserva, solicitante=self.usuario, justificativa='URGENTE',
            status='aprovada', admin_decisor=self.admin, decidido_em=timezone.now(),
        )
        self.client.force_authenticate(user=self.usuario)
        resp = self._post_vistoria(reserva, 'checkin', self._momento(reserva, 5, 0))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('06:00', str(resp.data))

    def test_autorizacao_nao_altera_checkout(self):
        reserva = self._reserva()
        AutorizacaoCheckinAntecipado.objects.create(
            reserva=reserva, solicitante=self.usuario, justificativa='URGENTE',
            status='aprovada', admin_decisor=self.admin, decidido_em=timezone.now(),
        )
        self.client.force_authenticate(user=self.usuario)
        checkin = self._post_vistoria(reserva, 'checkin', self._momento(reserva, 8, 0))
        self.assertEqual(checkin.status_code, status.HTTP_201_CREATED)
        cedo_demais = self._post_vistoria(
            reserva, 'checkout', self._momento(reserva, 8, 0),
            quilometragem=1100, unidade='gama',
        )
        self.assertEqual(cedo_demais.status_code, status.HTTP_400_BAD_REQUEST)
        atrasado = self._post_vistoria(
            reserva, 'checkout', self._momento(reserva, 13, 0),
            quilometragem=1100, unidade='gama',
        )
        self.assertEqual(atrasado.status_code, status.HTTP_201_CREATED)


class CancelamentoAutomaticoTests(OperacoesBase):
    def test_cancela_a_meia_noite_do_dia_seguinte(self):
        reserva = self._reserva()
        limite = momento_cancelamento_automatico(reserva)
        self.assertEqual(limite.hour, 0)
        self.assertEqual(limite.minute, 0)
        self.assertEqual(timezone.localtime(limite).date(), timezone.localtime(reserva.data_fim).date() + timedelta(days=1))

        antes = limite - timedelta(minutes=1)
        executar_rotina(antes)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'aprovada')

        executar_rotina(limite)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'cancelada')
        self.assertEqual(reserva.motivo_cancelamento, MOTIVO_CANCELAMENTO_FALTA_CHECKIN)
        self.assertTrue(reserva.cancelamento_automatico)
        self.assertEqual(self.veiculo.status, 'disponivel')

        executar_rotina(limite + timedelta(hours=1))
        self.assertEqual(
            EventoOperacional.objects.filter(
                tipo=EventoOperacional.Tipo.CANCELAMENTO_AUTOMATICO,
                reserva=reserva,
            ).filter(chave=f'{EventoOperacional.Tipo.CANCELAMENTO_AUTOMATICO}:{reserva.id}').count(),
            1,
        )
        self.assertEqual(
            RegistroAuditoria.objects.filter(acao='cancelar_reserva_auto', entidade_id=reserva.id).count(),
            1,
        )

    def test_nao_cancela_se_houve_checkin(self):
        reserva = self._reserva()
        Vistoria.objects.create(
            reserva=reserva, tipo='checkin', unidade='taguatinga',
            quilometragem=1000, realizada_por=self.usuario,
        )
        reserva.status = 'em_andamento'
        reserva.save()
        executar_rotina(momento_cancelamento_automatico(reserva) + timedelta(days=1))
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'em_andamento')

    def test_pernoite_nao_impede_nem_dispensa_cancelamento(self):
        reserva = self._reserva(pernoite=True, unidade_pernoite='SENAI GAMA')
        executar_rotina(momento_cancelamento_automatico(reserva))
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'cancelada')
        self.assertEqual(reserva.motivo_cancelamento, MOTIVO_CANCELAMENTO_FALTA_CHECKIN)

    def test_comando_management_e_idempotente(self):
        reserva = self._reserva()
        with patch('reservas.operacoes.local_ou', return_value=momento_cancelamento_automatico(reserva)):
            call_command('rotina_operacional')
            call_command('rotina_operacional')
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'cancelada')
        self.assertEqual(
            RegistroAuditoria.objects.filter(acao='cancelar_reserva_auto').count(), 1,
        )


class CheckoutAtrasadoAlertasTests(OperacoesBase):
    def test_alerta_checkout_atrasado_sem_duplicar(self):
        reserva = self._reserva()
        Vistoria.objects.create(
            reserva=reserva, tipo='checkin', unidade='taguatinga',
            quilometragem=1000, realizada_por=self.usuario,
        )
        reserva.status = 'em_andamento'
        reserva.unidade_checkin = 'taguatinga'
        reserva.save()
        self.veiculo.status = 'em_uso'
        self.veiculo.save()

        momento = timezone.localtime(reserva.data_fim) + timedelta(hours=2)
        executar_rotina(momento)
        executar_rotina(momento)
        self.assertEqual(
            EventoOperacional.objects.filter(
                tipo=EventoOperacional.Tipo.CHECKOUT_ATRASADO, reserva=reserva,
            ).count(),
            1,
        )

        self.client.force_authenticate(user=self.admin)
        with patch('reservas.operacoes.local_ou', return_value=momento):
            alertas = self.client.get('/api/reservas/alertas-operacionais/')
        self.assertEqual(alertas.status_code, status.HTTP_200_OK)
        tipos = [i['tipo'] for i in alertas.data['criticos']]
        self.assertIn('checkout_atrasado', tipos)

    def test_cinco_fotos_persistem_no_checkin_antecipado(self):
        reserva = self._reserva()
        AutorizacaoCheckinAntecipado.objects.create(
            reserva=reserva, solicitante=self.usuario, justificativa='URGENTE',
            status='aprovada', admin_decisor=self.admin, decidido_em=timezone.now(),
        )
        self.client.force_authenticate(user=self.usuario)
        resp = self._post_vistoria(reserva, 'checkin', self._momento(reserva, 8, 0))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data['fotos']), 5)
        self.assertEqual(FotoVistoria.objects.filter(vistoria_id=resp.data['id']).count(), 5)
        self.assertEqual(set(FOTOS_OBRIGATORIAS), set(
            FotoVistoria.objects.filter(vistoria_id=resp.data['id']).values_list('descricao', flat=True)
        ))

    @override_settings(
        FROTA_EMAIL_ENABLED=False,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_email_desligado_nao_envia_e_nao_bloqueia_alerta(self):
        reserva = self._reserva()
        executar_rotina(momento_cancelamento_automatico(reserva))
        self.assertEqual(len(mail.outbox), 0)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'cancelada')

    def test_usuario_sem_email_continua_com_alerta_interno(self):
        self.usuario.email = ''
        self.usuario.save()
        reserva = self._reserva()
        Vistoria.objects.create(
            reserva=reserva, tipo='checkin', unidade='taguatinga',
            quilometragem=1000, realizada_por=self.usuario,
        )
        reserva.status = 'em_andamento'
        reserva.save()
        momento = timezone.localtime(reserva.data_fim) + timedelta(hours=3)
        executar_rotina(momento)
        self.client.force_authenticate(user=self.usuario)
        with patch('reservas.operacoes.local_ou', return_value=momento):
            alertas = self.client.get('/api/reservas/alertas-operacionais/')
        self.assertTrue(any(i['tipo'] == 'checkout_atrasado' for i in alertas.data['criticos']))
