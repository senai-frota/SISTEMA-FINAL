import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadPerfil = useCallback(async () => {
    try {
      const { data } = await api.get('/usuarios/perfil/')
      setUser(data)
      return data
    } catch {
      setUser(null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      loadPerfil()
    } else {
      setLoading(false)
    }
  }, [loadPerfil])

  async function login(matricula, password = '') {
    setLoading(true)
    try {
      const { data } = await api.post('/usuarios/login/', {
        matricula,
        password: password || '',
      })
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)

      const { data: perfil } = await api.get('/usuarios/perfil/')
      if (!perfil) {
        throw new Error('PERFIL_INDISPONIVEL')
      }

      setUser(perfil)
      return {
        ...data,
        perfil,
        precisa_definir_senha:
          data.precisa_definir_senha ?? perfil.precisa_definir_senha,
      }
    } catch (err) {
      setUser(null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      throw err
    } finally {
      setLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        loadPerfil,
        isAdmin: !!user?.is_admin,
        precisaDefinirSenha: !!user?.precisa_definir_senha,
        cnh: user?.cnh || null,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
