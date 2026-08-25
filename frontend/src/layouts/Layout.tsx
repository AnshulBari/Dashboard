import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Users, Shield, MapPin, Swords,
  Trophy, Radio, BarChart3, Newspaper, Activity
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/players', label: 'Players', icon: Users },
  { to: '/teams', label: 'Teams', icon: Shield },
  { to: '/venues', label: 'Venues', icon: MapPin },
  { to: '/matchups', label: 'Matchups', icon: Swords },
  { to: '/matches', label: 'Matches', icon: Trophy },
  { to: '/live', label: 'Live', icon: Radio },
  { to: '/rankings', label: 'Rankings', icon: BarChart3 },
  { to: '/news', label: 'News', icon: Newspaper },
]

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-surface-200 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-surface-200">
          <Activity className="h-7 w-7 text-brand-600" />
          <span className="ml-3 text-lg font-bold text-gray-900">
            CricketIQ
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-600 hover:bg-surface-50 hover:text-gray-900'
                }`
              }
            >
              <item.icon className="h-5 w-5 mr-3 flex-shrink-0" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-surface-200">
          <div className="text-xs text-gray-400">
            Cricket Intelligence Platform
          </div>
          <div className="text-xs text-gray-400 mt-0.5">
            v1.0.0 · Data: Cricsheet
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
