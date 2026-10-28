from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAdmin(BasePermission):
    message = 'Apenas administradores podem realizar esta ação.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_admin', False)
        )


class ExigeSenhaDefinida(BasePermission):
    """
    Bloqueia o uso da API enquanto o usuário estiver em primeiro acesso
    (ainda precisa definir senha), exceto nas views marcadas com
    allow_primeiro_acesso = True e rotas de autenticação.
    """

    message = 'É necessário definir sua senha antes de continuar.'

    PATHS_LIBERADOS = (
        '/api/usuarios/login',
        '/api/usuarios/refresh',
        '/api/usuarios/definir-senha',
        '/api/usuarios/perfil',
    )

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True
        if not getattr(user, 'precisa_definir_senha', False):
            return True
        if getattr(view, 'allow_primeiro_acesso', False):
            return True
        path = request.path.rstrip('/')
        return any(path == liberado or path.startswith(liberado + '/') for liberado in self.PATHS_LIBERADOS)


# Use nas views no lugar de [IsAuthenticated] para não sobrescrever a regra de primeiro acesso.
AuthenticatedAndPasswordSet = [IsAuthenticated, ExigeSenhaDefinida]
