import { TrendingUp, Users, Shield, MapPin, Trophy, Activity } from 'lucide-react'

// Sample data for development (will be replaced with API data)
const trendingPlayers = [
  { id: '1', name: 'Suryakumar Yadav', team: 'IND', formScore: 89.2, runs: 1543, strikeRate: 148.5, trend: 'up' },
  { id: '2', name: 'Jos Buttler', team: 'ENG', formScore: 84.7, runs: 1287, strikeRate: 142.3, trend: 'up' },
  { id: '3', name: 'Babar Azam', team: 'PAK', formScore: 82.1, runs: 1654, strikeRate: 128.7, trend: 'stable' },
  { id: '4', name: 'Virat Kohli', team: 'IND', formScore: 79.8, runs: 1432, strikeRate: 135.2, trend: 'down' },
  { id: '5', name: 'David Warner', team: 'AUS', formScore: 78.3, runs: 1198, strikeRate: 140.8, trend: 'up' },
]

const teamRankings = [
  { id: '1', name: 'India', strength: 91.2, winRate: 72.5, matches: 45 },
  { id: '2', name: 'England', strength: 85.8, winRate: 68.3, matches: 42 },
  { id: '3', name: 'Australia', strength: 84.5, winRate: 65.2, matches: 38 },
  { id: '4', name: 'Pakistan', strength: 80.1, winRate: 62.8, matches: 40 },
  { id: '5', name: 'South Africa', strength: 78.9, winRate: 60.5, matches: 36 },
]

const recentMatches = [
  { id: '1', format: 'T20I', date: '2024-01-15', teamA: 'IND', teamB: 'AUS', result: 'IND won by 7 wickets' },
  { id: '2', format: 'T20I', date: '2024-01-14', teamA: 'ENG', teamB: 'SA', result: 'ENG won by 12 runs' },
  { id: '3', format: 'T20I', date: '2024-01-13', teamA: 'PAK', teamB: 'NZ', result: 'NZ won by 3 wickets' },
  { id: '4', format: 'ODI', date: '2024-01-12', teamA: 'IND', teamB: 'SL', result: 'IND won by 108 runs' },
  { id: '5', format: 'T20I', date: '2024-01-11', teamA: 'AUS', teamB: 'ENG', result: 'AUS won by 5 wickets' },
]

const venueInsights = [
  { name: 'MCG', avgScore: 168, chaseWinPct: 55, pacePct: 58 },
  { name: 'Eden Gardens', avgScore: 172, chaseWinPct: 52, pacePct: 52 },
  { name: 'Dubai International', avgScore: 158, chaseWinPct: 58, pacePct: 60 },
]

