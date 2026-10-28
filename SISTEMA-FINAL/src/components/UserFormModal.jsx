import { useState } from 'react'
import api from '../services/api'
import Modal from './Modal'
import { errosParaFormulario, textoCampo } from '../utils/erros'
import { useFeedback } from '../context/FeedbackContext'

const empty = {
  matricula: '',
  nome: '',
  email: '',
  telefone: '',
  setor: '',
  is_admin: false,
  is_active: true,
}

export default function UserFormModal({ usuario, onClose, onSaved }) {
  const feedback = useFeedback()
  const [form, setForm] = useState(usuario ? { ...empty, ...usuario } : empty)
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
        const { nome, email, telefone, setor, is_active } = form
        await api.patch(`/usuarios/${usuario.id}/`, { nome, email, telefone, setor, is_active })
        feedback.sucesso('Usuário atualizado.')
      } else {
        const { matricula, nome, email, telefone, setor, is_admin, is_active } = form
        await api.post('/usuarios/', {
          matricula,
          nome,
          email,
          telefone,
          setor,
          is_admin,
          is_active,
        })
        feedback.sucesso('Usuário cadastrado. A senha será definida no primeiro acesso.')
      }
      onSaved()
    } catch (err) {
      setErrors(errosParaFormulario(err, 'Não foi possível salvar o usuário. Tente novamente.'))
    } finally {
      setSaving(false)
    }
  }

  const erroGeral = textoCampo(errors, 'non_field_errors') || textoCampo(errors, 'detail')

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
            {textoCampo(errors, 'matricula') && (
              <small className="field-error">{textoCampo(errors, 'matricula')}</small>
            )}
          </label>
          <label className="field">
            <span>Nome completo</span>
            <input value={form.nome} onChange={(e) => update('nome', e.target.value)} required />
            {textoCampo(errors, 'nome') && (
              <small className="field-error">{textoCampo(errors, 'nome')}</small>
            )}
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
            {textoCampo(errors, 'email') && (
              <small className="field-error">{textoCampo(errors, 'email')}</small>
            )}
          </label>
          <label className="field">
            <span>Telefone</span>
            <input value={form.telefone || ''} onChange={(e) => update('telefone', e.target.value)} />
            {textoCampo(errors, 'telefone') && (
              <small className="field-error">{textoCampo(errors, 'telefone')}</small>
            )}
          </label>
        </div>

        <label className="field">
          <span>Setor</span>
          <input value={form.setor || ''} onChange={(e) => update('setor', e.target.value)} />
          {textoCampo(errors, 'setor') && (
            <small className="field-error">{textoCampo(errors, 'setor')}</small>
          )}
        </label>

        {!usuario && (
          <>
            <p className="muted-note">
              O próprio usuário cria a senha no primeiro acesso, usando a matrícula.
            </p>

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
            Perfil e senha não são alterados neste formulário. Use a ação “Redefinir senha” na lista.
            {usuario.precisa_definir_senha
              ? ' Este usuário ainda precisa concluir o primeiro acesso.'
              : ''}
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

        {erroGeral && <div className="form-error">{erroGeral}</div>}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
