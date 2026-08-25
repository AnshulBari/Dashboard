import { Routes, Route } from 'react-router-dom'
import Layout from './layouts/Layout'
import Dashboard from './pages/Dashboard'
import Players from './pages/Players'
import PlayerDetail from './pages/PlayerDetail'
import Teams from './pages/Teams'
import TeamDetail from './pages/TeamDetail'
import Venues from './pages/Venues'
import VenueDetail from './pages/VenueDetail'
import Matchups from './pages/Matchups'
import Matches from './pages/Matches'
import Live from './pages/Live'
import Rankings from './pages/Rankings'
import News from './pages/News'

function App() {
  return (
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
        <Route path="/live" element={<Live />} />
        <Route path="/rankings" element={<Rankings />} />
        <Route path="/news" element={<News />} />
      </Route>
    </Routes>
  )
}

export default App
