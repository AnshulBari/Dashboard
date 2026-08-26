import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { teamApi } from '../services/api'

interface TeamRow {
  id: string
  name: string
  short_name: string
  country: string | null
  overall_strength_score: number | null
  batting_strength_score: number | null
  bowling_strength_score: number | null
  win_rate: number | null
  matches: number | null
  wins: number | null
}

export default function Teams() {
  const [teams, setTeams] = useState<TeamRow[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    async function load() {
      try {
        const res = await teamApi.list({ format: 'T20' }) as { teams: TeamRow[] }
        setTeams(res.teams || [])
      } catch (err) {
        console.error('Failed to load teams:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Team Intelligence</h1>
        <p className="page-subtitle">
          Team strength ratings, performance analytics, and competitive insights
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading teams...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {teams.map((team, index) => (
            <div
              key={team.id}
              onClick={() => navigate(`/teams/${team.id}`)}
              className="card-hover p-5 cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-gray-300 w-6">#{index + 1}</span>
                  <div>
                    <h3 className="text-base font-semibold text-gray-900">{team.name}</h3>
                    <p className="text-sm text-gray-500">{team.short_name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-brand-600">{team.overall_strength_score?.toFixed(1) || '-'}</p>
                  <p className="text-xs text-gray-500">strength</p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-4 gap-3">
                <div>
                  <p className="text-xs text-gray-500">Win Rate</p>
                  <p className="text-sm font-bold text-gray-900">{team.win_rate?.toFixed(1) || '-'}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Matches</p>
                  <p className="text-sm font-bold text-gray-900">{team.matches || '-'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Batting</p>
                  <p className="text-sm font-bold text-emerald-600">{team.batting_strength_score?.toFixed(1) || '-'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Bowling</p>
                  <p className="text-sm font-bold text-brand-600">{team.bowling_strength_score?.toFixed(1) || '-'}</p>
                </div>
              </div>

              {/* Strength bars */}
              <div className="mt-3 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-14">Batting</span>
                  <div className="flex-1 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${team.batting_strength_score || 0}%` }} />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-14">Bowling</span>
                  <div className="flex-1 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-500 rounded-full" style={{ width: `${team.bowling_strength_score || 0}%` }} />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
