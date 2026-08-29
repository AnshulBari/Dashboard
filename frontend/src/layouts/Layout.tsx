import { useState } from 'react'
import { NavLink, Outlet, useSearchParams } from 'react-router-dom'
import {
  LayoutDashboard, Users, Shield, MapPin, Swords,
  Trophy, Radio, BarChart3, Search, Menu, X, Zap
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/live', label: 'Live', icon: Radio },
  { to: '/players', label: 'Players', icon: Users },
  { to: '/teams', label: 'Teams', icon: Shield },
  { to: '/matches', label: 'Matches', icon: Trophy },
  { to: '/venues', label: 'Venues', icon: MapPin },
  { to: '/matchups', label: 'Matchups', icon: Swords },
  { to: '/rankings', label: 'Rankings', icon: BarChart3 },
]

const FORMATS = ['All', 'T20', 'T20I', 'ODI', 'Test']

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const currentFormat = searchParams.get('format') || 'All'

  const setFormat = (fmt: string) => {
    const params = new URLSearchParams(searchParams)
    if (fmt === 'All') {
      params.delete('format')
    } else {
      params.set('format', fmt)
    }
    setSearchParams(params)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-0">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-surface-50 border-r border-surface-200/50 
        flex flex-col transform transition-transform duration-200 ease-in-out
        lg:relative lg:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo */}
        <div className="h-14 flex items-center px-5 border-b border-surface-200/50">
          <Zap className="h-6 w-6 text-brand-500" />
          <span className="ml-2.5 text-base font-bold text-gray-100 tracking-tight">
            Cricket<span className="text-brand-400">IQ</span>
          </span>
          <button 
            className="ml-auto lg:hidden text-gray-400 hover:text-gray-200"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                    : 'text-gray-400 hover:bg-surface-100 hover:text-gray-200 border border-transparent'
                }`
              }
            >
              <item.icon className="h-4 w-4 mr-3 flex-shrink-0" />
              {item.label}
              {item.to === '/live' && (
                <span className="ml-auto flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-cricket-green opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-cricket-green" />
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Format Filter */}
        <div className="px-3 py-3 border-t border-surface-200/50">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1">
            Format
          </p>
          <div className="flex flex-wrap gap-1">
            {FORMATS.map(fmt => (
              <button
                key={fmt}
                onClick={() => setFormat(fmt)}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                  currentFormat === fmt
                    ? 'bg-brand-500/15 text-brand-400 border border-brand-500/25'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-surface-100 border border-transparent'
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-surface-200/50">
          <div className="text-[10px] text-gray-600">
            Cricket Intelligence Platform
          </div>
          <div className="text-[10px] text-gray-600 mt-0.5">
            Data: Cricsheet · 8,250 matches
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 flex items-center px-4 border-b border-surface-200/50 bg-surface-50/50 backdrop-blur-sm">
          {/* Mobile menu button */}
          <button
            className="lg:hidden mr-3 text-gray-400 hover:text-gray-200"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Mobile logo */}
          <div className="lg:hidden flex items-center mr-auto">
            <Zap className="h-5 w-5 text-brand-500" />
            <span className="ml-1.5 text-sm font-bold text-gray-100">
              Cricket<span className="text-brand-400">IQ</span>
            </span>
          </div>

          {/* Desktop spacer */}
          <div className="hidden lg:block flex-1" />

          {/* Format tabs - desktop */}
          <div className="hidden md:flex items-center gap-1 mr-4">
            {FORMATS.map(fmt => (
              <button
                key={fmt}
                onClick={() => setFormat(fmt)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  currentFormat === fmt
                    ? 'bg-brand-500/15 text-brand-400 border border-brand-500/25'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-surface-100 border border-transparent'
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>

          {/* Search trigger */}
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-300 bg-surface-100 text-gray-500 hover:text-gray-300 hover:border-surface-400 transition-colors text-sm">
            <Search className="h-4 w-4" />
            <span className="hidden sm:inline text-xs">Search...</span>
            <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded bg-surface-200 text-[10px] font-mono text-gray-500 border border-surface-300">
              ⌘K
            </kbd>
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
            <Outlet context={{ format: currentFormat }} />
          </div>
        </main>
      </div>
    </div>
  )
}
