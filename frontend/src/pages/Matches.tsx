import { useState, useEffect } from 'react'
import { matchApi } from '../services/api'

interface MatchRow {
  id: string
  match_date: string
  format: string
  win_margin: number | null
  win_type: string | null
  team_a: string | null
  team_b: string | null
  winner: string | null
  venue: string | null
  toss_decision: string | null
  result: string
}

export default function Matches() {
  const [matches, setMatches] = useState<MatchRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await matchApi.list({ format: 'T20', limit: 50 }) as { matches: MatchRow[] }
        setMatches(res.matches || [])
      } catch (err) {
        console.error('Failed to load matches:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Matches</h1>
        <p className="page-subtitle">
          Match results and historical data
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading matches...</div>
      ) : (
        <div className="space-y-3">
          {matches.map((match) => (
            <div key={match.id} className="card-hover p-5">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <span className={`badge ${
                      match.format === 'T20I' ? 'bg-blue-100 text-blue-800' :
                      match.format === 'ODI' ? 'bg-emerald-100 text-emerald-800' :
                      'bg-amber-100 text-amber-800'
                    }`}>
                      {match.format}
                    </span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-900">{match.team_a || 'TBD'}</span>
                      <span className="text-xs text-gray-400">vs</span>
                      <span className="text-sm font-bold text-gray-900">{match.team_b || 'TBD'}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-gray-400">{match.match_date}</span>
                      {match.venue && (
                        <>
                          <span className="text-xs text-gray-400">·</span>
                          <span className="text-xs text-gray-400">{match.venue}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-brand-600">{match.result}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
