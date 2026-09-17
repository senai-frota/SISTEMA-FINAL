import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [matricula, setMatricula] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(matricula, password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      const status = err.response?.status
      setError(
        status === 401
          ? 'Matrícula ou senha inválidas.'
          : 'Não foi possível entrar. Verifique sua conexão e tente novamente.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <div className="login-side">
        <div className="login-side-content">
          <span className="brand-mark brand-mark-lg">S</span>
          <h1>Frota SENAI</h1>
          <p>Solicite, aprove e acompanhe o uso dos veículos da unidade em um só lugar.</p>
        </div>
      </div>

      <div className="login-form-wrap">
        <form className="login-form" onSubmit={handleSubmit}>
          <h2>Entrar</h2>
          <p className="login-subtitle">Use a matrícula e senha cadastradas pelo administrador.</p>

          <label className="field">
            <span>Matrícula</span>
            <input
              type="text"
              inputMode="numeric"
              autoFocus
              value={matricula}
              onChange={(e) => setMatricula(e.target.value)}
              placeholder="Ex.: 12345"
              required
            />
          </label>

          <label className="field">
            <span>Senha</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </label>

          {error && <div className="form-error">{error}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
