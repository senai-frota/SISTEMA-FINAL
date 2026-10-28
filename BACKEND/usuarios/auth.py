from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


Usuario = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Autenticação por matrícula + senha.
    Em primeiro acesso (precisa_definir_senha e senha ainda não definida),
    permite login apenas com a matrícula (senha vazia).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = True
        if 'password' in self.fields:
            self.fields['password'].required = False
            self.fields['password'].allow_blank = True

    def validate(self, attrs):
        matricula = attrs.get(self.username_field)
        password = attrs.get('password') or ''

        try:
            user = Usuario.objects.get(**{self.username_field: matricula})
        except Usuario.DoesNotExist:
            raise self._auth_error()

        if user.precisa_definir_senha and not user.has_usable_password():
            if password:
                raise self._auth_error()
        elif not user.check_password(password):
            raise self._auth_error()

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'precisa_definir_senha': bool(user.precisa_definir_senha),
            'is_admin': bool(user.is_admin),
            'matricula': user.matricula,
            'nome': user.nome,
        }

    def _auth_error(self):
        return serializers.ValidationError(
            'Usuário ou senha inválidos.',
            code='authorization',
        )


def user_authentication_rule(user):
    """Aceita usuário autenticado mesmo se is_active=False."""
    return user is not None


class DefinirSenhaSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': ['A confirmação não confere com a senha.'],
            })
        validate_password(attrs['password'], user=self.context['request'].user)
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.definir_senha(self.validated_data['password'])
        return user


class RedefinirSenhaAdminSerializer(serializers.Serializer):
    """Administrador redefine a senha de outro usuário. Não altera perfil nem privilégios."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': ['A confirmação não confere com a senha.'],
            })
        validate_password(attrs['password'], user=self.context['alvo'])
        return attrs

    def save(self, **kwargs):
        alvo = self.context['alvo']
        alvo.definir_senha(self.validated_data['password'])
        return alvo
