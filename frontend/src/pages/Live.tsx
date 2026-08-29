import { Radio, WifiOff, Clock } from 'lucide-react'
import { useLiveMatches } from '@/hooks/useQueries'
import { SkeletonMatch } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
import FormatBadge from '@/components/ui/FormatBadge'

export default function Live() {
  const { data, isLoading, isError, refetch, dataUpdatedAt } = useLiveMatches()

  const liveMatches = data?.data || []
  const providerAvailable = data?.provider_available ?? false
  const isStale = data?.stale ?? false
  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : null

  // Separate live vs upcoming vs completed
  const liveNow = liveMatches.filter(m => 
    m.status?.toLowerCase().includes('live') || 
    m.status?.toLowerCase().includes('in progress')
  )
  const upcoming = liveMatches.filter(m => 
    m.status?.toLowerCase().includes('upcoming') || 
    m.status?.toLowerCase().includes('not started')
  )
  const recentlyCompleted = liveMatches.filter(m => 
    !liveNow.includes(m) && !upcoming.includes(m)
  )

  return (
    <div className="space-y-6">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">Live Match Centre</h1>
          <p className="page-subtitle">
            Real-time match data from CricketData.org
          </p>
        </div>
        {lastUpdated && (
          <div className="flex items-center gap-2 text-[10px] text-gray-500">
            <Clock className="h-3 w-3" />
            Updated {lastUpdated.toLocaleTimeString()}
            {isStale && (
              <span className="text-amber-500">(stale)</span>
            )}
          </div>
        )}
      </div>

      {/* Provider Status */}
      {!providerAvailable && (
        <div className="card p-4 flex items-center gap-3 border-amber-500/20 bg-amber-500/5">
          <WifiOff className="h-5 w-5 text-amber-400 flex-shrink-0" />
          <div>
            <p className="text-xs font-medium text-amber-300">Live data provider not configured</p>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Set the CRICKETDATA_API_KEY environment variable to enable live match data.
            </p>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          <div>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Loading...
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Array.from({ length: 4 }).map((_, i) => <SkeletonMatch key={i} />)}
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {isError && (
        <ErrorCard 
          message="Failed to load live match data" 
          onRetry={() => refetch()} 
        />
      )}

      {/* Live Now */}
      {!isLoading && !isError && liveNow.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="live-dot" />
            <h2 className="text-xs font-semibold text-cricket-green uppercase tracking-wider">
              Live Now
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {liveNow.map(match => (
              <div key={match.id} className="match-card-live">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {match.match_type && <FormatBadge format={match.match_type} />}
                    {match.venue && (
                      <span className="text-[10px] text-gray-500 truncate max-w-[200px]">
                        {match.venue}
                      </span>
                    )}
                  </div>
                  <span className="flex items-center gap-1 text-[10px] text-cricket-green font-medium">
                    <span className="live-dot" />
                    LIVE
                  </span>
                </div>

                {match.teams && match.teams.length >= 2 && (
                  <div className="space-y-2">
                    {match.teams.map((team, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-gray-100">
                            {team.name}
                          </span>
                          {team.shortname && (
                            <span className="text-[10px] text-gray-500">{team.shortname}</span>
                          )}
                        </div>
                        {team.scores && (
                          <span className="text-sm font-mono font-bold text-gray-200">
                            {team.scores}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {match.status && (
                  <p className="text-[10px] text-gray-500 mt-3 text-center">
                    {match.status}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming */}
      {!isLoading && !isError && upcoming.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Upcoming
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {upcoming.map(match => (
              <div key={match.id} className="card p-4">
                <div className="flex items-center justify-between mb-2">
                  {match.match_type && <FormatBadge format={match.match_type} />}
                  {match.date_start && (
                    <span className="text-[10px] text-gray-500">
                      {new Date(match.date_start).toLocaleString()}
                    </span>
                  )}
                </div>
                {match.teams && match.teams.length >= 2 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-200">
                      {match.teams[0]?.name || 'TBA'}
                    </span>
                    <span className="text-xs text-gray-500 font-medium px-2">vs</span>
                    <span className="text-sm font-semibold text-gray-200">
                      {match.teams[1]?.name || 'TBA'}
                    </span>
                  </div>
                )}
                {match.venue && (
                  <p className="text-[10px] text-gray-500 mt-2 text-center">{match.venue}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recently Completed */}
      {!isLoading && !isError && recentlyCompleted.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Recently Completed
          </h2>
          <div className="space-y-2">
            {recentlyCompleted.slice(0, 5).map(match => (
              <div key={match.id} className="card p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {match.match_type && <FormatBadge format={match.match_type} />}
                    <div>
                      {match.teams && match.teams.length >= 2 && (
                        <p className="text-sm text-gray-200">
                          {match.teams[0]?.name} vs {match.teams[1]?.name}
                        </p>
                      )}
                    </div>
                  </div>
                  {match.status && (
                    <p className="text-[10px] text-gray-500">{match.status}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && liveMatches.length === 0 && (
        <EmptyState
          icon={<Radio className="h-10 w-10 text-gray-600" />}
          title="No live matches right now"
          message={providerAvailable 
            ? "Check back later for live match updates. Data refreshes every 30 seconds."
            : "Live data provider is not configured. Set CRICKETDATA_API_KEY to enable live scores."
          }
        />
      )}

      {/* Footer */}
      <div className="card p-3">
        <p className="text-[10px] text-gray-500 text-center">
          Data: CricketData.org · Auto-refresh: 30 seconds · Source may be delayed by a few minutes
        </p>
      </div>
    </div>
  )
}
