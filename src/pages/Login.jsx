import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function mensagemErroLogin(err, primeiroAcesso) {
  const status = err.response?.status
  const detail = err.response?.data

  if (detail != null) {
    if (typeof detail === 'string' && detail.trim()) return detail
    const fromFields =
      detail?.non_field_errors?.[0] ||
      (typeof detail?.detail === 'string' ? detail.detail : null) ||
      (Array.isArray(detail?.detail) ? detail.detail[0] : null)
    if (fromFields) return fromFields
  }

  if (status === 401 || status === 400) {
    return primeiroAcesso
      ? 'Não foi possível iniciar o primeiro acesso. Verifique a matrícula.'
      : 'Matrícula ou senha inválidas.'
  }

  if (!err.response) {
    return 'Não foi possível conectar ao servidor. Verifique a conexão e tente novamente.'
  }

  return 'Não foi possível concluir o login. Tente novamente.'
}

export default function Login() {
  const { login, user, precisaDefinirSenha, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [matricula, setMatricula] = useState('')
  const [password, setPassword] = useState('')
  const [primeiroAcesso, setPrimeiroAcesso] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const submittingRef = useRef(false)

  // Redireciona só quando o usuário já está no contexto (evita race com ProtectedRoute).
  useEffect(() => {
    if (authLoading || !user) return
    navigate(precisaDefinirSenha ? '/definir-senha' : '/', { replace: true })
  }, [authLoading, user, precisaDefinirSenha, navigate])

  async function handleSubmit(e) {
    e.preventDefault()
    if (submittingRef.current) return
    submittingRef.current = true
    setError('')
    setLoading(true)
    try {
      const result = await login(matricula, primeiroAcesso ? '' : password)
      if (!result?.perfil) {
        setError(
          'Login autenticado, mas não foi possível carregar o perfil. Tente novamente.'
        )
        setLoading(false)
        submittingRef.current = false
        return
      }
      // Mantém loading até o useEffect redirecionar com `user` já definido.
    } catch (err) {
      setError(mensagemErroLogin(err, primeiroAcesso))
      setLoading(false)
      submittingRef.current = false
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
          <h2>{primeiroAcesso ? 'Primeiro acesso' : 'Entrar'}</h2>
          <p className="login-subtitle">
            {primeiroAcesso
              ? 'Informe apenas a matrícula cadastrada pelo administrador para criar sua senha.'
              : 'Use a matrícula e a senha definidas no primeiro acesso.'}
          </p>

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
              disabled={loading}
            />
          </label>

          {!primeiroAcesso && (
            <label className="field">
              <span>Senha</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={loading}
              />
            </label>
          )}

          {error && <div className="form-error">{error}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={loading}>
            {loading ? 'Entrando…' : primeiroAcesso ? 'Continuar' : 'Entrar'}
          </button>

          <button
            type="button"
            className="btn btn-ghost btn-block"
            disabled={loading}
            onClick={() => {
              setPrimeiroAcesso((v) => !v)
              setError('')
              setPassword('')
            }}
          >
            {primeiroAcesso ? 'Já tenho senha' : 'Primeiro acesso (sem senha)'}
          </button>
        </form>
      </div>
    </div>
  )
}
