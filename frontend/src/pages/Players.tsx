import { useState } from 'react'
import { Search, Filter, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const samplePlayers = [
  { id: '1', name: 'Suryakumar Yadav', country: 'India', role: 'batsman', formScore: 89.2, battingAvg: 35.8, strikeRate: 148.5, careerRuns: 1543, careerWickets: 0 },
  { id: '2', name: 'Jos Buttler', country: 'England', role: 'wicketkeeper', formScore: 84.7, battingAvg: 32.5, strikeRate: 142.3, careerRuns: 1287, careerWickets: 0 },
  { id: '3', name: 'Babar Azam', country: 'Pakistan', role: 'batsman', formScore: 82.1, battingAvg: 42.3, strikeRate: 128.7, careerRuns: 1654, careerWickets: 0 },
  { id: '4', name: 'Virat Kohli', country: 'India', role: 'batsman', formScore: 79.8, battingAvg: 48.2, strikeRate: 135.2, careerRuns: 1432, careerWickets: 0 },
  { id: '5', name: 'Jasprit Bumrah', country: 'India', role: 'bowler', formScore: 85.3, battingAvg: 0, strikeRate: 0, careerRuns: 45, careerWickets: 72 },
  { id: '6', name: 'Rashid Khan', country: 'Afghanistan', role: 'bowler', formScore: 81.5, battingAvg: 12.5, strikeRate: 155.0, careerRuns: 234, careerWickets: 98 },
  { id: '7', name: 'David Warner', country: 'Australia', role: 'batsman', formScore: 78.3, battingAvg: 38.9, strikeRate: 140.8, careerRuns: 1198, careerWickets: 0 },
  { id: '8', name: 'Hardik Pandya', country: 'India', role: 'allrounder', formScore: 76.5, battingAvg: 28.5, strikeRate: 145.2, careerRuns: 654, careerWickets: 42 },
  { id: '9', name: 'Kagiso Rabada', country: 'South Africa', role: 'bowler', formScore: 74.8, battingAvg: 8.2, strikeRate: 120.5, careerRuns: 123, careerWickets: 85 },
  { id: '10', name: 'Quinton de Kock', country: 'South Africa', role: 'wicketkeeper', formScore: 72.1, battingAvg: 31.2, strikeRate: 138.5, careerRuns: 1087, careerWickets: 0 },
]

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
  const navigate = useNavigate()

  const filteredPlayers = samplePlayers.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.country.toLowerCase().includes(search.toLowerCase())
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

      {/* Player Grid */}
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
                <p className="text-sm text-gray-500">{player.country}</p>
              </div>
              <span className={`badge ${roleColors[player.role]}`}>
                {player.role}
              </span>
            </div>
            
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Form Score</span>
                <FormScoreBar score={player.formScore} />
              </div>
              
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-surface-100">
                {player.role === 'bowler' ? (
                  <>
                    <div>
                      <p className="text-xs text-gray-500">Wickets</p>
                      <p className="text-sm font-bold text-gray-900">{player.careerWickets}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Avg</p>
                      <p className="text-sm font-bold text-gray-900">{player.battingAvg}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">SR</p>
                      <p className="text-sm font-bold text-gray-900">{player.strikeRate}</p>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <p className="text-xs text-gray-500">Runs</p>
                      <p className="text-sm font-bold text-gray-900">{player.careerRuns.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Avg</p>
                      <p className="text-sm font-bold text-gray-900">{player.battingAvg}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">SR</p>
                      <p className="text-sm font-bold text-gray-900">{player.strikeRate}</p>
                    </div>
                  </>
                )}
              </div>
            </div>
            
            <div className="mt-4 flex items-center text-brand-600 text-xs font-medium">
              View Intelligence
              <ChevronRight className="h-3 w-3 ml-1" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
