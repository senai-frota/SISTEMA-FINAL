import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import DefinirSenha from './pages/DefinirSenha'
import Dashboard from './pages/Dashboard'
import Veiculos from './pages/Veiculos'
import Reservas from './pages/Reservas'
import Aprovacoes from './pages/Aprovacoes'
import Usuarios from './pages/Usuarios'
import RelatorioCalendario from './pages/RelatorioCalendario'
import MeuCNH from './pages/MeuCNH'
import CnhAdmin from './pages/CnhAdmin'
import MeuTermo from './pages/MeuTermo'
import TermosAdmin from './pages/TermosAdmin'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
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
          <Route path="/relatorio-calendario" element={<ProtectedRoute adminOnly><RelatorioCalendario /></ProtectedRoute>} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
