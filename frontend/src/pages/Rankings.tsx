import { useState } from 'react'


const sampleRankings = [
  { rank: 1, name: 'Suryakumar Yadav', country: 'IND', rating: 912, points: 2650, change: +3 },
  { rank: 2, name: 'Babar Azam', country: 'PAK', rating: 891, points: 2580, change: -1 },
  { rank: 3, name: 'Aiden Markram', country: 'SA', rating: 854, points: 2420, change: +2 },
  { rank: 4, name: 'Jos Buttler', country: 'ENG', rating: 842, points: 2385, change: -2 },
  { rank: 5, name: 'Aaron Finch', country: 'AUS', rating: 820, points: 2320, change: 0 },
  { rank: 6, name: 'Virat Kohli', country: 'IND', rating: 815, points: 2290, change: +1 },
  { rank: 7, name: 'David Miller', country: 'SA', rating: 798, points: 2240, change: -1 },
  { rank: 8, name: 'Rohit Sharma', country: 'IND', rating: 785, points: 2190, change: +4 },
  { rank: 9, name: 'Glenn Phillips', country: 'NZ', rating: 772, points: 2150, change: +2 },
  { rank: 10, name: 'Glenn Maxwell', country: 'AUS', rating: 768, points: 2130, change: -3 },
]

export default function Rankings() {
  const [format, setFormat] = useState('T20I')
  const [category, setCategory] = useState('batting')

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
          {['T20I', 'ODI', 'Test'].map(f => (
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

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-surface-50">
              <th className="px-6 py-3 w-16">Rank</th>
              <th className="px-6 py-3">Player</th>
              <th className="px-6 py-3">Country</th>
              <th className="px-6 py-3 text-right">Rating</th>
              <th className="px-6 py-3 text-right">Points</th>
              <th className="px-6 py-3 text-right">Change</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100">
            {sampleRankings.map((player) => (
              <tr key={player.rank} className="hover:bg-surface-50 transition-colors">
                <td className="px-6 py-4">
                  <span className={`text-sm font-bold ${
                    player.rank <= 3 ? 'text-brand-600' : 'text-gray-400'
                  }`}>
                    {player.rank}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{player.name}</td>
                <td className="px-6 py-4">
                  <span className="badge-blue">{player.country}</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className="text-sm font-bold text-gray-900">{player.rating}</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className="text-sm font-mono text-gray-700">{player.points.toLocaleString()}</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`text-sm font-medium ${
                    player.change > 0 ? 'text-emerald-600' :
                    player.change < 0 ? 'text-red-600' : 'text-gray-400'
                  }`}>
                    {player.change > 0 ? `+${player.change}` : player.change === 0 ? '—' : player.change}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
