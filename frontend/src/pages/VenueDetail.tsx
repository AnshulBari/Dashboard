import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, MapPin } from 'lucide-react'
import { useVenueAnalytics } from '@/hooks/useQueries'
import { SkeletonCard, Skeleton } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

export default function VenueDetail() {
  const { id } = useParams()
  const { data: venue, isLoading, isError, refetch } = useVenueAnalytics(id || '')

  if (isError) {
    return (
      <div>
        <Link to="/venues" className="flex items-center text-sm text-gray-500 hover:text-gray-300 mb-6 transition-colors">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Venues
        </Link>
        <ErrorCard message="Failed to load venue data" onRetry={() => refetch()} />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    )
  }

  if (!venue) {
    return (
      <div>
        <Link to="/venues" className="flex items-center text-sm text-gray-500 hover:text-gray-300 mb-6 transition-colors">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Venues
        </Link>
        <EmptyState title="Venue not found" message="This venue could not be found." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link to="/venues" className="flex items-center text-sm text-gray-500 hover:text-gray-300 transition-colors">
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Venues
      </Link>

      {/* Venue Header */}
      <div className="card p-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-brand-500/15 border border-brand-500/30 flex items-center justify-center">
            <MapPin className="h-6 w-6 text-brand-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-100">{venue.name || 'Unknown Venue'}</h1>
            <p className="text-sm text-gray-500">
              {venue.city || 'Unknown'}{venue.country ? `, ${venue.country}` : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-gray-100">{venue.total_matches || 0}</p>
          <p className="text-[10px] text-gray-500 mt-1">Matches</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-cricket-green">
            {venue.avg_first_innings_score?.toFixed(0) || '—'}
          </p>
          <p className="text-[10px] text-gray-500 mt-1">Avg 1st Innings</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-blue-400">
            {venue.avg_second_innings_score?.toFixed(0) || '—'}
          </p>
          <p className="text-[10px] text-gray-500 mt-1">Avg 2nd Innings</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-amber-400">
            {venue.chasing_win_pct?.toFixed(1) || '—'}%
          </p>
          <p className="text-[10px] text-gray-500 mt-1">Chase Win %</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Score Profile */}
        <div className="card p-5">
          <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-4">Score Profile</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100/50">
              <span className="text-xs text-gray-400">Highest Total</span>
              <span className="text-sm font-bold text-cricket-green">{venue.highest_total ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100/50">
              <span className="text-xs text-gray-400">Lowest Total</span>
              <span className="text-sm font-bold text-cricket-red">{venue.lowest_total ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100/50">
              <span className="text-xs text-gray-400">Avg 1st Innings</span>
              <span className="text-sm font-bold text-gray-200">
                {venue.avg_first_innings_score?.toFixed(0) || '—'}
              </span>
            </div>
            <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100/50">
              <span className="text-xs text-gray-400">Avg 2nd Innings</span>
              <span className="text-sm font-bold text-gray-200">
                {venue.avg_second_innings_score?.toFixed(0) || '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Pace vs Spin */}
        <div className="card p-5">
          <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-4">Pace vs Spin</h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">Pace Wickets</span>
                <span className="text-sm font-bold text-gray-200">{venue.pace_wickets_pct?.toFixed(1) || '—'}%</span>
              </div>
              <div className="h-2 bg-surface-200/50 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-cricket-red/60 rounded-full" 
                  style={{ width: `${venue.pace_wickets_pct || 0}%` }} 
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">Spin Wickets</span>
                <span className="text-sm font-bold text-gray-200">{venue.spin_wickets_pct?.toFixed(1) || '—'}%</span>
              </div>
              <div className="h-2 bg-surface-200/50 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-amber-500/60 rounded-full" 
                  style={{ width: `${venue.spin_wickets_pct || 0}%` }} 
                />
              </div>
            </div>
          </div>

          <div className="mt-6">
            <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3">Win Tendency</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-cricket-green/5 text-center border border-cricket-green/10">
                <p className="text-xl font-bold text-cricket-green">
                  {venue.chasing_win_pct?.toFixed(1) || '—'}%
                </p>
                <p className="text-[10px] text-gray-500 mt-1">Chasing</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-500/5 text-center border border-blue-500/10">
                <p className="text-xl font-bold text-blue-400">
                  {venue.defending_win_pct?.toFixed(1) || '—'}%
                </p>
                <p className="text-[10px] text-gray-500 mt-1">Defending</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
