import { useParams } from 'react-router-dom'
import { ArrowLeft, TrendingUp, Activity } from 'lucide-react'

const mockTeam = {
  name: 'India',
  shortName: 'IND',
  country: 'India',
  overallStrength: 91.2,
  battingStrength: 94.5,
  bowlingStrength: 87.8,
  winRate: 72.5,
  performance: {
    matches: 45, wins: 33, losses: 10, ties: 1, noResults: 1,
    avgFirstInnings: 178, avgSecondInnings: 168,
    avgPowerplay: 48, avgMiddle: 62, avgDeath: 68,
  },
  bowling: {
    avgEconomy: 7.2, powerplayEconomy: 6.5,
    middleEconomy: 7.0, deathEconomy: 9.2,
  },
  situational: {
    chasingWinPct: 68.5, defendingWinPct: 76.2,
  },
  recentResults: [
    { opponent: 'AUS', result: 'Won', margin: '7 wickets', date: '2024-01-15' },
    { opponent: 'ENG', result: 'Won', margin: '15 runs', date: '2024-01-12' },
    { opponent: 'SA', result: 'Lost', margin: '8 runs', date: '2024-01-08' },
    { opponent: 'NZ', result: 'Won', margin: '6 wickets', date: '2024-01-05' },
    { opponent: 'PAK', result: 'Won', margin: '5 wickets', date: '2024-01-01' },
  ],
}

export default function TeamDetail() {
  const { id: _id } = useParams()

  return (
    <div>
      <button
        onClick={() => window.history.back()}
        className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Teams
      </button>

      {/* Team Header */}
      <div className="card p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{mockTeam.name}</h1>
            <p className="text-sm text-gray-500 mt-1">{mockTeam.country}</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-brand-50 border-4 border-brand-500 flex items-center justify-center">
                <span className="text-2xl font-bold text-brand-700">{mockTeam.overallStrength}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Overall</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-50 border-2 border-emerald-400 flex items-center justify-center">
                <span className="text-xl font-bold text-emerald-700">{mockTeam.battingStrength}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Batting</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-blue-50 border-2 border-blue-400 flex items-center justify-center">
                <span className="text-xl font-bold text-blue-700">{mockTeam.bowlingStrength}</span>
              </div>
              <p className="text-xs font-medium text-gray-500 mt-2">Bowling</p>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        {[
          { label: 'Matches', value: mockTeam.performance.matches },
          { label: 'Wins', value: mockTeam.performance.wins },
          { label: 'Losses', value: mockTeam.performance.losses },
          { label: 'Win Rate', value: `${mockTeam.winRate}%` },
          { label: 'Avg 1st Innings', value: mockTeam.performance.avgFirstInnings },
        ].map((stat) => (
          <div key={stat.label} className="card p-4 text-center">
            <p className="text-xl font-bold text-gray-900">{stat.value}</p>
            <p className="text-xs text-gray-500 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Phase Performance */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Phase Performance</h2>
          </div>
          <div className="space-y-4">
            {[
              { name: 'Powerplay', runs: mockTeam.performance.avgPowerplay, econ: mockTeam.bowling.powerplayEconomy, color: 'bg-blue-500' },
              { name: 'Middle Overs', runs: mockTeam.performance.avgMiddle, econ: mockTeam.bowling.middleEconomy, color: 'bg-amber-500' },
              { name: 'Death Overs', runs: mockTeam.performance.avgDeath, econ: mockTeam.bowling.deathEconomy, color: 'bg-red-500' },
            ].map((phase) => (
              <div key={phase.name} className="p-3 rounded-lg bg-surface-50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">{phase.name}</span>
                  <span className={`w-2 h-2 rounded-full ${phase.color}`} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-gray-500">Avg Runs</p>
                    <p className="text-sm font-bold text-gray-900">{phase.runs}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Economy</p>
                    <p className="text-sm font-bold text-gray-900">{phase.econ}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Situational */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-gray-900">Situational Performance</h2>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="p-4 rounded-lg bg-emerald-50 text-center">
              <p className="text-3xl font-bold text-emerald-700">{mockTeam.situational.chasingWinPct}%</p>
              <p className="text-sm text-gray-600 mt-1">Chasing Win %</p>
            </div>
            <div className="p-4 rounded-lg bg-blue-50 text-center">
              <p className="text-3xl font-bold text-blue-700">{mockTeam.situational.defendingWinPct}%</p>
              <p className="text-sm text-gray-600 mt-1">Defending Win %</p>
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Recent Results</h3>
            <div className="space-y-2">
              {mockTeam.recentResults.map((result, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-50">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${result.result === 'Won' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                    <span className="text-sm font-medium text-gray-900">vs {result.opponent}</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-sm font-medium ${result.result === 'Won' ? 'text-emerald-600' : 'text-red-600'}`}>
                      {result.result}
                    </span>
                    <span className="text-xs text-gray-400 ml-2">{result.margin}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
