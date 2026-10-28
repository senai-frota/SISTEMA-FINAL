from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from reservas.models import Reserva
from termos.models import TermoResponsabilidade
from usuarios.models import DocumentoCNH, Usuario
from veiculos.models import Veiculo

from .integridade import verificar_cadeia
from .models import RegistroAuditoria
from .services import MSG_JUSTIFICATIVA_OBRIGATORIA

JUSTIFICATIVAS_INVALIDAS = (None, '', '   ', '\n\t ')


def _pdf(nome='doc.pdf'):
    return SimpleUploadedFile(nome, b'%PDF-1.4 fake', content_type='application/pdf')


class BaseRecusa(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='rec_admin', nome='Admin Recusa', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='rec_func', nome='Func Recusa', password='senha123',
        )
        self.veiculo = Veiculo.objects.create(
            placa='REC1A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5, status='disponivel',
        )

    def _payload(self, status_decisao, justificativa):
        dados = {'status': status_decisao}
        if justificativa is not None:
            dados['observacao_admin'] = justificativa
        return dados

    def _ultimo_log(self, acao):
        return RegistroAuditoria.objects.filter(acao=acao).order_by('-sequencia').first()

    def _conferir_log(self, acao, entidade, entidade_id, justificativa):
        log = self._ultimo_log(acao)
        self.assertIsNotNone(log)
        self.assertEqual(log.entidade, entidade)
        self.assertEqual(log.entidade_id, entidade_id)
        self.assertEqual(log.ator_id, self.admin.id)
        self.assertEqual(log.ator_nome, 'Admin Recusa')
        self.assertEqual(log.usuario_afetado_id, self.usuario.id)
        self.assertEqual(log.usuario_afetado_nome, 'Func Recusa')
        self.assertEqual(log.justificativa, justificativa)
        self.assertTrue(log.descricao)
        self.assertIsNotNone(log.criado_em)
        self.assertTrue(verificar_cadeia()['integra'])
        return log


