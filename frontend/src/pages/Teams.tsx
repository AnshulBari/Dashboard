import { useNavigate } from 'react-router-dom'

const sampleTeams = [
  { id: '1', name: 'India', shortName: 'IND', country: 'India', strength: 91.2, winRate: 72.5, matches: 45, batting: 94.5, bowling: 87.8 },
  { id: '2', name: 'England', shortName: 'ENG', country: 'England', strength: 85.8, winRate: 68.3, matches: 42, batting: 90.2, bowling: 81.3 },
  { id: '3', name: 'Australia', shortName: 'AUS', country: 'Australia', strength: 84.5, winRate: 65.2, matches: 38, batting: 86.7, bowling: 82.1 },
  { id: '4', name: 'Pakistan', shortName: 'PAK', country: 'Pakistan', strength: 80.1, winRate: 62.8, matches: 40, batting: 82.5, bowling: 77.8 },
  { id: '5', name: 'South Africa', shortName: 'SA', country: 'South Africa', strength: 78.9, winRate: 60.5, matches: 36, batting: 79.2, bowling: 78.5 },
  { id: '6', name: 'New Zealand', shortName: 'NZ', country: 'New Zealand', strength: 77.5, winRate: 59.2, matches: 34, batting: 75.8, bowling: 79.1 },
  { id: '7', name: 'West Indies', shortName: 'WI', country: 'West Indies', strength: 68.3, winRate: 48.5, matches: 32, batting: 72.5, bowling: 64.0 },
  { id: '8', name: 'Bangladesh', shortName: 'BAN', country: 'Bangladesh', strength: 62.1, winRate: 42.3, matches: 30, batting: 60.2, bowling: 64.0 },
]

export default function Teams() {
  const navigate = useNavigate()

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Team Intelligence</h1>
        <p className="page-subtitle">
          Team strength ratings, performance analytics, and competitive insights
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sampleTeams.map((team, index) => (
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
                  <p className="text-sm text-gray-500">{team.country}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-brand-600">{team.strength}</p>
                <p className="text-xs text-gray-500">strength</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-4 gap-3">
              <div>
                <p className="text-xs text-gray-500">Win Rate</p>
                <p className="text-sm font-bold text-gray-900">{team.winRate}%</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Matches</p>
                <p className="text-sm font-bold text-gray-900">{team.matches}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Batting</p>
                <p className="text-sm font-bold text-emerald-600">{team.batting}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Bowling</p>
                <p className="text-sm font-bold text-brand-600">{team.bowling}</p>
              </div>
            </div>

            {/* Strength bars */}
            <div className="mt-3 space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400 w-14">Batting</span>
                <div className="flex-1 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${team.batting}%` }} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400 w-14">Bowling</span>
                <div className="flex-1 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                  <div className="h-full bg-brand-500 rounded-full" style={{ width: `${team.bowling}%` }} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
