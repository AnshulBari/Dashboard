import { useState } from 'react'
import { NavLink, Outlet, useSearchParams } from 'react-router-dom'
import {
  LayoutDashboard, Users, Shield, MapPin,
  Trophy, Radio, BarChart3, Search, Menu, X, Zap
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/live', label: 'Live', icon: Radio, live: true },
  { to: '/players', label: 'Players', icon: Users },
  { to: '/teams', label: 'Teams', icon: Shield },
  { to: '/matches', label: 'Matches', icon: Trophy },
  { to: '/venues', label: 'Venues', icon: MapPin },
  { to: '/rankings', label: 'Rankings', icon: BarChart3 },
]

const FORMATS = ['All', 'T20', 'T20I', 'ODI', 'Test']

export default function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const currentFormat = searchParams.get('format') || 'All'

  const setFormat = (fmt: string) => {
    const params = new URLSearchParams(searchParams)
    if (fmt === 'All') params.delete('format')
    else params.set('format', fmt)
    setSearchParams(params)
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface-0">
      {/* ============================================================
          TOP NAVIGATION BAR — inspired by FIFA Live Center
          ============================================================ */}
      <header className="relative z-50 border-b border-white/5">
        {/* Main nav row */}
        <div className="h-14 flex items-center px-4 lg:px-6 bg-surface-50/80 backdrop-blur-md">
          {/* Logo */}
          <div className="flex items-center gap-2 mr-6 flex-shrink-0">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-bold text-gray-100 tracking-tight hidden sm:block">
              Cricket<span className="text-emerald-400">IQ</span>
            </span>
          </div>

          {/* Mobile menu toggle */}
          <button
            className="lg:hidden mr-2 text-gray-400 hover:text-gray-200 p-1.5"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          {/* Centered navigation tabs — desktop */}
          <nav className="hidden lg:flex items-center gap-1 flex-1 justify-center">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 shadow-sm shadow-emerald-500/10'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-white/[0.04]'
                  }`
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
                {item.live && (
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                )}
              </NavLink>
            ))}
          </nav>

          {/* Right side — search */}
          <div className="flex items-center gap-3 ml-auto">
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/10 bg-white/[0.03] text-gray-500 hover:text-gray-300 hover:border-white/15 transition-colors text-sm">
              <Search className="h-4 w-4" />
              <span className="hidden sm:inline text-xs">Search...</span>
              <kbd className="hidden md:inline-flex items-center px-1.5 py-0.5 rounded-md bg-white/5 text-[10px] font-mono text-gray-500 border border-white/10">
                ⌘K
              </kbd>
            </button>
          </div>
        </div>

        {/* Format filter bar — second row */}
        <div className="h-10 flex items-center px-4 lg:px-6 bg-surface-50/40 border-t border-white/[0.03]">
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mr-3 hidden sm:block">Format</span>
          <div className="flex items-center gap-1 overflow-x-auto">
            {FORMATS.map(fmt => (
              <button
                key={fmt}
                onClick={() => setFormat(fmt)}
                className={`px-3 py-1 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all duration-200 whitespace-nowrap ${
                  currentFormat === fmt
                    ? 'bg-emerald-500/15 text-emerald-400 shadow-sm shadow-emerald-500/10'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.04]'
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>
          {/* Data source indicator */}
          <div className="ml-auto text-[10px] text-gray-600 hidden md:block">
            8,250 matches · Cricsheet
          </div>
        </div>

        {/* Mobile navigation drawer */}
        {mobileMenuOpen && (
          <div className="lg:hidden absolute top-full left-0 right-0 bg-surface-50/95 backdrop-blur-lg border-b border-white/5 shadow-2xl z-40">
            <nav className="px-4 py-3 space-y-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-200'
                    }`
                  }
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                  {item.live && (
                    <span className="ml-1 w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
        )}
      </header>

      {/* ============================================================
          MAIN CONTENT
          ============================================================ */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-5">
          <Outlet context={{ format: currentFormat }} />
        </div>
      </main>
    </div>
  )
}
