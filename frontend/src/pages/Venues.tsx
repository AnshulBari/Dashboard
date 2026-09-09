import { Link, useOutletContext } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import { useVenueList } from '@/hooks/useQueries'
import { Skeleton } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

interface PageContext { format: string }

export default function Venues() {
  const { format } = useOutletContext<PageContext>()
  const venues = useVenueList({ format, limit: 100 })

  return (
    <div className="space-y-5">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2">
          <MapPin className="h-5 w-5 text-emerald-400" />
          Venues
        </h1>
        <p className="page-subtitle">
          {venues.data?.venues?.length || '—'} venues · {format === 'International' ? 'T20I + ODI + Test' : format}
        </p>
      </div>

      {venues.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="card-solid p-4 space-y-3"><Skeleton className="h-5 w-3/4" /><Skeleton className="h-4 w-1/2" /></div>
          ))}
        </div>
      ) : venues.isError ? (
        <ErrorCard message="Failed to load venues" onRetry={() => venues.refetch()} />
      ) : (venues.data?.venues || []).length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(venues.data?.venues || []).map(venue => (
            <Link
              key={venue.id}
              to={`/venues/${venue.id}`}
              className="card-solid p-4 hover:bg-white/[0.04] transition-all duration-200 group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-200 truncate group-hover:text-emerald-400 transition-colors">{venue.name}</p>
                  <p className="text-[11px] text-gray-500">{venue.city}{venue.country ? `, ${venue.country}` : ''}</p>
                </div>
                <div className="text-right ml-2">
                  <p className="text-xs font-bold text-gray-300">{venue.total_matches || 0}</p>
                  <p className="text-[9px] text-gray-600">matches</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-[10px] text-gray-500">Avg 1st Inn</p>
                  <p className="text-xs font-semibold text-gray-300">{venue.avg_first_innings_score?.toFixed(0) || '—'}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Chase Win%</p>
                  <p className="text-xs font-semibold text-gray-300">{venue.chasing_win_pct?.toFixed(1) || '—'}%</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No venues found" message="Try adjusting your format filter." />
      )}
    </div>
  )
}
