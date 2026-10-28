from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from termos.models import TermoResponsabilidade, VALIDADE_DIAS
from termos.services_conta import sincronizar_status_conta, resumo_termo_usuario
from usuarios.models import DocumentoCNH
from veiculos.models import Veiculo

Usuario = get_user_model()


def _pdf(name='termo.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 fake', content_type='application/pdf')


def _make_cnh(usuario, admin):
    return DocumentoCNH.objects.create(
        usuario=usuario,
        data_validade=timezone.localdate() + timedelta(days=365),
        arquivo=_pdf('cnh.pdf'),
        status='aprovado',
        admin_aprovador=admin,
        data_decisao=timezone.now(),
    )


class TermoFluxoTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            matricula='admin_termo', nome='Admin', password='senha123', is_admin=True,
        )
        self.usuario = Usuario.objects.create_user(
            matricula='func_termo', nome='Func', password='senha123', is_admin=False,
        )
        _make_cnh(self.usuario, self.admin)
        self.veiculo = Veiculo.objects.create(
            placa='TRM1A23', modelo='Onix', marca='Chevrolet', ano=2024,
            cor='Prata', tipo_combustivel='flex', capacidade=5, status='disponivel',
        )

    def _payload_reserva(self):
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

    def test_termo_valido_mantem_conta_ativa(self):
        TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333333',
            cnh='44444444444',
            data_solicitacao=timezone.localdate(),
            arquivo_pdf=_pdf(),
            status='aprovado',
            data_validade=timezone.localdate() + timedelta(days=VALIDADE_DIAS),
            admin_aprovador=self.admin,
            data_decisao=timezone.now(),
        )
        sincronizar_status_conta(self.usuario)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)
        resumo = resumo_termo_usuario(self.usuario)
        self.assertEqual(resumo['situacao'], 'valido')
        self.assertTrue(resumo['pode_reservar'])

    def test_termo_vencido_torna_conta_inativa(self):
        TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333334',
            cnh='44444444445',
            data_solicitacao=timezone.localdate() - timedelta(days=400),
            arquivo_pdf=_pdf(),
            status='aprovado',
            data_validade=timezone.localdate() - timedelta(days=1),
            admin_aprovador=self.admin,
            data_decisao=timezone.now() - timedelta(days=366),
        )
        sincronizar_status_conta(self.usuario)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)
        resumo = resumo_termo_usuario(self.usuario)
        self.assertEqual(resumo['situacao'], 'vencido')

    def test_usuario_inativo_nao_cria_reserva(self):
        TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333335',
            cnh='44444444446',
            data_solicitacao=timezone.localdate() - timedelta(days=400),
            arquivo_pdf=_pdf(),
            status='aprovado',
            data_validade=timezone.localdate() - timedelta(days=1),
            admin_aprovador=self.admin,
            data_decisao=timezone.now() - timedelta(days=366),
        )
        sincronizar_status_conta(self.usuario)
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.post('/api/reservas/', self._payload_reserva(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_usuario_inativo_envia_novo_termo(self):
        TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333336',
            cnh='44444444447',
            data_solicitacao=timezone.localdate() - timedelta(days=400),
            arquivo_pdf=_pdf('antigo.pdf'),
            status='aprovado',
            data_validade=timezone.localdate() - timedelta(days=1),
            admin_aprovador=self.admin,
            data_decisao=timezone.now() - timedelta(days=366),
        )
        sincronizar_status_conta(self.usuario)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

        self.client.force_authenticate(user=self.usuario)
        resp = self.client.post(
            '/api/termos/',
            {
                'entidade': 'SENAI',
                'cpf': '33333333336',
                'cnh': '12345678900',
                'arquivo_pdf': _pdf('novo.pdf'),
            },
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TermoResponsabilidade.objects.filter(usuario=self.usuario).count(), 2)
        novo = TermoResponsabilidade.objects.filter(usuario=self.usuario).latest('id')
        self.assertEqual(novo.status, 'pendente')

    def test_upload_termo_persiste_e_pode_ser_lido(self):
        from django.core.files.storage import default_storage

        self.client.force_authenticate(user=self.usuario)
        conteudo = b'%PDF-1.4 termo-assinado-teste'
        resp = self.client.post(
            '/api/termos/',
            {
                'entidade': 'SENAI',
                'cpf': '52998224725',
                'cnh': '12345678900',
                'data_solicitacao': (timezone.localdate() - timedelta(days=30)).isoformat(),
                'arquivo_pdf': SimpleUploadedFile(
                    'termo_assinado.pdf', conteudo, content_type='application/pdf'
                ),
            },
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data.get('arquivo_pdf_url'))
        termo = TermoResponsabilidade.objects.get(pk=resp.data['id'])
        self.assertEqual(termo.data_solicitacao, timezone.localdate())
        self.assertEqual(termo.data_solicitacao, timezone.localtime(termo.criado_em).date())
        self.assertTrue(default_storage.exists(termo.arquivo_pdf.name))
        with default_storage.open(termo.arquivo_pdf.name, 'rb') as fh:
            self.assertEqual(fh.read(), conteudo)
        media = self.client.get(termo.arquivo_pdf.url)
        self.assertEqual(media.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(media.streaming_content), conteudo)

    def test_gestor_aprova_termo_reativa_conta(self):
        termo = TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333337',
            cnh='44444444448',
            data_solicitacao=timezone.localdate(),
            arquivo_pdf=_pdf(),
            status='pendente',
        )
        self.usuario.is_active = False
        self.usuario.save()
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/termos/{termo.id}/decisao/',
            {'status': 'aprovado'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        termo.refresh_from_db()
        self.assertEqual(termo.status, 'aprovado')
        self.assertIsNotNone(termo.data_validade)
        self.assertEqual(termo.admin_aprovador_id, self.admin.id)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)

    def test_rejeicao_mantem_conta_inativa(self):
        termo = TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333338',
            cnh='44444444449',
            data_solicitacao=timezone.localdate(),
            arquivo_pdf=_pdf(),
            status='pendente',
        )
        self.usuario.is_active = False
        self.usuario.save()
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f'/api/termos/{termo.id}/decisao/',
            {'status': 'rejeitado', 'observacao_admin': 'Assinatura inválida'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        termo.refresh_from_db()
        self.assertEqual(termo.status, 'rejeitado')
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

    def test_historico_preservado(self):
        antigo = TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333339',
            cnh='44444444440',
            data_solicitacao=timezone.localdate() - timedelta(days=400),
            arquivo_pdf=_pdf('antigo.pdf'),
            status='aprovado',
            data_validade=timezone.localdate() - timedelta(days=1),
            admin_aprovador=self.admin,
            data_decisao=timezone.now() - timedelta(days=366),
        )
        novo = TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333339',
            cnh='44444444440',
            data_solicitacao=timezone.localdate(),
            arquivo_pdf=_pdf('novo.pdf'),
            status='aprovado',
            data_validade=timezone.localdate() + timedelta(days=VALIDADE_DIAS),
            admin_aprovador=self.admin,
            data_decisao=timezone.now(),
        )
        self.assertEqual(TermoResponsabilidade.objects.filter(usuario=self.usuario).count(), 2)
        self.assertNotEqual(antigo.id, novo.id)
        self.assertTrue(TermoResponsabilidade.objects.filter(pk=antigo.pk).exists())

    def test_usuario_comum_nao_aprova_termo(self):
        termo = TermoResponsabilidade.objects.create(
            usuario=self.usuario,
            entidade='SENAI',
            cpf='33333333330',
            cnh='44444444441',
            data_solicitacao=timezone.localdate(),
            arquivo_pdf=_pdf(),
            status='pendente',
        )
        self.client.force_authenticate(user=self.usuario)
        resp = self.client.patch(
            f'/api/termos/{termo.id}/decisao/',
            {'status': 'aprovado'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
