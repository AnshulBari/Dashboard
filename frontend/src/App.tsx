import { lazy, Suspense, type ReactNode } from 'react'
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
const MatchDetail = lazy(() => import('./pages/MatchDetail'))
const Live = lazy(() => import('./pages/Live'))
const Rankings = lazy(() => import('./pages/Rankings'))

function PageLoader() {
  return (
    <div className="card-glass flex min-h-[320px] items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-gray-500">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500/20 border-t-brand-400" />
        <span className="text-[9px] font-bold uppercase tracking-[.18em]">Loading intelligence</span>
      </div>
    </div>
  )
}

function LazyPage({ children }: { children: ReactNode }) {
  return <Suspense fallback={<PageLoader />}>{children}</Suspense>
}

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/players" element={<LazyPage><Players /></LazyPage>} />
        <Route path="/players/:id" element={<LazyPage><PlayerDetail /></LazyPage>} />
        <Route path="/teams" element={<LazyPage><Teams /></LazyPage>} />
        <Route path="/teams/:id" element={<LazyPage><TeamDetail /></LazyPage>} />
        <Route path="/venues" element={<LazyPage><Venues /></LazyPage>} />
        <Route path="/venues/:id" element={<LazyPage><VenueDetail /></LazyPage>} />
        <Route path="/matchups" element={<LazyPage><Matchups /></LazyPage>} />
        <Route path="/matches" element={<LazyPage><Matches /></LazyPage>} />
        <Route path="/matches/:id" element={<LazyPage><MatchDetail /></LazyPage>} />
        <Route path="/live" element={<LazyPage><Live /></LazyPage>} />
        <Route path="/rankings" element={<LazyPage><Rankings /></LazyPage>} />
        <Route path="/competitions" element={<LazyPage><Rankings /></LazyPage>} />
        <Route path="/competitions/:id" element={<LazyPage><Rankings /></LazyPage>} />
      </Route>
    </Routes>
  )
}

export default App
