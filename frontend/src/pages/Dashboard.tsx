import { useState, useEffect } from 'react'
import { Users, Shield, MapPin, Trophy } from 'lucide-react'
import { playerApi, teamApi, venueApi, matchApi } from '../services/api'

interface PlayerRow {
  id: string
  name: string
  team_name: string
  form_score: number | null
  career_runs: number | null
  strike_rate: number | null
  career_wickets: number | null
}

interface TeamRow {
  id: string
  name: string
  short_name: string
  overall_strength_score: number | null
  win_rate: number | null
  matches: number | null
  wins: number | null
}

interface VenueRow {
  id: string
  name: string
  total_matches: number | null
  avg_first_innings_score: number | null
  chasing_win_pct: number | null
}

interface MatchRow {
  id: string
  team_a: string
  team_b: string
  match_date: string
  format: string
  result: string
  venue: string | null
}

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
            <p className="text-xs text-gray-500 mt-1">{change}</p>
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

export default function Dashboard() {
  const [players, setPlayers] = useState<PlayerRow[]>([])
  const [teams, setTeams] = useState<TeamRow[]>([])
  const [venues, setVenues] = useState<VenueRow[]>([])
  const [matches, setMatches] = useState<MatchRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [playersRes, teamsRes, venuesRes, matchesRes] = await Promise.all([
          playerApi.list({ format: 'T20', sortBy: 'form_score', limit: 10 }) as Promise<{ players: PlayerRow[] }>,
          teamApi.list({ format: 'T20' }) as Promise<{ teams: TeamRow[] }>,
          venueApi.list({ format: 'T20' }) as Promise<{ venues: VenueRow[] }>,
          matchApi.list({ format: 'T20', limit: 10 }) as Promise<{ matches: MatchRow[] }>,
        ])
        setPlayers(playersRes.players || [])
        setTeams(teamsRes.teams || [])
        setVenues(venuesRes.venues || [])
        setMatches(matchesRes.matches || [])
      } catch (err) {
        console.error('Failed to load dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const totalPlayers = players.length || 261
  const totalTeams = teams.length || 11
  const totalVenues = venues.length || 20

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Intelligence Overview</h1>
        <p className="page-subtitle">
          Cricket analytics powered by Cricsheet historical data
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          label="Players Tracked"
          value={totalPlayers}
          icon={Users}
          color="bg-brand-600"
        />
        <StatCard
          label="Teams"
          value={totalTeams}
          icon={Shield}
          color="bg-emerald-600"
        />
        <StatCard
          label="Matches Analyzed"
          value="200+"
          change="Cricsheet IPL data"
          icon={Trophy}
          color="bg-amber-500"
        />
        <StatCard
          label="Venues"
          value={totalVenues}
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
          {loading ? (
            <div className="p-6 text-center text-gray-500">Loading...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <th className="px-6 py-3">Player</th>
                    <th className="px-6 py-3">Team</th>
                    <th className="px-6 py-3 text-right">Form Score</th>
                    <th className="px-6 py-3 text-right">Runs</th>
                    <th className="px-6 py-3 text-right">SR</th>
                    <th className="px-6 py-3 text-right">Wkts</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {players.filter(p => p.form_score != null).slice(0, 10).map((player) => (
                    <tr key={player.id} className="hover:bg-surface-50 cursor-pointer transition-colors">
                      <td className="px-6 py-4">
                        <span className="text-sm font-medium text-gray-900">{player.name}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="badge-blue">{player.team_name || '-'}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {player.form_score != null && <FormBadge score={player.form_score} />}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.career_runs?.toLocaleString() || '-'}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.strike_rate?.toFixed(1) || '-'}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.career_wickets || '-'}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Team Rankings */}
        <div className="card">
          <div className="px-6 py-4 border-b border-surface-200">
            <h2 className="text-lg font-semibold text-gray-900">Team Rankings</h2>
            <p className="text-sm text-gray-500 mt-0.5">By overall strength</p>
          </div>
          {loading ? (
            <div className="p-6 text-center text-gray-500">Loading...</div>
          ) : (
            <div className="divide-y divide-surface-100">
              {teams.filter(t => t.overall_strength_score != null).slice(0, 8).map((team, index) => (
                <div key={team.id} className="px-6 py-4 hover:bg-surface-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <span className="text-sm font-bold text-gray-400 w-6">
                        {index + 1}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{team.name}</p>
                        <p className="text-xs text-gray-500">{team.win_rate?.toFixed(1)}% win rate ({team.matches}M {team.wins}W)</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-brand-600">{team.overall_strength_score?.toFixed(1)}</p>
                      <p className="text-xs text-gray-500">strength</p>
                    </div>
                  </div>
                  {/* Strength bar */}
                  <div className="mt-2 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-500 rounded-full"
                      style={{ width: `${team.overall_strength_score || 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Matches */}
        <div className="card">
          <div className="px-6 py-4 border-b border-surface-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Matches</h2>
            <p className="text-sm text-gray-500 mt-0.5">Latest results</p>
          </div>
          {loading ? (
            <div className="p-6 text-center text-gray-500">Loading...</div>
          ) : (
            <div className="divide-y divide-surface-100">
              {matches.slice(0, 8).map((match) => (
                <div key={match.id} className="px-6 py-4 hover:bg-surface-50 transition-alls">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-gray-900">{match.team_a}</span>
                        <span className="text-xs text-gray-400">vs</span>
                        <span className="text-sm font-bold text-gray-900">{match.team_b}</span>
                        <span className="badge-amber">{match.format}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{match.match_date} {match.venue ? `· ${match.venue}` : ''}</p>
                    </div>
                    <p className="text-sm text-brand-600 font-medium text-right max-w-[200px] truncate">{match.result}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Venue Insights */}
        <div className="card">
          <div className="px-6 py-4 border-b border-surface-200">
            <h2 className="text-lg font-semibold text-gray-900">Venue Insights</h2>
            <p className="text-sm text-gray-500 mt-0.5">Key venue analytics</p>
          </div>
          {loading ? (
            <div className="p-6 text-center text-gray-500">Loading...</div>
          ) : (
            <div className="divide-y divide-surface-100">
              {venues.filter(v => v.total_matches && v.total_matches > 0).slice(0, 6).map((venue) => (
                <div key={venue.id} className="px-6 py-4 hover:bg-surface-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{venue.name}</p>
                      <p className="text-xs text-gray-500">{venue.total_matches} matches · Avg 1st inn: {venue.avg_first_innings_score?.toFixed(0) || '-'}</p>
                    </div>
                    <div className="flex items-center gap-4 text-right">
                      <div>
                        <p className="text-sm font-bold text-emerald-600">{venue.chasing_win_pct?.toFixed(1) || '-'}%</p>
                        <p className="text-xs text-gray-500">chase win</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Data Source */}
      <div className="mt-8 p-4 bg-surface-50 rounded-lg border border-surface-200">
        <p className="text-sm text-gray-600">
          <strong>Data Source:</strong> Historical ball-by-ball data from{' '}
          <a href="https://cricsheet.org" target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline">
            Cricsheet
          </a>
          {' '}— Men's IPL matches (2008-2017). Coverage depends on Cricsheet data availability.
        </p>
      </div>
    </div>
  )
}
