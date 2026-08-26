import { useState, useEffect } from 'react'
import { rankingApi } from '../services/api'

interface RankingRow {
  id: string
  rank: number
  name: string
  country: string | null
  team: string | null
  rating: number | null
  runs: number | null
  wickets: number | null
  batting_average: number | null
  strike_rate: number | null
  economy: number | null
  form_score: number | null
}

export default function Rankings() {
  const [format, setFormat] = useState('T20')
  const [category, setCategory] = useState('batting')
  const [rankings, setRankings] = useState<RankingRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const res = await rankingApi.get(format, category) as { rankings: RankingRow[] }
        setRankings(res.rankings || [])
      } catch (err) {
        console.error('Failed to load rankings:', err)
        setRankings([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [format, category])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Rankings</h1>
        <p className="page-subtitle">
          Platform-computed player rankings based on our analytics
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Format:</span>
          {['T20', 'T20I', 'ODI', 'Test'].map(f => (
            <button
              key={f}
              onClick={() => setFormat(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                format === f ? 'bg-brand-100 text-brand-700' : 'bg-surface-100 text-gray-600 hover:bg-surface-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Category:</span>
          {['batting', 'bowling', 'allrounder'].map(c => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                category === c ? 'bg-brand-100 text-brand-700' : 'bg-surface-100 text-gray-600 hover:bg-surface-200'
              }`}
            >
              {c.charAt(0).toUpperCase() + c.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading rankings...</div>
      ) : rankings.length === 0 ? (
        <div className="text-center py-12 text-gray-500">No rankings available for this format/category</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-surface-50">
                <th className="px-6 py-3 w-16">Rank</th>
                <th className="px-6 py-3">Player</th>
                <th className="px-6 py-3">Team</th>
                <th className="px-6 py-3 text-right">Rating</th>
                {category === 'batting' && <th className="px-6 py-3 text-right">Runs</th>}
                {category === 'batting' && <th className="px-6 py-3 text-right">Avg</th>}
                {category === 'batting' && <th className="px-6 py-3 text-right">SR</th>}
                {category === 'bowling' && <th className="px-6 py-3 text-right">Wkts</th>}
                {category === 'bowling' && <th className="px-6 py-3 text-right">Econ</th>}
                {category === 'bowling' && <th className="px-6 py-3 text-right">Avg</th>}
                <th className="px-6 py-3 text-right">Form</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {rankings.map((player) => (
                <tr key={player.id} className="hover:bg-surface-50 transition-colors">
                  <td className="px-6 py-4">
                    <span className={`text-sm font-bold ${
                      player.rank <= 3 ? 'text-brand-600' : 'text-gray-400'
                    }`}>
                      {player.rank}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{player.name}</td>
                  <td className="px-6 py-4">
                    <span className="badge-blue">{player.team || player.country || '-'}</span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="text-sm font-bold text-gray-900">{player.rating?.toFixed(1) || '-'}</span>
                  </td>
                  {category === 'batting' && (
                    <>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.runs?.toLocaleString() || '-'}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.batting_average?.toFixed(1) || '-'}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.strike_rate?.toFixed(1) || '-'}</span>
                      </td>
                    </>
                  )}
                  {category === 'bowling' && (
                    <>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.wickets || '-'}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.economy?.toFixed(2) || '-'}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm font-mono text-gray-700">{player.batting_average?.toFixed(1) || '-'}</span>
                      </td>
                    </>
                  )}
                  <td className="px-6 py-4 text-right">
                    {player.form_score != null ? (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
                        player.form_score >= 70 ? 'bg-emerald-100 text-emerald-800' :
                        player.form_score >= 50 ? 'bg-blue-100 text-blue-800' :
                        'bg-amber-100 text-amber-800'
                      }`}>
                        {player.form_score.toFixed(1)}
                      </span>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
