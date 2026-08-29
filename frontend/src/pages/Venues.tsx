import { useOutletContext } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import { useVenueList } from '@/hooks/useQueries'
import { SkeletonCard } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

interface PageContext {
  format: string
}

export default function Venues() {
  const { format } = useOutletContext<PageContext>()
  const { data, isLoading, isError, refetch } = useVenueList({ 
    format: format === 'All' ? 'T20' : format 
  })

  const venues = data?.venues || []

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Venues</h1>
        <p className="page-subtitle">
          Venue intelligence · {format === 'All' ? 'T20' : format}
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : isError ? (
        <ErrorCard message="Failed to load venues" onRetry={() => refetch()} />
      ) : venues.length === 0 ? (
        <EmptyState 
          icon={<MapPin className="h-10 w-10 text-gray-600" />}
          title="No venues found" 
          message="No venue data available for this selection." 
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {venues.map((venue) => (
            <Link
              key={venue.id}
              to={`/venues/${venue.id}`}
              className="card-glow p-4"
            >
              <div className="flex items-start gap-3 mb-3">
                <MapPin className="h-4 w-4 text-brand-400 mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-gray-100 truncate">{venue.name}</h3>
                  <p className="text-[10px] text-gray-500">
                    {venue.city || 'Unknown'}{venue.country ? `, ${venue.country}` : ''}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 mb-3">
                <div>
                  <p className="text-[10px] text-gray-500">Matches</p>
                  <p className="text-sm font-bold text-gray-100">{venue.total_matches || 0}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Avg 1st Inn</p>
                  <p className="text-sm font-bold text-gray-100">
                    {venue.avg_first_innings_score?.toFixed(0) || '—'}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-gray-500">Chase Win %</span>
                    <span className="font-medium text-gray-300">
                      {venue.chasing_win_pct?.toFixed(1) || '—'}%
                    </span>
                  </div>
                  <div className="h-1 bg-surface-200/50 rounded-full overflow-hidden mt-1">
                    <div
                      className="h-full bg-emerald-500/60 rounded-full"
                      style={{ width: `${venue.chasing_win_pct || 0}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-gray-500">Pace Wickets %</span>
                    <span className="font-medium text-gray-300">
                      {venue.pace_wickets_pct?.toFixed(1) || '—'}%
                    </span>
                  </div>
                  <div className="h-1 bg-surface-200/50 rounded-full overflow-hidden mt-1">
                    <div
                      className="h-full bg-brand-500/60 rounded-full"
                      style={{ width: `${venue.pace_wickets_pct || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
