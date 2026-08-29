import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './layouts/Layout'
import Dashboard from './pages/Dashboard'

// Lazy load pages that aren't the primary focus of this phase
const Players = lazy(() => import('./pages/Players'))
const PlayerDetail = lazy(() => import('./pages/PlayerDetail'))
const Teams = lazy(() => import('./pages/Teams'))
const TeamDetail = lazy(() => import('./pages/TeamDetail'))
const Venues = lazy(() => import('./pages/Venues'))
const VenueDetail = lazy(() => import('./pages/VenueDetail'))
const Matchups = lazy(() => import('./pages/Matchups'))
const Matches = lazy(() => import('./pages/Matches'))
const Live = lazy(() => import('./pages/Live'))
const Rankings = lazy(() => import('./pages/Rankings'))

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="flex items-center gap-3 text-gray-500">
        <div className="w-5 h-5 border-2 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
        <span className="text-sm">Loading...</span>
      </div>
    </div>
  )
}

function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/players" element={<Players />} />
          <Route path="/players/:id" element={<PlayerDetail />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/teams/:id" element={<TeamDetail />} />
          <Route path="/venues" element={<Venues />} />
          <Route path="/venues/:id" element={<VenueDetail />} />
          <Route path="/matchups" element={<Matchups />} />
          <Route path="/matches" element={<Matches />} />
          <Route path="/matches/:id" element={<Matches />} />
          <Route path="/live" element={<Live />} />
          <Route path="/rankings" element={<Rankings />} />
          <Route path="/competitions" element={<Rankings />} />
          <Route path="/competitions/:id" element={<Rankings />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default App
