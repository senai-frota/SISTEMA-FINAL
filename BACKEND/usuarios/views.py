from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes

from termos.models import TermoResponsabilidade
from termos.services_conta import situacao_termo
from .models import DocumentoCNH, resumo_cnh_usuario, CNH_DIAS_ALERTA_VENCIMENTO
from .serializers import (
    UsuarioSerializer, UsuarioCreateSerializer,
    UsuarioUpdateSerializer, PerfilSerializer,
    DocumentoCNHSerializer, DocumentoCNHCreateSerializer,
    DocumentoCNHDecisaoSerializer,
)
from .auth import (
    CustomTokenObtainPairSerializer,
    DefinirSenhaSerializer,
    RedefinirSenhaAdminSerializer,
)
from auditoria.services import registrar
from .permissions import AuthenticatedAndPasswordSet, IsAdmin

Usuario = get_user_model()


def _inclui_inativos(request):
    return (request.query_params.get('incluir_inativos') or '').lower() in ('1', 'true', 'sim')


def _lista_param(request, nome):
    valor = request.query_params.get(nome) or ''
    return {item.strip() for item in valor.split(',') if item.strip()}


class PendenciasAdminView(APIView):
    """
    GET /api/usuarios/pendencias/ — contadores do painel administrativo.

    CNH considera funcionários ativos; Termo considera todos os funcionários,
    porque termo vencido ou rejeitado é o que inativa a conta. Admins ficam fora.
    """
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def get(self, request):
        funcionarios = Usuario.objects.filter(is_admin=False)

        cnh = {'vencida': 0, 'proxima_vencimento': 0, 'regularizar': 0}
        for usuario in funcionarios.filter(is_active=True):
            situacao = resumo_cnh_usuario(usuario)['situacao']
            if situacao in ('vencida', 'proxima_vencimento'):
                cnh[situacao] += 1
            elif situacao in ('sem_cnh', 'rejeitada'):
                cnh['regularizar'] += 1

        termo = {'vencido': 0, 'regularizar': 0}
        for usuario in funcionarios:
            situacao, _ = situacao_termo(usuario)
            if situacao == 'vencido':
                termo['vencido'] += 1
            elif situacao in ('sem_termo', 'rejeitado'):
                termo['regularizar'] += 1

        return Response({
            'cnh': {
                'pendentes_analise': DocumentoCNH.objects.filter(
                    status='pendente', usuario__is_admin=False,
                ).count(),
                'vencidas': cnh['vencida'],
                'proximas_vencimento': cnh['proxima_vencimento'],
                'sem_cnh_valida': cnh['regularizar'],
                'dias_alerta': CNH_DIAS_ALERTA_VENCIMENTO,
            },
            'termo': {
                'pendentes_analise': TermoResponsabilidade.objects.filter(
                    status='pendente', usuario__is_admin=False,
                ).count(),
                'vencidos': termo['vencido'],
                'sem_termo_valido': termo['regularizar'],
            },
            'contas_inativas': funcionarios.filter(is_active=False).count(),
        })


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class PerfilView(APIView):
    """
    GET /api/usuarios/perfil/
    Retorna os dados do usuário autenticado (inclui resumo da CNH).
    """
    permission_classes = AuthenticatedAndPasswordSet
    allow_primeiro_acesso = True

    def get(self, request):
        serializer = PerfilSerializer(request.user)
        return Response(serializer.data)


