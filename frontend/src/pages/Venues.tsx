import { useState, useEffect } from 'react'
import { MapPin } from 'lucide-react'
import { venueApi } from '../services/api'

interface VenueRow {
  id: string
  name: string
  city: string | null
  country: string | null
  total_matches: number | null
  avg_first_innings_score: number | null
  chasing_win_pct: number | null
  pace_wickets_pct: number | null
}

export default function Venues() {
  const [venues, setVenues] = useState<VenueRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await venueApi.list({ format: 'T20' }) as { venues: VenueRow[] }
        setVenues(res.venues || [])
      } catch (err) {
        console.error('Failed to load venues:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Venue Intelligence</h1>
        <p className="page-subtitle">
          How different grounds play — batting paradise, pace-friendly, or spin heaven
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading venues...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {venues.map((venue) => (
            <div key={venue.id} className="card-hover p-5 cursor-pointer">
              <div className="flex items-start gap-3 mb-4">
                <MapPin className="h-5 w-5 text-brand-600 mt-0.5" />
                <div>
                  <h3 className="text-base font-semibold text-gray-900">{venue.name}</h3>
                  <p className="text-sm text-gray-500">{venue.city || 'Unknown'}{venue.country ? `, ${venue.country}` : ''}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <p className="text-xs text-gray-500">Matches</p>
                  <p className="text-sm font-bold text-gray-900">{venue.total_matches || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Avg 1st Innings</p>
                  <p className="text-sm font-bold text-gray-900">{venue.avg_first_innings_score?.toFixed(0) || '-'}</p>
                </div>
              </div>

              <div className="space-y-2">
                <div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Chase Win %</span>
                    <span className="font-medium text-gray-700">{venue.chasing_win_pct?.toFixed(1) || '-'}%</span>
                  </div>
                  <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden mt-1">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${venue.chasing_win_pct || 0}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Pace Wickets %</span>
                    <span className="font-medium text-gray-700">{venue.pace_wickets_pct?.toFixed(1) || '-'}%</span>
                  </div>
                  <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden mt-1">
                    <div
                      className="h-full bg-brand-500 rounded-full"
                      style={{ width: `${venue.pace_wickets_pct || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
