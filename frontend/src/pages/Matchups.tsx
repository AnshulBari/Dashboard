import { useState, useEffect } from 'react'
import { Swords } from 'lucide-react'
import { matchupApi } from '../services/api'

interface MatchupRow {
  batter_id: string
  bowler_id: string
  batter_name: string
  bowler_name: string
  total_balls: number
  total_runs: number
  total_wickets: number
  strike_rate: number
  batting_average: number | null
  dot_balls: number
  boundaries: number
  sixes: number
}

export default function Matchups() {
  const [matchups, setMatchups] = useState<MatchupRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await matchupApi.list({ format: 'T20', limit: 20 }) as { matchups: MatchupRow[] }
        setMatchups(res.matchups || [])
      } catch (err) {
        console.error('Failed to load matchups:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Matchup Analytics</h1>
        <p className="page-subtitle">
          Head-to-head batter vs bowler data derived from ball-by-ball records
        </p>
      </div>

      {/* Head-to-Head Matchups */}
      <div className="card mb-6">
        <div className="px-6 py-4 border-b border-surface-200">
          <div className="flex items-center gap-2">
            <Swords className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Top Head-to-Head Matchups</h2>
          </div>
          <p className="text-sm text-gray-500 mt-0.5">Minimum 10 balls for statistical significance — ranked by total runs scored</p>
        </div>
        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading matchups...</div>
        ) : matchups.length === 0 ? (
          <div className="p-6 text-center text-gray-500">No matchup data available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-6 py-3">Batter</th>
                  <th className="px-6 py-3">Bowler</th>
                  <th className="px-6 py-3 text-right">Balls</th>
                  <th className="px-6 py-3 text-right">Runs</th>
                  <th className="px-6 py-3 text-right">Wickets</th>
                  <th className="px-6 py-3 text-right">SR</th>
                  <th className="px-6 py-3 text-right">Avg</th>
                  <th className="px-6 py-3 text-right">Dots</th>
                  <th className="px-6 py-3 text-right">4s</th>
                  <th className="px-6 py-3 text-right">6s</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {matchups.map((m, idx) => (
                  <tr key={idx} className="hover:bg-surface-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{m.batter_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-700">{m.bowler_name}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.total_balls}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-900 font-bold">{m.total_runs}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.total_wickets}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.strike_rate?.toFixed(1) || '-'}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.batting_average?.toFixed(1) || '—'}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.dot_balls}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.boundaries}</td>
                    <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.sixes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
