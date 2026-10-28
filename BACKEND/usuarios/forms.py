from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Usuario


class UsuarioCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput,
        help_text='Defina uma senha forte para o usuário.'
    )
    password2 = forms.CharField(
        label='Confirmação de senha',
        widget=forms.PasswordInput
    )

    class Meta:
        model = Usuario
        fields = ('matricula', 'nome', 'email', 'telefone', 'setor', 'is_admin', 'is_active')

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p1 != p2:
            raise forms.ValidationError('As senhas não conferem.')
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UsuarioChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label='Senha',
        help_text='Senhas não são exibidas aqui. Use o botão "Alterar senha" no canto superior direito.'
    )

    class Meta:
        model = Usuario
        fields = (
            'matricula', 'nome', 'email', 'telefone', 'setor',
            'password', 'is_admin', 'is_active',
            'is_superuser', 'groups', 'user_permissions'
        )

    def clean_password(self):
        return self.initial.get('password')
