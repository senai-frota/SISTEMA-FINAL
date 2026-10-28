"""Filtros compartilhados pelos indicadores e pela exportação."""
from dataclasses import dataclass
from datetime import date

from django.utils.dateparse import parse_date
from rest_framework import serializers

from reservas.models import Reserva
from usuarios.models import Usuario
from veiculos.models import Veiculo

STATUS_RESERVA = dict(Reserva.STATUS_CHOICES)
TURNOS = dict(Reserva.TURNO_CHOICES)


@dataclass(frozen=True)
class FiltrosRelatorio:
    de: date | None = None
    ate: date | None = None
    veiculo: Veiculo | None = None
    usuario: Usuario | None = None
    status: str = ''
    turno: str = ''

    def como_dict(self):
        """Representação legível (auditoria e aba Resumo)."""
        return {
            'de': self.de.isoformat() if self.de else None,
            'ate': self.ate.isoformat() if self.ate else None,
            'veiculo': self.veiculo.placa if self.veiculo else None,
            'usuario': (
                f'{self.usuario.nome} ({self.usuario.matricula})' if self.usuario else None
            ),
            'status': STATUS_RESERVA.get(self.status) if self.status else None,
            'turno': TURNOS.get(self.turno) if self.turno else None,
        }

    # --- aplicação por conjunto de dados -------------------------------

    def _periodo(self, qs, campo):
        if self.de:
            qs = qs.filter(**{f'{campo}__date__gte': self.de})
        if self.ate:
            qs = qs.filter(**{f'{campo}__date__lte': self.ate})
        return qs

    def reservas(self, qs):
        qs = self._periodo(qs, 'data_inicio')
        if self.veiculo:
            qs = qs.filter(veiculo=self.veiculo)
        if self.usuario:
            qs = qs.filter(usuario=self.usuario)
        if self.status:
            qs = qs.filter(status=self.status)
        if self.turno:
            qs = qs.filter(modalidade='turno', turno=self.turno)
        return qs

    def vistorias(self, qs):
        """Vistorias do período cujas reservas atendem aos demais filtros."""
        qs = self._periodo(qs, 'data_hora')
        if self.veiculo:
            qs = qs.filter(reserva__veiculo=self.veiculo)
        if self.usuario:
            qs = qs.filter(reserva__usuario=self.usuario)
        if self.status:
            qs = qs.filter(reserva__status=self.status)
        if self.turno:
            qs = qs.filter(reserva__modalidade='turno', reserva__turno=self.turno)
        return qs

    def documentos(self, qs):
        """Termos e CNHs: enviados no período, do usuário filtrado."""
        qs = self._periodo(qs, 'criado_em')
        if self.usuario:
            qs = qs.filter(usuario=self.usuario)
        return qs

    def usuarios(self, qs):
        if self.usuario:
            qs = qs.filter(pk=self.usuario.pk)
        return qs

    def veiculos(self, qs):
        if self.veiculo:
            qs = qs.filter(pk=self.veiculo.pk)
        return qs

    def auditoria(self, qs):
        from django.db.models import Q

        qs = self._periodo(qs, 'criado_em')
        if self.usuario:
            qs = qs.filter(Q(ator_id=self.usuario.pk) | Q(usuario_afetado_id=self.usuario.pk))
        return qs


def _data(params, campo, erros):
    bruto = (params.get(campo) or '').strip()
    if not bruto:
        return None
    try:
        valor = parse_date(bruto)
    except ValueError:
        valor = None
    if valor is None:
        erros[campo] = ['Data inválida. Use o formato AAAA-MM-DD.']
    return valor


def _objeto(params, campo, modelo, erros, rotulo):
    bruto = (params.get(campo) or '').strip()
    if not bruto:
        return None
    try:
        return modelo.objects.get(pk=int(bruto))
    except (ValueError, modelo.DoesNotExist):
        erros[campo] = [f'{rotulo} não encontrado.']
        return None


def ler_filtros(params):
    """Valida os parâmetros de consulta; valores inválidos geram 400 com mensagem clara."""
    erros = {}
    de = _data(params, 'de', erros)
    ate = _data(params, 'ate', erros)
    if de and ate and de > ate:
        erros['ate'] = ['A data final deve ser igual ou posterior à data inicial.']

    veiculo = _objeto(params, 'veiculo', Veiculo, erros, 'Veículo')
    usuario = _objeto(params, 'usuario', Usuario, erros, 'Usuário')

    status = (params.get('status') or '').strip()
    if status and status not in STATUS_RESERVA:
        erros['status'] = ['Status de reserva inválido.']
    turno = (params.get('turno') or '').strip()
    if turno and turno not in TURNOS:
        erros['turno'] = ['Turno inválido.']

    if erros:
        raise serializers.ValidationError(erros)
    return FiltrosRelatorio(
        de=de, ate=ate, veiculo=veiculo, usuario=usuario, status=status, turno=turno,
    )
