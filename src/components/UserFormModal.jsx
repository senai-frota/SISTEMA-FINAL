import { useState } from 'react'
import api from '../services/api'
import Modal from './Modal'

const empty = {
  matricula: '',
  nome: '',
  email: '',
  telefone: '',
  setor: '',
  password: '',
  is_admin: false,
  is_active: true,
}

export default function UserFormModal({ usuario, onClose, onSaved }) {
  const [form, setForm] = useState(usuario ? { ...empty, ...usuario, password: '' } : empty)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setErrors({})
    try {
      if (usuario) {
        // A edição só aceita nome, e-mail, telefone, setor e status ativo.
        const { nome, email, telefone, setor, is_active } = form
        await api.patch(`/usuarios/${usuario.id}/`, { nome, email, telefone, setor, is_active })
      } else {
        await api.post('/usuarios/', form)
      }
      onSaved()
    } catch (err) {
      if (err.response?.data && typeof err.response.data === 'object') {
        setErrors(err.response.data)
      } else {
        setErrors({ non_field_errors: ['Não foi possível salvar. Tente novamente.'] })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title={usuario ? 'Editar usuário' : 'Novo usuário'} onClose={onClose} width={520}>
      <form onSubmit={handleSubmit} className="form-grid">
        <div className="field-row">
          <label className="field">
            <span>Matrícula</span>
            <input
              value={form.matricula}
              onChange={(e) => update('matricula', e.target.value)}
              required
              disabled={!!usuario}
            />
            {errors.matricula && <small className="field-error">{errors.matricula[0]}</small>}
          </label>
          <label className="field">
            <span>Nome completo</span>
            <input value={form.nome} onChange={(e) => update('nome', e.target.value)} required />
          </label>
        </div>

        <div className="field-row">
          <label className="field">
            <span>E-mail</span>
            <input
              type="email"
              value={form.email || ''}
              onChange={(e) => update('email', e.target.value)}
            />
          </label>
          <label className="field">
            <span>Telefone</span>
            <input value={form.telefone || ''} onChange={(e) => update('telefone', e.target.value)} />
          </label>
        </div>

        <label className="field">
          <span>Setor</span>
          <input value={form.setor || ''} onChange={(e) => update('setor', e.target.value)} />
        </label>

        {!usuario && (
          <>
            <label className="field">
              <span>Senha</span>
              <input
                type="password"
                value={form.password}
                onChange={(e) => update('password', e.target.value)}
                required
              />
              {errors.password && <small className="field-error">{errors.password[0]}</small>}
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={form.is_admin}
                onChange={(e) => update('is_admin', e.target.checked)}
              />
              <span>Administrador (acesso total ao sistema)</span>
            </label>
          </>
        )}

        {usuario && (
          <p className="muted-note">
            Senha e perfil (administrador/funcionário) não podem ser alterados aqui — apenas na
            criação do usuário.
          </p>
        )}

        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => update('is_active', e.target.checked)}
          />
          <span>Usuário ativo</span>
        </label>

        {errors.non_field_errors && (
          <div className="form-error">{errors.non_field_errors[0]}</div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Salvando…' : 'Salvar usuário'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
