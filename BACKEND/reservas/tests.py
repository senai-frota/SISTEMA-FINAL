from datetime import datetime, time, timedelta
from io import BytesIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from reservas.models import Reserva
from reservas.serializers import MSG_ANTECEDENCIA, MSG_PASSADO, MSG_TURNO_ENCERRADO
from reservas.views import MSG_ADMIN_NAO_RESERVA
from termos.models import TermoResponsabilidade, VALIDADE_DIAS
from usuarios.models import DocumentoCNH, CNH_DIAS_ALERTA_VENCIMENTO
from veiculos.models import Veiculo

Usuario = get_user_model()


def _pdf(name='doc.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake', content_type='application/pdf')


def _make_cnh(usuario, *, status_doc='aprovado', dias_validade=365, admin=None, data_validade=None):
    validade = data_validade
    if validade is None and status_doc == 'aprovado':
        validade = timezone.localdate() + timedelta(days=dias_validade)
    doc = DocumentoCNH.objects.create(
        usuario=usuario,
        data_validade=validade,
        arquivo=_pdf('cnh.pdf'),
        status='pendente' if status_doc == 'pendente' else status_doc,
    )
    if status_doc == 'aprovado':
        doc.status = 'aprovado'
        doc.admin_aprovador = admin
        doc.data_decisao = timezone.now()
        doc.data_validade = validade
        doc.save()
    elif status_doc == 'rejeitado':
        doc.status = 'rejeitado'
        doc.admin_aprovador = admin
        doc.data_decisao = timezone.now()
        doc.observacao_admin = 'Documento ilegível'
        doc.save()
    return doc


def _make_termo(usuario, *, status_doc='aprovado', admin=None, dias_validade=None, cpf_suffix='1'):
    validade = None
    if status_doc == 'aprovado':
        dias = dias_validade if dias_validade is not None else VALIDADE_DIAS
        validade = timezone.localdate() + timedelta(days=dias)
    termo = TermoResponsabilidade.objects.create(
        usuario=usuario,
        entidade='SENAI',
        cpf=f'0000000000{cpf_suffix}'[-11:],
        cnh=f'1000000000{cpf_suffix}'[-11:],
        data_solicitacao=timezone.localdate(),
        arquivo_pdf=_pdf('termo.pdf'),
        status=status_doc if status_doc != 'vencido' else 'aprovado',
        data_validade=validade if status_doc != 'vencido' else timezone.localdate() - timedelta(days=1),
        admin_aprovador=admin if status_doc in ('aprovado', 'vencido', 'rejeitado') else None,
        data_decisao=timezone.now() if status_doc in ('aprovado', 'vencido', 'rejeitado') else None,
    )
    return termo


def _veiculo(placa='TST1A23', km=1000):
    return Veiculo.objects.create(
        placa=placa, modelo='Onix', marca='Chevrolet', ano=2024,
        cor='Prata', tipo_combustivel='flex', capacidade=5,
        status='disponivel', km_atual=km,
    )


class ReservaAntecedenciaTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_ant', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_ant', nome='Solicitante', password='senha123', is_admin=False,
        )
        _make_cnh(self.usuario, admin=self.admin)
        _make_termo(self.usuario, admin=self.admin, cpf_suffix='1')
        self.veiculo = _veiculo('ANT1A23')
        self.url = '/api/reservas/'
        self.client.force_authenticate(user=self.usuario)

    def _payload(self, dias_inicio, hora=18, duracao_horas=2):
        base = timezone.localtime(timezone.now()).replace(
            hour=hora, minute=0, second=0, microsecond=0
        ) + timedelta(days=dias_inicio)
        if dias_inicio == 0 and base <= timezone.now():
            base = timezone.now() + timedelta(minutes=30)
            base = base.replace(second=0, microsecond=0)
        fim = base + timedelta(hours=duracao_horas)
        # Sem pernoite: início e fim devem permanecer no mesmo dia civil.
        if timezone.localtime(fim).date() != timezone.localtime(base).date():
            dia = timezone.localtime(base).date()
            tz = timezone.get_current_timezone()
            fim = timezone.make_aware(datetime.combine(dia, time(23, 45)), tz)
            if fim <= base:
                base = timezone.make_aware(datetime.combine(dia, time(23, 0)), tz)
                fim = timezone.make_aware(datetime.combine(dia, time(23, 30)), tz)
        return {
            'veiculo': self.veiculo.id,
            'modalidade': 'horario',
            'data_inicio': base.isoformat(),
            'data_fim': fim.isoformat(),
            'motivo': 'Visita técnica',
            'destino': 'SENAI Gama',
            'passageiros': 2,
        }

    def test_reserva_passada_rejeitada(self):
        response = self.client.post(self.url, self._payload(dias_inicio=-1), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['data_inicio'][0], MSG_PASSADO)

    def test_reserva_hoje_aceita(self):
        from unittest.mock import patch
        agora = timezone.localtime(timezone.now()).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        with patch('django.utils.timezone.now', return_value=agora):
            response = self.client.post(self.url, self._payload(dias_inicio=0), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reserva_amanha_aceita(self):
        response = self.client.post(self.url, self._payload(dias_inicio=1), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reserva_exatamente_14_dias_aceita(self):
        response = self.client.post(self.url, self._payload(dias_inicio=14), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_reserva_15_dias_rejeitada(self):
        response = self.client.post(self.url, self._payload(dias_inicio=15), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['data_inicio'][0], MSG_ANTECEDENCIA)


class ReservaCNHTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_cnh', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_cnh', nome='Func', password='senha123', is_admin=False,
        )
        _make_termo(self.usuario, admin=self.admin, cpf_suffix='2')
        self.veiculo = _veiculo('CNH1A23')
        self.url = '/api/reservas/'
        self.client.force_authenticate(user=self.usuario)

    def _payload(self):
        inicio = timezone.localtime(timezone.now()).replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=2)
        return {
            'veiculo': self.veiculo.id,
            'modalidade': 'horario',
            'data_inicio': inicio.isoformat(),
            'data_fim': (inicio + timedelta(hours=2)).isoformat(),
            'motivo': 'Serviço',
            'passageiros': 1,
        }

    def test_sem_cnh_nao_reserva(self):
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cnh_pendente_nao_reserva(self):
        _make_cnh(self.usuario, status_doc='pendente')
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cnh_rejeitada_nao_reserva(self):
        _make_cnh(self.usuario, status_doc='rejeitado', admin=self.admin)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cnh_vencida_nao_reserva(self):
        _make_cnh(
            self.usuario,
            status_doc='aprovado',
            admin=self.admin,
            data_validade=timezone.localdate() - timedelta(days=1),
        )
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cnh_aprovada_permite_reserva(self):
        _make_cnh(self.usuario, admin=self.admin)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_aprovacao_pelo_gestor_com_validade_libera_reserva(self):
        doc = _make_cnh(self.usuario, status_doc='pendente')
        self.client.force_authenticate(user=self.admin)
        validade = (timezone.localdate() + timedelta(days=200)).isoformat()
        resp = self.client.patch(
            f'/api/usuarios/cnh/{doc.id}/decisao/',
            {'status': 'aprovado', 'data_validade': validade},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'aprovado')
        self.assertEqual(doc.data_validade.isoformat(), validade)
        self.client.force_authenticate(user=self.usuario)
        response = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_aprovacao_sem_validade_rejeitada(self):
        doc = _make_cnh(self.usuario, status_doc='pendente')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/usuarios/cnh/{doc.id}/decisao/',
            {'status': 'aprovado'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ReservaHorarioTurnoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_ht', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_ht', nome='Func', password='senha123', is_admin=False,
        )
        _make_cnh(self.usuario, admin=self.admin)
        _make_termo(self.usuario, admin=self.admin, cpf_suffix='3')
        self.veiculo = _veiculo('HOR1A23')
        self.url = '/api/reservas/'
        self.client.force_authenticate(user=self.usuario)
        self.dia = timezone.localdate() + timedelta(days=3)

    def _horario(self, h_ini, h_fim):
        tz = timezone.get_current_timezone()
        inicio = timezone.make_aware(datetime.combine(self.dia, time(h_ini, 0)), tz)
        fim = timezone.make_aware(datetime.combine(self.dia, time(h_fim, 0)), tz)
        return {
            'veiculo': self.veiculo.id,
            'modalidade': 'horario',
            'data_inicio': inicio.isoformat(),
            'data_fim': fim.isoformat(),
            'motivo': 'Serviço',
            'passageiros': 1,
        }

    def test_mesmo_dia_sem_sobreposicao(self):
        r1 = self.client.post(self.url, self._horario(8, 12), format='json')
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        r2 = self.client.post(self.url, self._horario(14, 18), format='json')
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

    def test_mesmo_dia_com_sobreposicao(self):
        self.client.post(self.url, self._horario(8, 12), format='json')
        r2 = self.client.post(self.url, self._horario(10, 14), format='json')
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reserva_por_turno(self):
        response = self.client.post(self.url, {
            'veiculo': self.veiculo.id,
            'modalidade': 'turno',
            'turno': 'manha',
            'data': self.dia.isoformat(),
            'motivo': 'Turno manhã',
            'passageiros': 1,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reserva = Reserva.objects.get(veiculo=self.veiculo)
        self.assertEqual(reserva.modalidade, 'turno')
        self.assertEqual(reserva.turno, 'manha')
        self.assertEqual(timezone.localtime(reserva.data_inicio).hour, 6)
        self.assertEqual(timezone.localtime(reserva.data_fim).hour, 12)

    def test_conflito_turno_com_horario(self):
        self.client.post(self.url, self._horario(8, 12), format='json')
        r2 = self.client.post(self.url, {
            'veiculo': self.veiculo.id,
            'modalidade': 'turno',
            'turno': 'manha',
            'data': self.dia.isoformat(),
            'motivo': 'Turno',
            'passageiros': 1,
        }, format='json')
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def _agora_hoje(self, hora):
        tz = timezone.get_current_timezone()
        return timezone.make_aware(
            datetime.combine(timezone.localdate(), time(hora, 0)), tz
        )

    def _turno_hoje(self, turno):
        return {
            'veiculo': self.veiculo.id,
            'modalidade': 'turno',
            'turno': turno,
            'data': timezone.localdate().isoformat(),
            'motivo': 'Turno vigente',
            'passageiros': 1,
        }

    def test_turno_em_andamento_pode_ser_reservado(self):
        with mock.patch('django.utils.timezone.now', return_value=self._agora_hoje(10)):
            response = self.client.post(self.url, self._turno_hoje('manha'), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reserva = Reserva.objects.get(veiculo=self.veiculo)
        self.assertEqual(timezone.localtime(reserva.data_inicio).hour, 6)
        self.assertEqual(timezone.localtime(reserva.data_fim).hour, 12)

    def test_turno_encerrado_nao_pode_ser_reservado(self):
        with mock.patch('django.utils.timezone.now', return_value=self._agora_hoje(13)):
            response = self.client.post(self.url, self._turno_hoje('manha'), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['turno'][0], MSG_TURNO_ENCERRADO)

    def test_turno_em_andamento_com_conflito_continua_bloqueado(self):
        with mock.patch('django.utils.timezone.now', return_value=self._agora_hoje(10)):
            primeira = self.client.post(self.url, self._turno_hoje('manha'), format='json')
            segunda = self.client.post(self.url, self._turno_hoje('manha'), format='json')
        self.assertEqual(primeira.status_code, status.HTTP_201_CREATED, primeira.data)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disponibilidade_endpoint(self):
        self.client.post(self.url, self._horario(8, 12), format='json')
        payload = self._horario(14, 18)
        resp = self.client.get('/api/reservas/disponibilidade/', {
            'veiculo': self.veiculo.id,
            'data_inicio': payload['data_inicio'],
            'data_fim': payload['data_fim'],
        })
        self.assertTrue(resp.data['disponivel'])
        payload2 = self._horario(10, 11)
        resp2 = self.client.get('/api/reservas/disponibilidade/', {
            'veiculo': self.veiculo.id,
            'data_inicio': payload2['data_inicio'],
            'data_fim': payload2['data_fim'],
        })
        self.assertFalse(resp2.data['disponivel'])

    def test_cancelada_nao_bloqueia_disponibilidade(self):
        r1 = self.client.post(self.url, self._horario(8, 12), format='json')
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        reserva = Reserva.objects.filter(veiculo=self.veiculo).latest('id')
        cancel = self.client.delete(f'/api/reservas/{reserva.id}/')
        self.assertIn(cancel.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'cancelada')
        r2 = self.client.post(self.url, self._horario(8, 12), format='json')
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)


class ReservaPermissoesFluxoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_perm', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_perm', nome='Func', password='senha123', is_admin=False,
        )
        self.outro = Usuario.objects.create_user(
            matricula='outro_perm', nome='Outro', password='senha123', is_admin=False,
        )
        _make_cnh(self.usuario, admin=self.admin)
        _make_termo(self.usuario, admin=self.admin, cpf_suffix='5')
        _make_cnh(self.outro, admin=self.admin)
        _make_termo(self.outro, admin=self.admin, cpf_suffix='6')
        self.veiculo = _veiculo('PRM1A23')
        self.client.force_authenticate(user=self.usuario)
        inicio = timezone.localtime(timezone.now()).replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=2)
        resp = self.client.post('/api/reservas/', {
            'veiculo': self.veiculo.id,
            'modalidade': 'horario',
            'data_inicio': inicio.isoformat(),
            'data_fim': (inicio + timedelta(hours=2)).isoformat(),
            'motivo': 'Serviço',
            'passageiros': 1,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.reserva = Reserva.objects.get(usuario=self.usuario)

    def test_criacao_fica_pendente(self):
        self.assertEqual(self.reserva.status, 'pendente')

    def test_admin_nao_pode_criar_reserva(self):
        self.client.force_authenticate(user=self.admin)
        inicio = timezone.localtime(timezone.now()).replace(
            hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=3)
        resp = self.client.post('/api/reservas/', {
            'veiculo': self.veiculo.id,
            'modalidade': 'horario',
            'data_inicio': inicio.isoformat(),
            'data_fim': (inicio + timedelta(hours=1)).isoformat(),
            'motivo': 'Admin',
            'passageiros': 1,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data['detail'], MSG_ADMIN_NAO_RESERVA)
        self.assertFalse(Reserva.objects.filter(usuario=self.admin).exists())

    def test_admin_continua_listando_reservas(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/reservas/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {r['id'] for r in (resp.data.get('results') or resp.data)}
        self.assertIn(self.reserva.id, ids)

    def test_usuario_ve_somente_suas_reservas(self):
        self.client.force_authenticate(user=self.outro)
        inicio = timezone.localtime(timezone.now()).replace(
            hour=14, minute=0, second=0, microsecond=0
        ) + timedelta(days=2)
        self.client.post('/api/reservas/', {
            'veiculo': self.veiculo.id,
            'modalidade': 'horario',
            'data_inicio': inicio.isoformat(),
            'data_fim': (inicio + timedelta(hours=1)).isoformat(),
            'motivo': 'Outro',
            'passageiros': 1,
        }, format='json')
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.get('/api/reservas/')
        ids = {r['id'] for r in (resp.data.get('results') or resp.data)}
        self.assertIn(self.reserva.id, ids)
        self.assertEqual(len(ids), 1)

    def test_usuario_nao_acessa_reserva_de_outro_por_id(self):
        self.client.force_authenticate(user=self.outro)
        resp = self.client.get(f'/api/reservas/{self.reserva.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_usuario_nao_cancela_reserva_de_outro(self):
        self.client.force_authenticate(user=self.outro)
        resp = self.client.delete(f'/api/reservas/{self.reserva.id}/')
        self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'pendente')

    def test_usuario_nao_aprova_nem_rejeita(self):
        self.client.force_authenticate(user=self.usuario)
        for st in ('aprovada', 'negada'):
            resp = self.client.patch(
                f'/api/reservas/{self.reserva.id}/aprovar/',
                {'status': st},
                format='json',
            )
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'pendente')

    def test_admin_lista_aprova_e_nao_reanalisa(self):
        self.client.force_authenticate(user=self.admin)
        lista = self.client.get('/api/reservas/', {'status': 'pendente'})
        ids = {r['id'] for r in (lista.data.get('results') or lista.data)}
        self.assertIn(self.reserva.id, ids)

        ok = self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'aprovada'},
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'aprovada')

        again = self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'negada'},
            format='json',
        )
        self.assertEqual(again.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_rejeita(self):
        reserva = Reserva.objects.create(
            usuario=self.usuario,
            veiculo=self.veiculo,
            data_inicio=timezone.now() + timedelta(days=4),
            data_fim=timezone.now() + timedelta(days=4, hours=2),
            motivo='Rejeitar',
            status='pendente',
            modalidade='horario',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/reservas/{reserva.id}/aprovar/',
            {'status': 'negada', 'observacao_admin': 'Indisponível'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'negada')
        self.assertEqual(reserva.observacao_admin, 'INDISPONÍVEL')

    def test_admin_cancela_aprovada_e_nao_rejeita(self):
        self.client.force_authenticate(user=self.admin)
        ok = self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'aprovada'},
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        rejeita = self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'negada', 'observacao_admin': 'Tarde demais'},
            format='json',
        )
        self.assertEqual(rejeita.status_code, status.HTTP_403_FORBIDDEN)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'aprovada')
        cancela = self.client.delete(
            f'/api/reservas/{self.reserva.id}/',
            {'justificativa': 'Mudança de agenda'},
            format='json',
        )
        self.assertEqual(cancela.status_code, status.HTTP_204_NO_CONTENT)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'cancelada')

    def test_nao_cancela_reserva_negada_nem_ja_cancelada(self):
        self.client.force_authenticate(user=self.admin)
        self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'negada', 'observacao_admin': 'Indisponível'},
            format='json',
        )
        resp = self.client.delete(f'/api/reservas/{self.reserva.id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'negada')

        outra = Reserva.objects.create(
            usuario=self.usuario,
            veiculo=self.veiculo,
            data_inicio=timezone.now() + timedelta(days=5),
            data_fim=timezone.now() + timedelta(days=5, hours=2),
            motivo='Cancelar duas vezes',
            status='pendente',
            modalidade='horario',
        )
        self.client.force_authenticate(user=self.usuario)
        self.assertEqual(self.client.delete(f'/api/reservas/{outra.id}/').status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self.client.delete(f'/api/reservas/{outra.id}/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_cancelada_permanece_e_nao_pode_ser_aprovada(self):
        self.client.force_authenticate(user=self.usuario)
        self.client.delete(f'/api/reservas/{self.reserva.id}/')
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, 'cancelada')
        self.assertTrue(Reserva.objects.filter(pk=self.reserva.pk).exists())
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/reservas/{self.reserva.id}/aprovar/',
            {'status': 'aprovada'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ReservaPernoiteTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_pn', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_pn', nome='Func', password='senha123', is_admin=False,
        )
        self.outro = Usuario.objects.create_user(
            matricula='outro_pn', nome='Outro', password='senha123', is_admin=False,
        )
        _make_cnh(self.usuario, admin=self.admin)
        _make_termo(self.usuario, admin=self.admin, cpf_suffix='7')
        _make_cnh(self.outro, admin=self.admin)
        _make_termo(self.outro, admin=self.admin, cpf_suffix='8')
        self.veiculo = _veiculo('PRN1A23', km=20000)
        self.url = '/api/reservas/'
        self.client.force_authenticate(user=self.usuario)
        self.dia = timezone.localdate() + timedelta(days=2)
        self.dia2 = self.dia + timedelta(days=1)

    def _aware(self, dia, hora, minuto=0):
        tz = timezone.get_current_timezone()
        return timezone.make_aware(datetime.combine(dia, time(hora, minuto)), tz)

    def _payload(self, dia_ini, h_ini, dia_fim, h_fim, **extra):
        payload = {
            'veiculo': self.veiculo.id,
            'modalidade': 'horario',
            'data_inicio': self._aware(dia_ini, h_ini).isoformat(),
            'data_fim': self._aware(dia_fim, h_fim).isoformat(),
            'motivo': 'Viagem',
            'passageiros': 1,
            'pernoite': False,
        }
        payload.update(extra)
        return payload

    def test_criar_reserva_sem_pernoite(self):
        resp = self.client.post(
            self.url,
            self._payload(self.dia, 8, self.dia, 12),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        reserva = Reserva.objects.latest('id')
        self.assertFalse(reserva.pernoite)
        self.assertIn(reserva.unidade_pernoite, (None, ''))

    def test_criar_reserva_com_pernoite_e_unidade(self):
        resp = self.client.post(
            self.url,
            self._payload(
                self.dia, 8, self.dia2, 17,
                motivo='Missão externa',
                passageiros=2,
                pernoite=True,
                unidade_pernoite='unidade senai gama',
            ),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        reserva = Reserva.objects.latest('id')
        self.assertTrue(reserva.pernoite)
        self.assertEqual(reserva.unidade_pernoite, 'UNIDADE SENAI GAMA')
        self.assertEqual(timezone.localtime(reserva.data_inicio).date(), self.dia)
        self.assertEqual(timezone.localtime(reserva.data_fim).date(), self.dia2)

    def test_rejeitar_pernoite_sem_unidade(self):
        resp = self.client.post(
            self.url,
            self._payload(
                self.dia, 8, self.dia2, 17,
                motivo='Missão',
                pernoite=True,
                unidade_pernoite='',
            ),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('unidade_pernoite', resp.data)

    def test_aceitar_pernoite_com_unidade(self):
        resp = self.client.post(
            self.url,
            self._payload(
                self.dia, 8, self.dia2, 17,
                pernoite=True,
                unidade_pernoite='UNIDADE SENAI TAGUATINGA',
            ),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data.get('pernoite') or Reserva.objects.latest('id').pernoite)

    def test_multiplo_dia_sem_pernoite_bloqueado(self):
        resp = self.client.post(
            self.url,
            self._payload(
                self.dia, 8, self.dia2, 17,
                motivo='Sem pernoite',
                pernoite=False,
            ),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conflito_no_periodo_completo_com_pernoite(self):
        ok = self.client.post(
            self.url,
            self._payload(
                self.dia, 8, self.dia2, 17,
                motivo='Missão longa',
                pernoite=True,
                unidade_pernoite='SENAI TAGUATINGA',
            ),
            format='json',
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.outro)
        conflito = self.client.post(
            self.url,
            self._payload(
                self.dia2, 9, self.dia2, 12,
                motivo='Outra reserva',
                pernoite=False,
            ),
            format='json',
        )
        self.assertEqual(conflito.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_visualiza_pernoite(self):
        self.client.post(
            self.url,
            self._payload(
                self.dia, 8, self.dia2, 17,
                motivo='Missão',
                pernoite=True,
                unidade_pernoite='SENAI GAMA',
            ),
            format='json',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        itens = resp.data.get('results', resp.data)
        alvo = next(r for r in itens if r.get('pernoite'))
        self.assertTrue(alvo['pernoite'])
        self.assertEqual(alvo['unidade_pernoite'], 'SENAI GAMA')

    def test_checkin_unico_checkout_final_e_sem_liberacao_automatica(self):
        from unittest.mock import patch
        from vistorias.dispositivo import FOTOS_OBRIGATORIAS

        png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
            b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        foto = lambda name: SimpleUploadedFile(name, png, content_type='image/png')
        mobile = {
            'HTTP_X_CLIENT_FORM_FACTOR': 'mobile',
            'HTTP_USER_AGENT': (
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
                'AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1'
            ),
        }

        reserva = Reserva.objects.create(
            usuario=self.usuario,
            veiculo=self.veiculo,
            data_inicio=self._aware(self.dia, 8),
            data_fim=self._aware(self.dia2, 17),
            motivo='PERNOITE',
            status='aprovada',
            modalidade='horario',
            pernoite=True,
            unidade_pernoite='SENAI GAMA',
        )
        self.veiculo.status = 'disponivel'
        self.veiculo.km_atual = 20000
        self.veiculo.save()

        def payload(tipo, **extra):
            data = {
                'reserva': reserva.id,
                'tipo': tipo,
                'unidade': 'gama',
                'fotos': [foto(f'{a}.png') for a in FOTOS_OBRIGATORIAS],
                'descricoes': list(FOTOS_OBRIGATORIAS),
            }
            data.update(extra)
            return data

        momento_dia1 = self._aware(self.dia, 10)
        with patch('vistorias.regras.agora_local', return_value=momento_dia1):
            r1 = self.client.post(
                '/api/vistorias/registrar/', payload('checkin'), format='multipart', **mobile
            )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.veiculo.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'em_uso')
        self.assertEqual(reserva.status, 'em_andamento')

        depois_das_22 = self._aware(self.dia, 22, 30)
        self.assertFalse(
            timezone.localtime(depois_das_22).time() <= time(22, 0)
            and self.veiculo.status == 'disponivel'
        )
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'em_uso')
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'em_andamento')

        momento_dia2 = self._aware(self.dia2, 9)
        with patch('vistorias.regras.agora_local', return_value=momento_dia2):
            r2 = self.client.post(
                '/api/vistorias/registrar/', payload('checkin'), format='multipart', **mobile
            )
        # Pernoite não cria check-in extra: a nova tentativa reaproveita o
        # check-in já gravado (idempotente) e não altera o status.
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertTrue(r2.data.get('idempotente'))
        from vistorias.models import Vistoria
        self.assertEqual(Vistoria.objects.filter(reserva=reserva, tipo='checkin').count(), 1)
        reserva.refresh_from_db()
        self.assertEqual(reserva.status, 'em_andamento')

        with patch('vistorias.regras.agora_local', return_value=momento_dia2):
            r3 = self.client.post(
                '/api/vistorias/registrar/',
                payload('checkout', quilometragem=20450),
                format='multipart',
                **mobile,
            )
        self.assertEqual(r3.status_code, status.HTTP_201_CREATED)
        self.veiculo.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(self.veiculo.status, 'disponivel')
        self.assertEqual(self.veiculo.km_atual, 20450)
        self.assertEqual(reserva.status, 'concluida')

    def test_usuario_nao_acessa_reserva_pernoite_de_outro(self):
        reserva = Reserva.objects.create(
            usuario=self.usuario,
            veiculo=self.veiculo,
            data_inicio=self._aware(self.dia, 8),
            data_fim=self._aware(self.dia2, 17),
            motivo='PRIVADA',
            status='aprovada',
            modalidade='horario',
            pernoite=True,
            unidade_pernoite='SENAI GAMA',
        )
        self.client.force_authenticate(user=self.outro)
        resp = self.client.get(f'/api/reservas/{reserva.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
