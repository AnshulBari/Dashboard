import { useParams } from 'react-router-dom'
import { ArrowLeft, MapPin } from 'lucide-react'

const mockVenue = {
  name: 'Melbourne Cricket Ground',
  city: 'Melbourne',
  country: 'Australia',
  capacity: 100024,
  matches: 85,
  avgFirstInnings: 168.5,
  avgSecondInnings: 155.2,
  highestTotal: 223,
  lowestTotal: 78,
  chasingWinPct: 55.0,
  defendingWinPct: 45.0,
  avgPowerplay: 42.5,
  avgMiddle: 58.2,
  avgDeath: 67.8,
  paceWicketsPct: 58.0,
  spinWicketsPct: 42.0,
  boundaryFrequency: 15.8,
  tossBatFirstWinPct: 48.5,
  tossFieldFirstWinPct: 51.5,
}

export default function VenueDetail() {
  const { id: _id } = useParams()

  return (
    <div>
      <button
        onClick={() => window.history.back()}
        className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Venues
      </button>

      {/* Venue Header */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-3 mb-2">
          <MapPin className="h-6 w-6 text-brand-600" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{mockVenue.name}</h1>
            <p className="text-sm text-gray-500">{mockVenue.city}, {mockVenue.country}</p>
          </div>
        </div>
        <p className="text-sm text-gray-400">Capacity: {mockVenue.capacity.toLocaleString()}</p>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{mockVenue.matches}</p>
          <p className="text-xs text-gray-500">Matches</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-emerald-600">{mockVenue.avgFirstInnings}</p>
          <p className="text-xs text-gray-500">Avg 1st Innings</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-blue-600">{mockVenue.avgSecondInnings}</p>
          <p className="text-xs text-gray-500">Avg 2nd Innings</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-amber-600">{mockVenue.chasingWinPct}%</p>
          <p className="text-xs text-gray-500">Chase Win %</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score Profile */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Score Profile</h2>
          <div className="space-y-3">
            {[
              { label: 'Highest Total', value: mockVenue.highestTotal, color: 'text-emerald-600' },
              { label: 'Lowest Total', value: mockVenue.lowestTotal, color: 'text-red-600' },
              { label: 'Avg 1st Innings', value: mockVenue.avgFirstInnings, color: '' },
              { label: 'Avg 2nd Innings', value: mockVenue.avgSecondInnings, color: '' },
            ].map((stat) => (
              <div key={stat.label} className="flex items-center justify-between p-2 rounded-lg bg-surface-50">
                <span className="text-sm text-gray-600">{stat.label}</span>
                <span className={`text-sm font-bold ${stat.color || 'text-gray-900'}`}>{stat.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pace vs Spin */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Pace vs Spin</h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">Pace Wickets</span>
                <span className="text-sm font-bold text-gray-900">{mockVenue.paceWicketsPct}%</span>
              </div>
              <div className="h-3 bg-surface-100 rounded-full overflow-hidden">
                <div className="h-full bg-red-500 rounded-full" style={{ width: `${mockVenue.paceWicketsPct}%` }} />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">Spin Wickets</span>
                <span className="text-sm font-bold text-gray-900">{mockVenue.spinWicketsPct}%</span>
              </div>
              <div className="h-3 bg-surface-100 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: `${mockVenue.spinWicketsPct}%` }} />
              </div>
            </div>
          </div>

          <h2 className="text-lg font-semibold text-gray-900 mt-6 mb-4">Phase Scoring</h2>
          <div className="space-y-3">
            {[
              { phase: 'Powerplay', runs: mockVenue.avgPowerplay },
              { phase: 'Middle Overs', runs: mockVenue.avgMiddle },
              { phase: 'Death Overs', runs: mockVenue.avgDeath },
            ].map((phase) => (
              <div key={phase.phase} className="flex items-center justify-between p-2 rounded-lg bg-surface-50">
                <span className="text-sm text-gray-600">{phase.phase}</span>
                <span className="text-sm font-bold text-gray-900">{phase.runs}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
