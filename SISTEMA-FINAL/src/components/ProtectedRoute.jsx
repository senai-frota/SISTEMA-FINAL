import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Layout from './Layout'

export default function ProtectedRoute({ children, adminOnly = false, allowPrimeiroAcesso = false }) {
  const { user, loading, isAdmin, precisaDefinirSenha } = useAuth()

  if (loading) {
    return (
      <div className="full-screen-loader">
        <div className="spinner" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  if (precisaDefinirSenha && !allowPrimeiroAcesso) {
    return <Navigate to="/definir-senha" replace />
  }

  if (!precisaDefinirSenha && allowPrimeiroAcesso) {
    return <Navigate to="/" replace />
  }

  if (adminOnly && !isAdmin) return <Navigate to="/" replace />

  if (allowPrimeiroAcesso) {
    return children
  }

  return <Layout>{children}</Layout>
}
