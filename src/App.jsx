import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { AuthProvider, CHAVE_SESSAO_INICIADA, useAuth } from './context/AuthContext'
import { FeedbackProvider } from './context/FeedbackContext'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import DefinirSenha from './pages/DefinirSenha'
import Dashboard from './pages/Dashboard'
import Veiculos from './pages/Veiculos'
import Reservas from './pages/Reservas'
import Aprovacoes from './pages/Aprovacoes'
import Usuarios from './pages/Usuarios'
import RelatorioCalendario from './pages/RelatorioCalendario'
import Relatorios from './pages/Relatorios'
import MeuCNH from './pages/MeuCNH'
import CnhAdmin from './pages/CnhAdmin'
import MeuTermo from './pages/MeuTermo'
import TermosAdmin from './pages/TermosAdmin'
import Auditoria from './pages/Auditoria'

function EntradaPeloDashboard() {
  const { user, loading, precisaDefinirSenha } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (loading || !user) return
    if (sessionStorage.getItem(CHAVE_SESSAO_INICIADA)) return
    sessionStorage.setItem(CHAVE_SESSAO_INICIADA, '1')
    if (!precisaDefinirSenha && location.pathname !== '/') {
      navigate('/', { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, user, precisaDefinirSenha])

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <FeedbackProvider>
        <AuthProvider>
          <EntradaPeloDashboard />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/definir-senha"
              element={
                <ProtectedRoute allowPrimeiroAcesso>
                  <DefinirSenha />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/veiculos" element={<ProtectedRoute><Veiculos /></ProtectedRoute>} />
            <Route path="/reservas" element={<ProtectedRoute><Reservas /></ProtectedRoute>} />
            <Route path="/minha-cnh" element={<ProtectedRoute><MeuCNH /></ProtectedRoute>} />
            <Route path="/meu-termo" element={<ProtectedRoute><MeuTermo /></ProtectedRoute>} />
            <Route path="/aprovacoes" element={<ProtectedRoute adminOnly><Aprovacoes /></ProtectedRoute>} />
            <Route path="/usuarios" element={<ProtectedRoute adminOnly><Usuarios /></ProtectedRoute>} />
            <Route path="/cnh-pendentes" element={<ProtectedRoute adminOnly><CnhAdmin /></ProtectedRoute>} />
            <Route path="/termos-pendentes" element={<ProtectedRoute adminOnly><TermosAdmin /></ProtectedRoute>} />
            <Route path="/relatorios" element={<ProtectedRoute adminOnly><Relatorios /></ProtectedRoute>} />
            <Route path="/relatorio-calendario" element={<ProtectedRoute adminOnly><RelatorioCalendario /></ProtectedRoute>} />
            <Route path="/auditoria" element={<ProtectedRoute adminOnly><Auditoria /></ProtectedRoute>} />
          </Routes>
        </AuthProvider>
      </FeedbackProvider>
    </BrowserRouter>
  )
}
