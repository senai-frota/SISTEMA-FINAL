from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from usuarios.permissions import AuthenticatedAndPasswordSet
from auditoria.services import registrar

from .models import TermoResponsabilidade, usuario_possui_termo_valido
from .serializers import (
    TermoResponsabilidadeSerializer, TermoCreateSerializer, TermoDecisaoSerializer
)
from .services_conta import resumo_termo_usuario, sincronizar_status_conta


class TermoListCreateView(generics.ListCreateAPIView):
    permission_classes = AuthenticatedAndPasswordSet
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TermoCreateSerializer
        return TermoResponsabilidadeSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = (
            TermoResponsabilidade.objects.all()
            if user.is_admin
            else TermoResponsabilidade.objects.filter(usuario=user)
        )
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.select_related('usuario', 'admin_aprovador')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        termo = serializer.save()
        registrar(
            ator=request.user,
            acao='enviar_termo',
            entidade='termo',
            entidade_id=termo.id,
            identificacao=f'Termo de {request.user.nome}',
            descricao=f'{request.user.nome} enviou um termo de responsabilidade.',
        )
        output = TermoResponsabilidadeSerializer(termo, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class TermoDetailView(generics.RetrieveAPIView):
    serializer_class = TermoResponsabilidadeSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return TermoResponsabilidade.objects.all()
        return TermoResponsabilidade.objects.filter(usuario=user)


class TermoDecisaoView(generics.UpdateAPIView):
    queryset = TermoResponsabilidade.objects.all()
    serializer_class = TermoDecisaoSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_object(self):
        obj = super().get_object()
        if obj.status != 'pendente':
            raise PermissionDenied(
                'Este Termo já foi analisado anteriormente.'
            )
        return obj

    def update(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem validar Termos de Responsabilidade.'
            )
        instance = self.get_object()
        if instance.usuario_id == request.user.id:
            raise PermissionDenied(
                'Você não pode aprovar o próprio termo.'
            )
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        aprovado = instance.status == 'aprovado'
        registrar(
            ator=request.user,
            acao='aprovar_termo' if aprovado else 'rejeitar_termo',
            entidade='termo',
            entidade_id=instance.id,
            identificacao=f'Termo de {instance.usuario.nome}',
            descricao=(
                f'O termo de {instance.usuario.nome} foi '
                f'{"aprovado" if aprovado else "rejeitado"}.'
            ),
            justificativa='' if aprovado else instance.observacao_admin,
            usuario_afetado=instance.usuario,
        )
        output = TermoResponsabilidadeSerializer(instance, context={'request': request})
        return Response(output.data)


@api_view(['GET'])
@permission_classes(AuthenticatedAndPasswordSet)
def meu_status(request):
    sincronizar_status_conta(request.user)
    termo = (
        TermoResponsabilidade.objects
        .filter(usuario=request.user)
        .order_by('-criado_em')
        .first()
    )
    historico = TermoResponsabilidade.objects.filter(usuario=request.user).order_by('-criado_em')[:10]
    resumo = resumo_termo_usuario(request.user)
    return Response({
        **resumo,
        'pode_reservar': (
            request.user.is_active
            and usuario_possui_termo_valido(request.user)
        ),
        'termo': TermoResponsabilidadeSerializer(termo, context={'request': request}).data
        if termo else None,
        'historico': TermoResponsabilidadeSerializer(
            historico, many=True, context={'request': request}
        ).data,
    })
