

const sampleMatches = [
  { id: '1', format: 'T20I', date: '2024-01-15', teamA: 'IND', teamB: 'AUS', venue: 'MCG', result: 'India won by 7 wickets', score: '179/3 vs 176/8' },
  { id: '2', format: 'T20I', date: '2024-01-14', teamA: 'ENG', teamB: 'SA', venue: 'Newlands', result: 'England won by 12 runs', score: '192/5 vs 180/10' },
  { id: '3', format: 'T20I', date: '2024-01-13', teamA: 'PAK', teamB: 'NZ', venue: 'Eden Park', result: 'New Zealand won by 3 wickets', score: '165/8 vs 166/7' },
  { id: '4', format: 'ODI', date: '2024-01-12', teamA: 'IND', teamB: 'SL', venue: 'Wankhede', result: 'India won by 108 runs', score: '312/4 vs 204/10' },
  { id: '5', format: 'T20I', date: '2024-01-11', teamA: 'AUS', teamB: 'ENG', venue: 'Gabba', result: 'Australia won by 5 wickets', score: '188/5 vs 185/8' },
  { id: '6', format: 'Test', date: '2024-01-10', teamA: 'IND', teamB: 'ENG', venue: 'Lords', result: 'Match drawn', score: '345 & 280 vs 310 & 250/6' },
]

export default function Matches() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Matches</h1>
        <p className="page-subtitle">
          Match results and historical data
        </p>
      </div>

      <div className="space-y-3">
        {sampleMatches.map((match) => (
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
                    <span className="text-sm font-bold text-gray-900">{match.teamA}</span>
                    <span className="text-xs text-gray-400">vs</span>
                    <span className="text-sm font-bold text-gray-900">{match.teamB}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-gray-400">{match.date}</span>
                    <span className="text-xs text-gray-400">·</span>
                    <span className="text-xs text-gray-400">{match.venue}</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-brand-600">{match.result}</p>
                <p className="text-xs font-mono text-gray-500 mt-0.5">{match.score}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