function StatCard({ label, value, change, icon: Icon, color }: {
  label: string
  value: string | number
  change?: string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="stat-label">{label}</p>
          <p className="stat-value mt-1">{value}</p>
          {change && (
            <p className={change.startsWith('+') ? 'stat-change-positive mt-1' : 'stat-change-negative mt-1'}>
              {change}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
      </div>
    </div>
  )
}

function FormBadge({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-emerald-100 text-emerald-800'
    : score >= 60 ? 'bg-blue-100 text-blue-800'
    : score >= 40 ? 'bg-amber-100 text-amber-800'
    : 'bg-red-100 text-red-800'
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${color}`}>
      {score.toFixed(1)}
    </span>
  )
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'up') return <TrendingUp className="h-4 w-4 text-emerald-500" />
  if (trend === 'down') return <TrendingUp className="h-4 w-4 text-red-500 rotate-180" />
  return <Activity className="h-4 w-4 text-gray-400" />
}

export default function Dashboard() {
  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Intelligence Overview</h1>
        <p className="page-subtitle">
          Real-time cricket analytics and player intelligence
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          label="Players Tracked"
          value="1,247"
          change="+23 this week"
          icon={Users}
          color="bg-brand-600"
        />
        <StatCard
          label="Teams"
          value="18"
          icon={Shield}
          color="bg-emerald-600"
        />
        <StatCard
          label="Matches Analyzed"
          value="3,892"
          change="+156 this month"
          icon={Trophy}
          color="bg-amber-500"
        />
        <StatCard
          label="Venues"
          value="87"
          icon={MapPin}
          color="bg-violet-600"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Trending Players */}
        <div className="lg:col-span-2 card">
          <div className="px-6 py-4 border-b border-surface-200">
            <h2 className="text-lg font-semibold text-gray-900">Trending Players</h2>
            <p className="text-sm text-gray-500 mt-0.5">Players with the highest form scores</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-6 py-3">Player</th>
                  <th className="px-6 py-3">Team</th>
                  <th className="px-6 py-3 text-right">Form Score</th>
                  <th className="px-6 py-3 text-right">Runs</th>
                  <th className="px-6 py-3 text-right">SR</th>
                  <th className="px-6 py-3">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {trendingPlayers.map((player) => (
                  <tr key={player.id} className="hover:bg-surface-50 cursor-pointer transition-colors">
                    <td className="px-6 py-4">
                      <span className="text-sm font-medium text-gray-900">{player.name}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="badge-blue">{player.team}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <FormBadge score={player.formScore} />
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="text-sm font-mono text-gray-700">{player.runs.toLocaleString()}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="text-sm font-mono text-gray-700">{player.strikeRate}</span>
                    </td>
                    <td className="px-6 py-4">
                      <TrendIcon trend={player.trend} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Team Rankings */}
        <div className="card">
          <div className="px-6 py-4 border-b border-surface-200">
            <h2 className="text-lg font-semibold text-gray-900">Team Rankings</h2>
            <p className="text-sm text-gray-500 mt-0.5">By overall strength</p>
          </div>
          <div className="divide-y divide-surface-100">
            {teamRankings.map((team, index) => (
              <div key={team.id} className="px-6 py-4 hover:bg-surface-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <span className="text-sm font-bold text-gray-400 w-6">
                      {index + 1}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{team.name}</p>
                      <p className="text-xs text-gray-500">{team.winRate}% win rate</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-brand-600">{team.strength}</p>
                    <p className="text-xs text-gray-500">strength</p>
                  </div>
                </div>
                {/* Strength bar */}
                <div className="mt-2 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 rounded-full"
                    style={{ width: `${team.strength}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Matches */}
        <div className="card">
          <div className="px-6 py-4 border-b border-surface-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Matches</h2>
            <p className="text-sm text-gray-500 mt-0.5">Latest results</p>
          </div>
          <div className="divide-y divide-surface-100">
            {recentMatches.map((match) => (
              <div key={match.id} className="px-6 py-4 hover:bg-surface-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-900">{match.teamA}</span>
                      <span className="text-xs text-gray-400">vs</span>
                      <span className="text-sm font-bold text-gray-900">{match.teamB}</span>
                      <span className="badge-amber">{match.format}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{match.date}</p>
                  </div>
                  <p className="text-sm text-brand-600 font-medium">{match.result}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Venue Insights */}
        <div className="card">
          <div className="px-6 py-4 border-b border-surface-200">
            <h2 className="text-lg font-semibold text-gray-900">Venue Insights</h2>
            <p className="text-sm text-gray-500 mt-0.5">Key venue analytics</p>
          </div>
          <div className="divide-y divide-surface-100">
            {venueInsights.map((venue) => (
              <div key={venue.name} className="px-6 py-4 hover:bg-surface-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{venue.name}</p>
                    <p className="text-xs text-gray-500">Avg 1st innings: {venue.avgScore}</p>
                  </div>
                  <div className="flex items-center gap-4 text-right">
                    <div>
                      <p className="text-sm font-bold text-emerald-600">{venue.chaseWinPct}%</p>
                      <p className="text-xs text-gray-500">chase win</p>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-brand-600">{venue.pacePct}%</p>
                      <p className="text-xs text-gray-500">pace wickets</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
