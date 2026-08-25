import { useParams } from 'react-router-dom'
import { ArrowLeft, TrendingUp, Target, MapPin, Swords } from 'lucide-react'

const mockPlayer = {
  name: 'Suryakumar Yadav',
  fullName: 'Suryakumar Ashok Yadav',
  role: 'Batsman',
  country: 'India',
  battingStyle: 'Right-hand bat',
  formScore: 89.2,
  battingRating: 92.1,
  consistency: 76.5,
  career: {
    matches: 68,
    innings: 65,
    runs: 1842,
    average: 35.42,
    strikeRate: 147.5,
    highestScore: 117,
    fours: 155,
    sixes: 85,
    fifties: 12,
    hundreds: 2,
    notOuts: 13,
    ballsFaced: 1249,
  },
  phases: {
    powerplay: { balls: 245, runs: 348, strikeRate: 142.0, avg: 38.7 },
    middle: { balls: 480, runs: 672, strikeRate: 140.0, avg: 37.3 },
    death: { balls: 524, runs: 822, strikeRate: 156.9, avg: 41.1 },
  },
  recentForm: [
    { match: 'vs AUS', runs: 80, sr: 152.3, isOut: false },
    { match: 'vs ENG', runs: 45, sr: 138.5, isOut: true },
    { match: 'vs SA', runs: 92, sr: 161.4, isOut: false },
    { match: 'vs WI', runs: 112, sr: 172.3, isOut: false },
    { match: 'vs NZ', runs: 28, sr: 116.7, isOut: true },
    { match: 'vs PAK', runs: 67, sr: 144.6, isOut: true },
    { match: 'vs BAN', runs: 55, sr: 137.5, isOut: true },
    { match: 'vs SL', runs: 78, sr: 155.2, isOut: false },
  ],
  formComponents: {
    recentPerformance: { score: 92, weight: 0.35 },
    consistency: { score: 78, weight: 0.20 },
    oppositionStrength: { score: 85, weight: 0.15 },
    venuePerformance: { score: 82, weight: 0.10 },
    matchSituation: { score: 75, weight: 0.10 },
    efficiency: { score: 90, weight: 0.10 },
  },
}

function StatBox({ label, value, subtitle }: { label: string; value: string | number; subtitle?: string }) {
  return (
    <div className="text-center p-3 rounded-lg bg-surface-50">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs font-medium text-gray-500 mt-1">{label}</p>
      {subtitle && <p className="text-xs text-gray-400">{subtitle}</p>}
    </div>
  )
}

function FormComponentBar({ name, score, weight }: { name: string; score: number; weight: number }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-36 text-xs text-gray-600 truncate">{name}</div>
      <div className="flex-1 h-2 bg-surface-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-500 rounded-full transition-all"
          style={{ width: `${score}%` }}
        />
      </div>
      <div className="w-10 text-right">
        <span className="text-xs font-bold text-gray-900">{score}</span>
        <span className="text-xs text-gray-400 ml-0.5">×{(weight * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}

export default function PlayerDetail() {
  const { id: _id } = useParams()
  
  // In production, this would fetch from the API using the id
  const player = mockPlayer

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => window.history.back()}
        className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Players
      </button>

      {/* Player Header */}
      <div className="card p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{player.name}</h1>
            <p className="text-sm text-gray-500 mt-1">{player.fullName}</p>
            <div className="flex items-center gap-3 mt-2">
              <span className="badge-blue">{player.role}</span>
              <span className="badge-green">{player.country}</span>
              <span className="text-xs text-gray-400">{player.battingStyle}</span>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-brand-50 border-4 border-brand-500 flex items-center justify-center">
                <span className="text-2xl font-bold text-brand-700">{player.formScore}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Form Score</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-surface-50 border-2 border-surface-300 flex items-center justify-center">
                <span className="text-xl font-bold text-gray-700">{player.battingRating}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Rating</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-surface-50 border-2 border-surface-300 flex items-center justify-center">
                <span className="text-xl font-bold text-gray-700">{player.consistency}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Consistency</p>
            </div>
          </div>
        </div>
      </div>

      {/* Form Score Breakdown */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-gray-900">Form Score Breakdown</h2>
        </div>
        <div className="space-y-3">
          {Object.entries(player.formComponents).map(([key, component]) => {
            const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())
            return (
              <FormComponentBar
                key={key}
                name={label}
                score={component.score}
                weight={component.weight}
              />
            )
          })}
        </div>
        <p className="text-xs text-gray-400 mt-4">
          Form Score = Σ(component_score × weight). Each component is normalized 0-100 using min-max scaling across all players.
        </p>
      </div>

      {/* Career Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Career Batting</h2>
          <div className="grid grid-cols-4 gap-3">
            <StatBox label="Matches" value={player.career.matches} />
            <StatBox label="Innings" value={player.career.innings} />
            <StatBox label="Runs" value={player.career.runs.toLocaleString()} />
            <StatBox label="Average" value={player.career.average} />
            <StatBox label="Strike Rate" value={player.career.strikeRate} />
            <StatBox label="Highest" value={player.career.highestScore} />
            <StatBox label="Fours" value={player.career.fours} />
            <StatBox label="Sixes" value={player.career.sixes} />
            <StatBox label="50s" value={player.career.fifties} />
            <StatBox label="100s" value={player.career.hundreds} />
            <StatBox label="4s %" value={`${((player.career.fours * 4 / player.career.runs) * 100).toFixed(1)}%`} />
            <StatBox label="6s %" value={`${((player.career.sixes * 6 / player.career.runs) * 100).toFixed(1)}%`} />
          </div>
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Form</h2>
          <div className="space-y-2">
            {player.recentForm.map((match, idx) => (
              <div key={idx} className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-50">
                <span className="text-sm text-gray-500 w-16">{match.match}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="h-2 flex-1 bg-surface-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${match.isOut ? 'bg-amber-500' : 'bg-emerald-500'}`}
                        style={{ width: `${Math.min(match.runs / 1.2, 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-bold text-gray-900 w-10 text-right">
                      {match.runs}{match.isOut ? '' : '*'}
                    </span>
                    <span className="text-xs text-gray-400 w-14 text-right">SR {match.sr}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Phase Performance */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-gray-900">Phase Performance</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(player.phases).map(([phase, stats]) => (
            <div key={phase} className="p-4 rounded-lg bg-surface-50 border border-surface-200">
              <h3 className="text-sm font-semibold text-gray-700 capitalize mb-3">{phase}</h3>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-xs text-gray-500">Runs</p>
                  <p className="text-sm font-bold text-gray-900">{stats.runs}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Balls</p>
                  <p className="text-sm font-bold text-gray-900">{stats.balls}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Strike Rate</p>
                  <p className="text-sm font-bold text-gray-900">{stats.strikeRate}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Average</p>
                  <p className="text-sm font-bold text-gray-900">{stats.avg}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Placeholder sections for future features */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Performance by Venue</h2>
          </div>
          <p className="text-sm text-gray-500">Venue-wise performance breakdown will be displayed here.</p>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Swords className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Matchups</h2>
          </div>
          <p className="text-sm text-gray-500">Head-to-head matchup data will be displayed here.</p>
        </div>
      </div>
    </div>
  )
}
