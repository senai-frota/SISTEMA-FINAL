import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { mensagemErroApi } from '../utils/erros'

function mensagemErroLogin(err, primeiroAcesso) {
  const status = err.response?.status
  if (status === 401 || status === 400) {
    return primeiroAcesso
      ? 'Não foi possível iniciar o primeiro acesso. Verifique a matrícula.'
      : 'Matrícula ou senha inválidas.'
  }
  return mensagemErroApi(err, 'Não foi possível concluir o login. Tente novamente.')
}

export default function Login() {
  const { login, user, precisaDefinirSenha, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [matricula, setMatricula] = useState('')
  const [password, setPassword] = useState('')
  const [senhaVisivel, setSenhaVisivel] = useState(false)
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
              <div className="password-field">
                <input
                  className="password-input"
                  type={senhaVisivel ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="icon-btn password-toggle"
                  aria-label={senhaVisivel ? 'Ocultar senha' : 'Mostrar senha'}
                  aria-pressed={senhaVisivel}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    setSenhaVisivel((v) => !v)
                  }}
                  disabled={loading}
                >
                  {senhaVisivel ? (
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        d="M3 3l18 18M10.5 10.6a3 3 0 0 0 4 3.9M9.9 5.1A10.5 10.5 0 0 1 12 4.8c5 0 9.3 3.1 11 7.2a11.3 11.3 0 0 1-4.1 4.8M6.6 6.6A11.4 11.4 0 0 0 1 12c1.2 2.7 3.4 4.9 6.1 6.1A11 11 0 0 0 12 19.2c1.1 0 2.2-.2 3.2-.5"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        d="M2 12s3.6-7.2 10-7.2S22 12 22 12s-3.6 7.2-10 7.2S2 12 2 12z"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinejoin="round"
                      />
                      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
                    </svg>
                  )}
                </button>
              </div>
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
              setSenhaVisivel(false)
            }}
          >
            {primeiroAcesso ? 'Já tenho senha' : 'Primeiro acesso (sem senha)'}
          </button>
        </form>
      </div>
    </div>
  )
}
