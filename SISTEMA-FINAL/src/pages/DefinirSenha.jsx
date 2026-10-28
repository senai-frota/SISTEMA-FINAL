import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { errosParaFormulario, textoCampo } from '../utils/erros'

export default function DefinirSenha() {
  const { user, loadPerfil, logout } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    if (password !== passwordConfirm) {
      setErrors({ password_confirm: ['A confirmação não confere com a senha.'] })
      return
    }
    setSaving(true)
    try {
      await api.post('/usuarios/definir-senha/', {
        password,
        password_confirm: passwordConfirm,
      })
      await loadPerfil()
      navigate('/', { replace: true })
    } catch (err) {
      setErrors(errosParaFormulario(err, 'Não foi possível definir a senha.'))
    } finally {
      setSaving(false)
    }
  }

  const tipo = mostrar ? 'text' : 'password'
  const erroGeral = textoCampo(errors, 'non_field_errors') || textoCampo(errors, 'detail')

  return (
    <div className="login-screen">
      <div className="login-side">
        <div className="login-side-content">
          <span className="brand-mark brand-mark-lg">S</span>
          <h1>Frota SENAI</h1>
          <p>Defina sua senha para concluir o primeiro acesso.</p>
        </div>
      </div>

      <div className="login-form-wrap">
        <form className="login-form" onSubmit={handleSubmit}>
          <h2>Definir senha</h2>
          <p className="login-subtitle">
            Olá{user?.nome ? `, ${user.nome.split(' ')[0]}` : ''}. Crie uma senha segura para a
            matrícula <strong>{user?.matricula}</strong>.
          </p>
          <p className="muted-note">
            A senha deve ter pelo menos 8 caracteres, não pode ser só números nem uma senha comum, e
            não deve se parecer com o nome ou a matrícula.
          </p>

          <label className="field">
            <span>Nova senha</span>
            <div className="password-field">
              <input
                className="password-input"
                type={tipo}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoFocus
                autoComplete="new-password"
              />
              <button
                type="button"
                className="icon-btn password-toggle"
                aria-label={mostrar ? 'Ocultar senha' : 'Mostrar senha'}
                aria-pressed={mostrar}
                onClick={() => setMostrar((v) => !v)}
              >
                {mostrar ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>
            {textoCampo(errors, 'password') && (
              <small className="field-error">{textoCampo(errors, 'password')}</small>
            )}
          </label>

          <label className="field">
            <span>Confirmar senha</span>
            <input
              type={tipo}
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
            {textoCampo(errors, 'password_confirm') && (
              <small className="field-error">{textoCampo(errors, 'password_confirm')}</small>
            )}
          </label>

          {erroGeral && <div className="form-error">{erroGeral}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={saving}>
            {saving ? 'Salvando…' : 'Confirmar senha'}
          </button>

          <button
            type="button"
            className="btn btn-ghost btn-block"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            Sair
          </button>
        </form>
      </div>
    </div>
  )
}
