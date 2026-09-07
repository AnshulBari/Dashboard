import { Radio, WifiOff } from 'lucide-react'
import { useLiveMatches } from '@/hooks/useQueries'
import { SkeletonMatch } from '@/components/ui/Skeleton'
import EmptyState from '@/components/ui/EmptyState'

export default function Live() {
  const live = useLiveMatches()
  const liveMatches = live.data?.data || []
  const liveAvailable = live.data?.provider_available ?? false

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2">
          <Radio className="h-5 w-5 text-emerald-400" />
          Live Center
        </h1>
        <p className="page-subtitle">
          Real-time match updates from CricketData.org
        </p>
      </div>

      {/* Status banner */}
      <div className={`card-solid p-4 flex items-center gap-3 ${liveAvailable ? 'border-emerald-500/20' : 'border-amber-500/20'}`}>
        {liveAvailable ? (
          <>
            <span className="live-badge"><span className="live-dot" /> Live</span>
            <span className="text-sm text-gray-300">Provider connected · Auto-refresh every 30s</span>
          </>
        ) : (
          <>
            <WifiOff className="h-4 w-4 text-amber-400" />
            <span className="text-sm text-gray-400">
              Live data provider not configured. Set <code className="px-1.5 py-0.5 rounded bg-white/5 text-amber-400 text-xs">CRICKETDATA_API_KEY</code> to enable live scores.
            </span>
          </>
        )}
      </div>

      {/* Live matches */}
      {live.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <SkeletonMatch key={i} />)}
        </div>
      ) : liveMatches.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {liveMatches.map((match: any) => (
            <div key={match.id} className="match-card-live p-5">
              <div className="flex items-center justify-between mb-3">
                {match.match_type && (
                  <span className="badge badge-green">{match.match_type}</span>
                )}
                <span className="live-badge"><span className="live-dot" /> LIVE</span>
              </div>
              {match.venue && (
                <p className="text-[11px] text-gray-500 mb-3">{match.venue}</p>
              )}
              {match.teams && match.teams.length >= 2 && (
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-100">{match.teams[0]?.name || 'TBA'}</p>
                    {match.teams[0]?.scores && (
                      <p className="text-xs font-mono text-emerald-400 mt-1">{match.teams[0].scores}</p>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 font-medium px-3">vs</span>
                  <div className="flex-1 text-right">
                    <p className="text-sm font-semibold text-gray-100">{match.teams[1]?.name || 'TBA'}</p>
                    {match.teams[1]?.scores && (
                      <p className="text-xs font-mono text-emerald-400 mt-1">{match.teams[1].scores}</p>
                    )}
                  </div>
                </div>
              )}
              {match.status && (
                <p className="text-[10px] text-gray-500 mt-3 text-center">{match.status}</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Radio className="h-10 w-10 text-gray-600" />}
          title="No live matches right now"
          message="Check back during major tournaments for live match updates."
        />
      )}

      {/* Data source footer */}
      <div className="text-center py-4">
        <p className="text-[10px] text-gray-600">
          Live data: CricketData.org · Historical data: Cricsheet
        </p>
      </div>
    </div>
  )
}