class RecusaReservaTests(BaseRecusa):
    def setUp(self):
        super().setUp()
        inicio = timezone.now() + timedelta(days=2)
        self.reserva = Reserva.objects.create(
            usuario=self.usuario, veiculo=self.veiculo, data_inicio=inicio,
            data_fim=inicio + timedelta(hours=2), motivo='SERVIÇO', modalidade='horario',
        )
        self.url = f'/api/reservas/{self.reserva.id}/aprovar/'

    def test_negar_sem_justificativa_e_bloqueado(self):
        self.client.force_authenticate(user=self.admin)
        for valor in JUSTIFICATIVAS_INVALIDAS:
            resp = self.client.patch(self.url, self._payload('negada', valor), format='json')
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, repr(valor))
            self.assertEqual(resp.data['observacao_admin'], [MSG_JUSTIFICATIVA_OBRIGATORIA])
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'pendente')
        self.assertIsNone(self._ultimo_log('rejeitar_reserva'))

    def test_negar_com_justificativa_registra_na_reserva_e_na_auditoria(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            self.url, self._payload('negada', '  Veículo em revisão nesta data.  '), format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'negada')
        self.assertEqual(self.reserva.observacao_admin, 'VEÍCULO EM REVISÃO NESTA DATA.')
        self._conferir_log('rejeitar_reserva', 'reserva', self.reserva.id, 'VEÍCULO EM REVISÃO NESTA DATA.')

    def test_aprovar_continua_sem_justificativa(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(self.url, {'status': 'aprovada'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self._ultimo_log('aprovar_reserva').justificativa, '')

    def test_funcionario_nao_nega(self):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(self.url, self._payload('negada', 'Tentativa'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'pendente')


class CancelamentoPeloAdminTests(BaseRecusa):
    def setUp(self):
        super().setUp()
        inicio = timezone.now() + timedelta(days=3)
        self.reserva = Reserva.objects.create(
            usuario=self.usuario, veiculo=self.veiculo, data_inicio=inicio,
            data_fim=inicio + timedelta(hours=2), motivo='SERVIÇO', modalidade='horario',
            status='aprovada',
        )
        self.url = f'/api/reservas/{self.reserva.id}/'

    def test_admin_cancelar_reserva_de_outro_exige_justificativa(self):
        self.client.force_authenticate(user=self.admin)
        for valor in ('', '   '):
            resp = self.client.delete(self.url, {'justificativa': valor}, format='json')
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(resp.data['justificativa'], [MSG_JUSTIFICATIVA_OBRIGATORIA])
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'aprovada')

    def test_admin_cancelar_com_justificativa(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(self.url, {'justificativa': 'Veículo quebrou.'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'cancelada')
        self.assertEqual(self.reserva.observacao_admin, 'VEÍCULO QUEBROU.')
        self._conferir_log('cancelar_reserva', 'reserva', self.reserva.id, 'VEÍCULO QUEBROU.')

    def test_usuario_cancela_a_propria_sem_justificativa(self):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.delete(self.url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'cancelada')


class RecusaTermoTests(BaseRecusa):
    def setUp(self):
        super().setUp()
        self.termo = TermoResponsabilidade.objects.create(
            usuario=self.usuario, entidade='SENAI', cpf='11111111111', cnh='22222222222',
            data_solicitacao=timezone.localdate(), arquivo_pdf=_pdf('termo.pdf'),
            status='pendente',
        )
        self.url = f'/api/termos/{self.termo.id}/decisao/'

    def test_rejeitar_sem_justificativa_e_bloqueado(self):
        self.client.force_authenticate(user=self.admin)
        for valor in JUSTIFICATIVAS_INVALIDAS:
            resp = self.client.patch(self.url, self._payload('rejeitado', valor), format='json')
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, repr(valor))
        self.termo.refresh_from_db()
        self.assertEqual(self.termo.status, 'pendente')

    def test_rejeitar_com_justificativa(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            self.url,
            self._payload('rejeitado', 'Documento ilegível. Favor enviar uma nova versão.'),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.termo.refresh_from_db()
        esperado = 'DOCUMENTO ILEGÍVEL. FAVOR ENVIAR UMA NOVA VERSÃO.'
        self.assertEqual(self.termo.status, 'rejeitado')
        self.assertEqual(self.termo.observacao_admin, esperado)
        self._conferir_log('rejeitar_termo', 'termo', self.termo.id, esperado)

    def test_funcionario_nao_rejeita(self):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(self.url, self._payload('rejeitado', 'x'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class RecusaCNHTests(BaseRecusa):
    def setUp(self):
        super().setUp()
        self.doc = DocumentoCNH.objects.create(
            usuario=self.usuario, arquivo=_pdf('cnh.pdf'), status='pendente',
        )
        self.url = f'/api/usuarios/cnh/{self.doc.id}/decisao/'

    def test_rejeitar_sem_justificativa_e_bloqueado(self):
        self.client.force_authenticate(user=self.admin)
        for valor in JUSTIFICATIVAS_INVALIDAS:
            resp = self.client.patch(self.url, self._payload('rejeitado', valor), format='json')
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, repr(valor))
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, 'pendente')

    def test_rejeitar_com_justificativa(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(self.url, self._payload('rejeitado', 'Foto cortada.'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, 'rejeitado')
        self.assertEqual(self.doc.observacao_admin, 'FOTO CORTADA.')
        self._conferir_log('rejeitar_cnh', 'cnh', self.doc.id, 'FOTO CORTADA.')

    def test_aprovar_nao_exige_justificativa(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            self.url,
            {'status': 'aprovado', 'data_validade': str(timezone.localdate() + timedelta(days=200))},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_funcionario_nao_rejeita(self):
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(self.url, self._payload('rejeitado', 'x'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
