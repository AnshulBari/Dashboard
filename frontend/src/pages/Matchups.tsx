import { Swords } from 'lucide-react'

const sampleMatchups = [
  { batter: 'Virat Kohli', bowler: 'Trent Boult', balls: 42, runs: 68, wickets: 1, sr: 161.9, avg: 68.0, dots: 12, boundaries: 8 },
  { batter: 'Babar Azam', bowler: 'Jasprit Bumrah', balls: 35, runs: 42, wickets: 2, sr: 120.0, avg: 21.0, dots: 14, boundaries: 4 },
  { batter: 'Jos Buttler', bowler: 'Rashid Khan', balls: 38, runs: 55, wickets: 1, sr: 144.7, avg: 55.0, dots: 10, boundaries: 6 },
  { batter: 'Suryakumar Yadav', bowler: 'Mitchell Starc', balls: 28, runs: 48, wickets: 0, sr: 171.4, avg: null, dots: 5, boundaries: 6 },
  { batter: 'David Warner', bowler: 'Mohammed Shami', balls: 32, runs: 38, wickets: 2, sr: 118.8, avg: 19.0, dots: 12, boundaries: 3 },
]

const typeMatchups = [
  { batter: 'Virat Kohli', type: 'vs Pace', balls: 850, runs: 1250, sr: 147.1, dots: 245, boundaries: 142 },
  { batter: 'Virat Kohli', type: 'vs Spin', balls: 520, runs: 680, sr: 130.8, dots: 168, boundaries: 65 },
  { batter: 'Babar Azam', type: 'vs Pace', balls: 920, runs: 1180, sr: 128.3, dots: 310, boundaries: 125 },
  { batter: 'Babar Azam', type: 'vs Spin', balls: 480, runs: 560, sr: 116.7, dots: 178, boundaries: 52 },
]

export default function Matchups() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Matchup Analytics</h1>
        <p className="page-subtitle">
          Head-to-head batter vs bowler data and contextual matchup breakdowns
        </p>
      </div>

      {/* Head-to-Head Matchups */}
      <div className="card mb-6">
        <div className="px-6 py-4 border-b border-surface-200">
          <div className="flex items-center gap-2">
            <Swords className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Head-to-Head Matchups</h2>
          </div>
          <p className="text-sm text-gray-500 mt-0.5">Minimum 10 balls for statistical significance</p>
        </div>
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
                <th className="px-6 py-3 text-right">Boundaries</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {sampleMatchups.map((m, idx) => (
                <tr key={idx} className="hover:bg-surface-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{m.batter}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{m.bowler}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.balls}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-900 font-bold">{m.runs}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.wickets}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.sr}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.avg ?? '—'}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.dots}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.boundaries}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Type Matchups */}
      <div className="card">
        <div className="px-6 py-4 border-b border-surface-200">
          <h2 className="text-lg font-semibold text-gray-900">Bowler Type Matchups</h2>
          <p className="text-sm text-gray-500 mt-0.5">Performance against pace vs spin</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <th className="px-6 py-3">Batter</th>
                <th className="px-6 py-3">Type</th>
                <th className="px-6 py-3 text-right">Balls</th>
                <th className="px-6 py-3 text-right">Runs</th>
                <th className="px-6 py-3 text-right">SR</th>
                <th className="px-6 py-3 text-right">Dots %</th>
                <th className="px-6 py-3 text-right">Boundaries</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {typeMatchups.map((m, idx) => (
                <tr key={idx} className="hover:bg-surface-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{m.batter}</td>
                  <td className="px-6 py-4">
                    <span className={`badge ${m.type === 'vs Pace' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}`}>
                      {m.type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.balls}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-900 font-bold">{m.runs}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.sr}</td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">
                    {((m.dots / m.balls) * 100).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-mono text-gray-700">{m.boundaries}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
