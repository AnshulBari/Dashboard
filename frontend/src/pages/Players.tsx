import { useState, useEffect } from 'react'
import { Search, Filter, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { playerApi } from '../services/api'

interface PlayerRow {
  id: string
  name: string
  role: string | null
  country: string | null
  team_name: string | null
  form_score: number | null
  batting_average: number | null
  strike_rate: number | null
  career_runs: number | null
  career_wickets: number | null
}

const roleColors: Record<string, string> = {
  batsman: 'bg-blue-100 text-blue-800',
  bowler: 'bg-red-100 text-red-800',
  allrounder: 'bg-purple-100 text-purple-800',
  wicketkeeper: 'bg-amber-100 text-amber-800',
}

function FormScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-emerald-500'
    : score >= 60 ? 'bg-brand-500'
    : score >= 40 ? 'bg-amber-500'
    : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-surface-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-bold text-gray-900 w-10 text-right">{score.toFixed(1)}</span>
    </div>
  )
}

export default function Players() {
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [players, setPlayers] = useState<PlayerRow[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    async function load() {
      try {
        const res = await playerApi.list({ format: 'T20', sortBy: 'form_score', limit: 100 }) as { players: PlayerRow[] }
        setPlayers(res.players || [])
      } catch (err) {
        console.error('Failed to load players:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filteredPlayers = players.filter(p => {
    const matchesSearch = (p.name || '').toLowerCase().includes(search.toLowerCase()) ||
      (p.country || '').toLowerCase().includes(search.toLowerCase())
    const matchesRole = roleFilter === 'all' || p.role === roleFilter
    return matchesSearch && matchesRole
  })

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Player Intelligence</h1>
        <p className="page-subtitle">
          Analyze player performance, form, and matchup data
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search players..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="form-input pl-10"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          {['all', 'batsman', 'bowler', 'allrounder', 'wicketkeeper'].map(role => (
            <button
              key={role}
              onClick={() => setRoleFilter(role)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                roleFilter === role
                  ? 'bg-brand-100 text-brand-700'
                  : 'bg-surface-100 text-gray-600 hover:bg-surface-200'
              }`}
            >
              {role === 'all' ? 'All' : role.charAt(0).toUpperCase() + role.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading players...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPlayers.map((player) => (
            <div
              key={player.id}
              onClick={() => navigate(`/players/${player.id}`)}
              className="card-hover p-5 cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-base font-semibold text-gray-900">{player.name}</h3>
                  <p className="text-sm text-gray-500">{player.team_name || player.country || 'Unknown'}</p>
                </div>
                <span className={`badge ${roleColors[player.role || 'batsman']}`}>
                  {player.role || 'batsman'}
                </span>
              </div>
              
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Form Score</span>
                  {player.form_score != null ? (
                    <FormScoreBar score={player.form_score} />
                  ) : (
                    <span className="text-xs text-gray-400">N/A</span>
                  )}
                </div>
                
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-surface-100">
                  <div>
                    <p className="text-xs text-gray-500">Runs</p>
                    <p className="text-sm font-bold text-gray-900">{player.career_runs?.toLocaleString() || '-'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Avg</p>
                    <p className="text-sm font-bold text-gray-900">{player.batting_average?.toFixed(1) || '-'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">SR</p>
                    <p className="text-sm font-bold text-gray-900">{player.strike_rate?.toFixed(1) || '-'}</p>
                  </div>
                </div>
              </div>
              
              <div className="mt-4 flex items-center text-brand-600 text-xs font-medium">
                View Intelligence
                <ChevronRight className="h-3 w-3 ml-1" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
