import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function DefinirSenha() {
  const { user, loadPerfil, logout } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
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
      const data = err.response?.data
      if (data && typeof data === 'object') {
        setErrors(data)
      } else {
        setErrors({ non_field_errors: ['Não foi possível definir a senha.'] })
      }
    } finally {
      setSaving(false)
    }
  }

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

          <label className="field">
            <span>Nova senha</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoFocus
            />
            {errors.password && (
              <small className="field-error">
                {Array.isArray(errors.password) ? errors.password[0] : errors.password}
              </small>
            )}
          </label>

          <label className="field">
            <span>Confirmar senha</span>
            <input
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              minLength={6}
            />
            {errors.password_confirm && (
              <small className="field-error">
                {Array.isArray(errors.password_confirm)
                  ? errors.password_confirm[0]
                  : errors.password_confirm}
              </small>
            )}
          </label>

          {(errors.non_field_errors || errors.detail) && (
            <div className="form-error">
              {errors.non_field_errors?.[0] || errors.detail}
            </div>
          )}

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
