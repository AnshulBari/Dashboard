import { MapPin } from 'lucide-react'

const sampleVenues = [
  { id: '1', name: 'Melbourne Cricket Ground', city: 'Melbourne', country: 'Australia', matches: 85, avgScore: 168, chaseWinPct: 55, pacePct: 58 },
  { id: '2', name: 'Eden Gardens', city: 'Kolkata', country: 'India', matches: 72, avgScore: 172, chaseWinPct: 52, pacePct: 52 },
  { id: '3', name: 'Dubai International Cricket Stadium', city: 'Dubai', country: 'UAE', matches: 68, avgScore: 158, chaseWinPct: 58, pacePct: 60 },
  { id: '4', name: 'The Oval', city: 'London', country: 'England', matches: 65, avgScore: 162, chaseWinPct: 48, pacePct: 55 },
  { id: '5', name: 'Lords', city: 'London', country: 'England', matches: 60, avgScore: 155, chaseWinPct: 45, pacePct: 58 },
  { id: '6', name: 'Wankhede Stadium', city: 'Mumbai', country: 'India', matches: 55, avgScore: 175, chaseWinPct: 54, pacePct: 56 },
]

export default function Venues() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Venue Intelligence</h1>
        <p className="page-subtitle">
          How different grounds play — batting paradise, pace-friendly, or spin heaven
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sampleVenues.map((venue) => (
          <div key={venue.id} className="card-hover p-5 cursor-pointer">
            <div className="flex items-start gap-3 mb-4">
              <MapPin className="h-5 w-5 text-brand-600 mt-0.5" />
              <div>
                <h3 className="text-base font-semibold text-gray-900">{venue.name}</h3>
                <p className="text-sm text-gray-500">{venue.city}, {venue.country}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div>
                <p className="text-xs text-gray-500">Matches</p>
                <p className="text-sm font-bold text-gray-900">{venue.matches}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Avg 1st Innings</p>
                <p className="text-sm font-bold text-gray-900">{venue.avgScore}</p>
              </div>
            </div>

            <div className="space-y-2">
              <div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Chase Win %</span>
                  <span className="font-medium text-gray-700">{venue.chaseWinPct}%</span>
                </div>
                <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden mt-1">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${venue.chaseWinPct}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Pace Wickets %</span>
                  <span className="font-medium text-gray-700">{venue.pacePct}%</span>
                </div>
                <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden mt-1">
                  <div
                    className="h-full bg-brand-500 rounded-full"
                    style={{ width: `${venue.pacePct}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
