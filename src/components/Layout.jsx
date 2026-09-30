import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/', label: 'Painel', icon: '▤', end: true, bottom: true },
  { to: '/veiculos', label: 'Veículos', icon: '▣', bottom: true },
  { to: '/reservas', label: 'Minhas reservas', adminLabel: 'Reservas', icon: '▤', bottom: true },
  { to: '/minha-cnh', label: 'Minha CNH', icon: '▥', userOnly: true, bottom: true },
  { to: '/meu-termo', label: 'Meu termo', icon: '▥', userOnly: true },
  { to: '/aprovacoes', label: 'Aprovações', icon: '▤', adminOnly: true, bottom: true },
  { to: '/usuarios', label: 'Usuários', icon: '◉', adminOnly: true },
  { to: '/cnh-pendentes', label: 'CNH pendentes', icon: '▤', adminOnly: true },
  { to: '/termos-pendentes', label: 'Termos pendentes', icon: '▤', adminOnly: true },
  { to: '/relatorios', label: 'Relatórios', icon: '▦', adminOnly: true },
  { to: '/auditoria', label: 'Auditoria', icon: '▥', adminOnly: true },
]

export default function Layout({ children }) {
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [menuOpen, setMenuOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark')

  useEffect(() => {
    const html = document.documentElement
    if (darkMode) {
      html.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      html.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [darkMode])

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  const items = useMemo(
    () =>
      NAV_ITEMS.filter((item) => {
        if (item.adminOnly && !isAdmin) return false
        if (item.userOnly && isAdmin) return false
        return true
      }),
    [isAdmin]
  )

  const bottomItems = useMemo(() => {
    const primary = items.filter((i) => i.bottom).slice(0, 4)
    return primary
  }, [items])

  function labelOf(item) {
    return isAdmin && item.adminLabel ? item.adminLabel : item.label
  }

  function handleLogout() {
    setMenuOpen(false)
    logout()
    navigate('/login')
  }

  const initials = (user?.nome || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>FROTA / SENAI</strong>
            <small>Gestão de veículos</small>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Menu principal">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              onClick={() => setMenuOpen(false)}
            >
              <span className="sidebar-icon">{item.icon}</span>
              {labelOf(item)}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <span className="avatar">{initials || '?'}</span>
            <div className="user-info">
              <strong>{user?.nome}</strong>
              <small>{isAdmin ? 'Administrador' : `Matrícula ${user?.matricula}`}</small>
            </div>
          </div>
          <button
            className="logout-btn"
            onClick={handleLogout}
            type="button"
            aria-label="Sair da conta"
          >
            Sair
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button
            className="icon-btn mobile-menu-btn"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
            type="button"
          >
            ☰
          </button>
          <div className="topbar-title">FROTA / SENAI</div>
          <div className="topbar-spacer" />
          <button
            className="theme-toggle"
            onClick={() => setDarkMode((c) => !c)}
            aria-label={darkMode ? 'Ativar tema claro' : 'Ativar tema escuro'}
            type="button"
          >
            {darkMode ? '☀' : '◐'}
          </button>
        </header>

        <main className="app-content">{children}</main>

        <div className="powered-by">
          <span>Desenvolvido por </span>
          <strong>3ºDS/2026 - Humberto.O - Samuel.Sa - Samuel.So - Pedro.So</strong>
        </div>
      </div>

      <nav className="bottom-nav" aria-label="Atalhos móveis">
        {bottomItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `bottom-nav-link ${isActive ? 'active' : ''}`}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{labelOf(item)}</span>
          </NavLink>
        ))}
        <button
          type="button"
          className="bottom-nav-link"
          onClick={() => setMenuOpen(true)}
          aria-label="Mais opções"
        >
          <span className="bottom-nav-icon">☰</span>
          <span className="bottom-nav-label">Mais</span>
        </button>
      </nav>

      {menuOpen && (
        <div className="sidebar-scrim" onClick={() => setMenuOpen(false)} aria-hidden="true" />
      )}
    </div>
  )
}
