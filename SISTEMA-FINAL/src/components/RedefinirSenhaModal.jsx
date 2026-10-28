import { useState } from 'react'
import api from '../services/api'
import Modal from './Modal'
import { errosParaFormulario, textoCampo } from '../utils/erros'
import { useFeedback } from '../context/FeedbackContext'

export default function RedefinirSenhaModal({ usuario, onClose, onSaved }) {
  const feedback = useFeedback()
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
      await api.post(`/usuarios/${usuario.id}/redefinir-senha/`, {
        password,
        password_confirm: passwordConfirm,
      })
      feedback.sucesso(`Senha de ${usuario.nome} redefinida.`)
      onSaved()
    } catch (err) {
      setErrors(errosParaFormulario(err, 'Não foi possível redefinir a senha.'))
    } finally {
      setSaving(false)
    }
  }

  const tipo = mostrar ? 'text' : 'password'
  const erroGeral = textoCampo(errors, 'non_field_errors') || textoCampo(errors, 'detail')

  return (
    <Modal title="Redefinir senha" onClose={onClose} width={440}>
      <form onSubmit={handleSubmit} className="form-grid">
        <p className="muted-note">
          {usuario.nome} · matrícula {usuario.matricula}. A senha atual não é exibida e não é
          necessária. O usuário passa a entrar com a nova senha.
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
              autoComplete="new-password"
              autoFocus
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

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Salvando…' : 'Redefinir senha'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