class DefinirSenhaView(APIView):
    """
    POST /api/usuarios/definir-senha/
    Define a senha no primeiro acesso.
    """
    permission_classes = AuthenticatedAndPasswordSet
    allow_primeiro_acesso = True

    def post(self, request):
        if not request.user.precisa_definir_senha:
            return Response(
                {'detail': 'Sua senha já foi definida.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = DefinirSenhaSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        registrar(
            ator=request.user,
            acao='definir_senha',
            entidade='usuario',
            entidade_id=request.user.id,
            identificacao=f'{request.user.nome} ({request.user.matricula})',
            descricao=f'{request.user.nome} definiu a senha de acesso.',
        )
        return Response({
            'detail': 'Senha definida com sucesso.',
            'precisa_definir_senha': False,
            'perfil': PerfilSerializer(request.user).data,
        })


class RedefinirSenhaAdminView(APIView):
    """
    POST /api/usuarios/<id>/redefinir-senha/
    Administrador redefine a senha. Não altera matrícula, perfil nem privilégios.
    """
    permission_classes = [*AuthenticatedAndPasswordSet, IsAdmin]

    def post(self, request, pk):
        try:
            alvo = Usuario.objects.get(pk=pk)
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Usuário não encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = RedefinirSenhaAdminSerializer(
            data=request.data,
            context={'request': request, 'alvo': alvo},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        registrar(
            ator=request.user,
            acao='definir_senha',
            entidade='usuario',
            entidade_id=alvo.id,
            identificacao=f'{alvo.nome} ({alvo.matricula})',
            descricao=f'A senha de {alvo.nome} foi redefinida pelo administrador.',
            usuario_afetado=alvo,
        )
        return Response({'detail': 'Senha redefinida com sucesso.'})


class UsuarioListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/usuarios/        -> Lista usuários (admin)
    POST /api/usuarios/        -> Cria usuário (admin)
    """
    queryset = Usuario.objects.all()
    permission_classes = AuthenticatedAndPasswordSet

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def get_queryset(self):
        queryset = Usuario.objects.all()
        ativo = self.request.query_params.get('ativo')
        setor = self.request.query_params.get('setor')
        cnh_situacoes = _lista_param(self.request, 'cnh_situacao')
        termo_situacoes = _lista_param(self.request, 'termo_situacao')
        if ativo is not None:
            queryset = queryset.filter(is_active=ativo.lower() == 'true')
        elif not _inclui_inativos(self.request):
            queryset = queryset.filter(is_active=True)
        if setor:
            queryset = queryset.filter(setor__icontains=setor)
        # Filtros de CNH/Termo reutilizam as regras de situação, aplicadas em
        # memória; admins não possuem CNH nem Termo e ficam fora do resultado.
        if cnh_situacoes:
            ids = [
                u.id for u in queryset.filter(is_admin=False)
                if resumo_cnh_usuario(u)['situacao'] in cnh_situacoes
            ]
            queryset = queryset.filter(id__in=ids)
        if termo_situacoes:
            ids = [
                u.id for u in queryset.filter(is_admin=False)
                if situacao_termo(u)[0] in termo_situacoes
            ]
            queryset = queryset.filter(id__in=ids)
        return queryset

    def list(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem listar usuários.'
            )
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        if not self.request.user.is_admin:
            raise PermissionDenied('Apenas administradores podem criar usuários.')
        usuario = serializer.save()
        registrar(
            ator=self.request.user,
            acao='criar_usuario',
            entidade='usuario',
            entidade_id=usuario.id,
            identificacao=f'{usuario.nome} ({usuario.matricula})',
            descricao=(
                f'Usuário {usuario.nome} (matrícula {usuario.matricula}) foi cadastrado '
                f'como {"administrador" if usuario.is_admin else "funcionário"}.'
            ),
            detalhes={
                'perfil': 'administrador' if usuario.is_admin else 'funcionario',
                'setor': usuario.setor or '',
            },
        )


class UsuarioDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/usuarios/<id>/  -> Detalhes do usuário
    PATCH  /api/usuarios/<id>/  -> Atualiza usuário
    DELETE /api/usuarios/<id>/  -> Remove usuário
    """
    queryset = Usuario.objects.all()
    serializer_class = UsuarioUpdateSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_object(self):
        obj = super().get_object()
        if not self.request.user.is_admin and obj.id != self.request.user.id:
            raise PermissionDenied(
                'Você não tem permissão para acessar este usuário.'
            )
        return obj

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UsuarioSerializer
        return UsuarioUpdateSerializer

    def perform_destroy(self, instance):
        if not self.request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem remover usuários.'
            )
        if instance.pk == self.request.user.pk:
            raise PermissionDenied(
                'Você não pode remover a própria conta.'
            )
        # Soft-delete: inativa o usuário e preserva o histórico relacionado.
        if not instance.is_active:
            return
        instance.is_active = False
        instance.save(update_fields=['is_active', 'atualizado_em'])
        registrar(
            ator=self.request.user,
            acao='inativar_usuario',
            entidade='usuario',
            entidade_id=instance.id,
            identificacao=f'{instance.nome} ({instance.matricula})',
            descricao=f'A conta de {instance.nome} (matrícula {instance.matricula}) foi desativada.',
        )

    def perform_update(self, serializer):
        anterior = serializer.instance
        campos = {}
        for campo in ('nome', 'email', 'telefone', 'setor', 'is_active'):
            if campo not in serializer.validated_data:
                continue
            if serializer.validated_data[campo] != getattr(anterior, campo):
                campos[campo] = serializer.validated_data[campo]
        serializer.save()
        if not campos:
            return
        usuario = serializer.instance
        if 'is_active' in campos and len(campos) == 1:
            acao = 'ativar_usuario' if usuario.is_active else 'inativar_usuario'
            efeito = 'ativada' if usuario.is_active else 'desativada'
            descricao = f'A conta de {usuario.nome} foi {efeito}.'
        elif 'is_active' in campos:
            acao = 'ativar_usuario' if usuario.is_active else 'inativar_usuario'
            descricao = f'A conta de {usuario.nome} foi atualizada.'
        else:
            acao = 'alterar_usuario'
            descricao = f'Os dados de {usuario.nome} foram atualizados.'
        rotulos = {
            'nome': 'nome',
            'email': 'e-mail',
            'telefone': 'telefone',
            'setor': 'setor',
            'is_active': 'situação da conta',
        }
        registrar(
            ator=self.request.user,
            acao=acao,
            entidade='usuario',
            entidade_id=usuario.id,
            identificacao=f'{usuario.nome} ({usuario.matricula})',
            descricao=descricao,
            detalhes={'campos': [rotulos.get(campo, campo) for campo in sorted(campos)]},
        )


class MeuStatusCNHView(APIView):
    """GET /api/usuarios/cnh/meu-status/"""
    permission_classes = AuthenticatedAndPasswordSet

    def get(self, request):
        resumo = resumo_cnh_usuario(request.user)
        vigente = None
        pendente = None
        docs = DocumentoCNH.objects.filter(usuario=request.user).order_by('-criado_em')[:5]
        for doc in docs:
            if doc.status == 'aprovado' and vigente is None and not doc.esta_vencida:
                vigente = doc
            if doc.status == 'pendente' and pendente is None:
                pendente = doc
        return Response({
            **resumo,
            'vigente': DocumentoCNHSerializer(vigente, context={'request': request}).data if vigente else None,
            'pendente': DocumentoCNHSerializer(pendente, context={'request': request}).data if pendente else None,
        })


class DocumentoCNHListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/usuarios/cnh/  -> Admin: lista (filtro ?status=pendente);
                                usuário: só as próprias.
    POST /api/usuarios/cnh/  -> Usuário envia nova CNH (multipart).
    """
    permission_classes = AuthenticatedAndPasswordSet
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DocumentoCNHCreateSerializer
        return DocumentoCNHSerializer

    def get_queryset(self):
        user = self.request.user
        qs = DocumentoCNH.objects.all() if user.is_admin else DocumentoCNH.objects.filter(usuario=user)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.select_related('usuario', 'admin_aprovador')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()
        registrar(
            ator=request.user,
            acao='enviar_cnh',
            entidade='cnh',
            entidade_id=doc.id,
            identificacao=f'CNH de {request.user.nome}',
            descricao=f'{request.user.nome} enviou uma CNH para análise.',
        )
        output = DocumentoCNHSerializer(doc, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class DocumentoCNHDecisaoView(generics.UpdateAPIView):
    """PATCH /api/usuarios/cnh/<id>/decisao/ — somente admin."""
    queryset = DocumentoCNH.objects.all()
    serializer_class = DocumentoCNHDecisaoSerializer
    permission_classes = AuthenticatedAndPasswordSet

    def get_object(self):
        obj = super().get_object()
        if obj.status != 'pendente':
            raise PermissionDenied('Este documento já foi analisado.')
        return obj

    def update(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied(
                'Apenas administradores podem aprovar ou rejeitar CNH.'
            )
        instance = self.get_object()
        if instance.usuario_id == request.user.id:
            raise PermissionDenied('Você não pode aprovar a própria CNH.')
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        acao = 'aprovar_cnh' if instance.status == 'aprovado' else 'rejeitar_cnh'
        resultado = 'aprovada' if instance.status == 'aprovado' else 'rejeitada'
        registrar(
            ator=request.user,
            acao=acao,
            entidade='cnh',
            entidade_id=instance.id,
            identificacao=f'CNH de {instance.usuario.nome}',
            descricao=f'A CNH de {instance.usuario.nome} foi {resultado}.',
            justificativa='' if instance.status == 'aprovado' else instance.observacao_admin,
            usuario_afetado=instance.usuario,
        )
        output = DocumentoCNHSerializer(instance, context={'request': request})
        return Response(output.data)


@api_view(['GET'])
@permission_classes(AuthenticatedAndPasswordSet)
def documento_cnh_detail(request, pk):
    """GET /api/usuarios/cnh/<id>/ — dono ou admin."""
    try:
        doc = DocumentoCNH.objects.get(pk=pk)
    except DocumentoCNH.DoesNotExist:
        return Response({'detail': 'Documento não encontrado.'}, status=404)
    if not request.user.is_admin and doc.usuario_id != request.user.id:
        return Response({'detail': 'Sem permissão.'}, status=403)
    return Response(DocumentoCNHSerializer(doc, context={'request': request}).data)
