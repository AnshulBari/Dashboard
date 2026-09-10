import { FormEvent, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Activity, BarChart3, CircleUserRound, LayoutDashboard, MapPin,
  Menu, Radio, Search, Shield, Swords, Trophy, Users, X,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/live', label: 'Live', icon: Radio, live: true },
  { to: '/matches', label: 'Matches', icon: Trophy },
  { to: '/players', label: 'Players', icon: Users },
  { to: '/teams', label: 'Teams', icon: Shield },
  { to: '/matchups', label: 'Matchups', icon: Swords },
  { to: '/venues', label: 'Venues', icon: MapPin },
  { to: '/rankings', label: 'Rankings', icon: BarChart3 },
]

const FORMATS = [
  { value: 'International', label: 'INTL' },
  { value: 'T20I', label: 'T20I' },
  { value: 'ODI', label: 'ODI' },
  { value: 'Test', label: 'TEST' },
  { value: 'T20', label: 'T20' },
]

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const currentFormat = searchParams.get('format') || 'International'

  const setFormat = (format: string) => {
    const params = new URLSearchParams(searchParams)
    if (format === 'International') params.delete('format')
    else params.set('format', format)
    setSearchParams(params)
  }

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    const term = query.trim()
    if (!term) return
    const params = new URLSearchParams()
    params.set('search', term)
    if (currentFormat !== 'International') params.set('format', currentFormat)
    navigate(`/players?${params.toString()}`)
    setMobileMenuOpen(false)
  }

  return (
    <div className="app-shell">
      <div className="stadium-backdrop" aria-hidden="true" />
      <header className="app-header">
        <div className="topbar">
          <NavLink to="/" className="brand-lockup" aria-label="Cricket IQ home">
            <span className="brand-mark"><span className="brand-seam" /></span>
            <span className="brand-copy">
              <span className="brand-name">CRICKET IQ</span>
              <span className="brand-subtitle">Intelligence Center</span>
            </span>
          </NavLink>

          <form className="global-search" onSubmit={submitSearch} role="search">
            <Search className="h-4 w-4" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search players..."
              aria-label="Search players"
            />
            <kbd>Enter</kbd>
          </form>

          <button
            className="mobile-menu-button"
            onClick={() => setMobileMenuOpen((open) => !open)}
            aria-label="Toggle navigation"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X /> : <Menu />}
          </button>

          <nav className="desktop-nav" aria-label="Primary navigation">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                title={item.label}
                className={({ isActive }) => `nav-pill ${isActive ? 'nav-pill-active' : ''}`}
              >
                <item.icon />
                <span>{item.label}</span>
                {item.live && <i className="signal-dot" />}
              </NavLink>
            ))}
          </nav>

          <div className="member-chip">
            <span className="member-avatar"><CircleUserRound /></span>
            <span className="member-copy">
              <strong>Analyst</strong>
              <small>Pro workspace</small>
            </span>
            <Activity className="member-activity" />
          </div>
        </div>

        <div className="context-bar">
          <div className="context-route">
            <span className="signal-dot" />
            <span>{location.pathname === '/' ? 'Command center' : location.pathname.split('/')[1]}</span>
          </div>
          <div className="format-switch" aria-label="Match format filter">
            {FORMATS.map((format) => (
              <button
                key={format.value}
                onClick={() => setFormat(format.value)}
                className={currentFormat === format.value ? 'active' : ''}
                title={format.value === 'International' ? 'International: T20I + ODI + Test' : format.value}
              >
                {format.label}
              </button>
            ))}
          </div>
          <div className="data-status">
            <span className="status-wave"><i /><i /><i /></span>
            8,232 matches indexed
          </div>
        </div>

        {mobileMenuOpen && (
          <nav className="mobile-nav" aria-label="Mobile navigation">
            <form className="mobile-search" onSubmit={submitSearch} role="search">
              <Search />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search players..."
                aria-label="Search players"
              />
            </form>
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}
              >
                <item.icon />
                <span>{item.label}</span>
                {item.live && <i className="signal-dot" />}
              </NavLink>
            ))}
          </nav>
        )}
      </header>

      <main className="app-main">
        <div className="content-frame">
          <Outlet context={{ format: currentFormat }} />
        </div>
      </main>
    </div>
  )
}
