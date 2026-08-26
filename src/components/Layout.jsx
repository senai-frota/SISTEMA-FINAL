import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  {
    to: '/',
    label: 'Painel',
    icon: '▤',
    end: true,
  },
  {
    to: '/veiculos',
    label: 'Veículos',
    icon: '▣',
  },
  {
    to: '/reservas',
    label: 'Minhas reservas',
    adminLabel: 'Reservas',
    icon: '▤',
  },
  {
    to: '/termos',
    label: 'Meu termo',
    adminLabel: 'Termos',
    icon: '▦',
  },
  {
    to: '/usuarios',
    label: 'Usuários',
    icon: '◉',
    adminOnly: true,
  },
]

export default function Layout({ children }) {
  const { user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()

  const [menuOpen, setMenuOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('theme') === 'dark'
  })

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

  function toggleTheme() {
    setDarkMode((current) => !current)
  }

  function handleLogout() {
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

        <nav className="sidebar-nav">
          {NAV_ITEMS
            .filter((item) => !item.adminOnly || isAdmin)
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'active' : ''}`
                }
                onClick={() => setMenuOpen(false)}
              >
                <span className="sidebar-icon">
                  {item.icon}
                </span>

                {isAdmin && item.adminLabel
                  ? item.adminLabel
                  : item.label}
              </NavLink>
            ))}
        </nav>

        <div className="sidebar-footer">

          <div className="user-chip">
            <span className="avatar">
              {initials || '?'}
            </span>

            <div className="user-info">
              <strong>{user?.nome}</strong>

              <small>
                {isAdmin
                  ? 'Administrador'
                  : `Matrícula ${user?.matricula}`}
              </small>
            </div>
          </div>

          <button
            className="logout-btn"
            onClick={handleLogout}
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
            aria-label="Abrir menu"
          >
            ☰
          </button>

          <div className="topbar-spacer" />

          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={
              darkMode
                ? 'Ativar tema claro'
                : 'Ativar tema escuro'
            }
            title={
              darkMode
                ? 'Tema claro'
                : 'Tema escuro'
            }
          >
            {darkMode ? '☀' : '◐'}
          </button>

        </header>

        <main className="app-content">
          {children}
        </main>

        <div className="powered-by">
          <span>Desenvolvido por </span>
          <strong>
            3ºDS/2026 - Humberto.O - Samuel.Sa - Samuel.So - Pedro.So
          </strong>
        </div>

      </div>

      {menuOpen && (
        <div
          className="sidebar-scrim"
          onClick={() => setMenuOpen(false)}
        />
      )}
    </div>
  )
}