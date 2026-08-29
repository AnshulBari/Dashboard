import { useOutletContext } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { 
  Users, Shield, Trophy, MapPin, Radio, 
  TrendingUp, ArrowRight, WifiOff
} from 'lucide-react'
import { usePlayerList, useTeamList, useMatchList, useVenueList, useLiveMatches } from '@/hooks/useQueries'
import { SkeletonCard, SkeletonMatch, Skeleton } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
import FormatBadge from '@/components/ui/FormatBadge'

interface DashboardContext {
  format: string
}

function FormScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span className="text-gray-600">—</span>
  const cls = score >= 70 ? 'form-score-high' : score >= 50 ? 'form-score-mid' : 'form-score-low'
  return <span className={cls}>{score.toFixed(1)}</span>
}

function StatSummary({ label, value, icon: Icon, color }: {
  label: string
  value: string | number
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">{label}</p>
          <p className="text-xl font-bold text-gray-100 mt-0.5">{value}</p>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { format } = useOutletContext<DashboardContext>()
  
  // All queries run in parallel
  const players = usePlayerList({ 
    format: format === 'All' ? 'T20' : format, 
    sort_by: 'form_score', 
    limit: 10 
  })
  const teams = useTeamList({ 
    format: format === 'All' ? 'T20' : format, 
    limit: 8 
  })
  const matches = useMatchList({ 
    format: format === 'All' ? undefined : format, 
    limit: 8 
  })
  const venues = useVenueList({ 
    format: format === 'All' ? 'T20' : format, 
    limit: 6 
  })
  const live = useLiveMatches()

  const isLoading = players.isLoading || teams.isLoading || matches.isLoading || venues.isLoading

  const liveMatches = live.data?.data || []
  const liveAvailable = live.data?.provider_available ?? false

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">
          Cricket intelligence powered by 8,250+ historical matches
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatSummary 
              label="Players" 
              value={players.data?.total?.toLocaleString() || '—'} 
              icon={Users} 
              color="bg-brand-600" 
            />
            <StatSummary 
              label="Teams" 
              value={teams.data?.total?.toLocaleString() || '—'} 
              icon={Shield} 
              color="bg-emerald-600" 
            />
            <StatSummary 
              label="Matches" 
              value={matches.data?.total?.toLocaleString() || '—'} 
              icon={Trophy} 
              color="bg-amber-600" 
            />
            <StatSummary 
              label="Venues" 
              value={venues.data?.total?.toLocaleString() || '—'} 
              icon={MapPin} 
              color="bg-purple-600" 
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* LIVE NOW - Left Column */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="px-4 py-3 border-b border-surface-200/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-cricket-green" />
                <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Live Now</h2>
              </div>
              <div className="flex items-center gap-2">
                {liveAvailable ? (
                  <span className="flex items-center gap-1.5 text-[10px] text-gray-500">
                    <span className="live-dot" />
                    Live
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-[10px] text-gray-600">
                    <WifiOff className="h-3 w-3" />
                    Provider unavailable
                  </span>
                )}
              </div>
            </div>

            <div className="p-4">
              {live.isLoading ? (
                <div className="space-y-3">
                  <SkeletonMatch />
                  <SkeletonMatch />
                </div>
              ) : liveMatches.length > 0 ? (
                <div className="space-y-3">
                  {liveMatches.slice(0, 3).map((match) => (
                    <Link
                      key={match.id}
                      to={`/live`}
                      className="match-card-live block"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          {match.match_type && (
                            <FormatBadge format={match.match_type} />
                          )}
                          {match.venue && (
                            <span className="text-[10px] text-gray-500 truncate max-w-[200px]">
                              {match.venue}
                            </span>
                          )}
                        </div>
                        <span className="flex items-center gap-1 text-[10px] text-cricket-green">
                          <span className="live-dot" />
                          LIVE
                        </span>
                      </div>
                      {match.teams && match.teams.length >= 2 && (
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-semibold text-gray-100">
                              {match.teams[0]?.name || 'TBA'}
                            </p>
                            {match.teams[0]?.scores && (
                              <p className="text-xs font-mono text-gray-300">{match.teams[0].scores}</p>
                            )}
                          </div>
                          <span className="text-xs text-gray-500 font-medium px-2">vs</span>
                          <div className="text-right">
                            <p className="text-sm font-semibold text-gray-100">
                              {match.teams[1]?.name || 'TBA'}
                            </p>
                            {match.teams[1]?.scores && (
                              <p className="text-xs font-mono text-gray-300">{match.teams[1].scores}</p>
                            )}
                          </div>
                        </div>
                      )}
                      {match.status && (
                        <p className="text-[10px] text-gray-500 mt-2 text-center">{match.status}</p>
                      )}
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={<Radio className="h-8 w-8 text-gray-600" />}
                  title="No live matches right now"
                  message={liveAvailable 
                    ? "Check back later for live match updates." 
                    : "Live data provider is not configured. Set CRICKETDATA_API_KEY to enable live scores."
                  }
                />
              )}
              {liveMatches.length > 0 && (
                <Link 
                  to="/live" 
                  className="flex items-center justify-center gap-1 mt-3 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                >
                  View all live matches
                  <ArrowRight className="h-3 w-3" />
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* TOP PERFORMERS - Right Column */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="px-4 py-3 border-b border-surface-200/50">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-brand-400" />
                <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                  Top Performers
                </h2>
              </div>
              <p className="text-[10px] text-gray-500 mt-0.5">
                By form score · {format === 'All' ? 'T20' : format}
              </p>
            </div>

            <div className="divide-y divide-surface-200/30">
              {players.isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                ))
              ) : players.isError ? (
                <div className="p-4">
                  <ErrorCard 
                    message="Failed to load player data" 
                    onRetry={() => players.refetch()} 
                  />
                </div>
              ) : (players.data?.players || []).filter(p => p.form_score != null).length > 0 ? (
                (players.data?.players || [])
                  .filter(p => p.form_score != null)
                  .slice(0, 8)
                  .map((player, idx) => (
                    <Link
                      key={player.id}
                      to={`/players/${player.id}`}
                      className="player-row"
                    >
                      <span className="text-xs font-bold text-gray-600 w-5 text-right">
                        {idx + 1}
                      </span>
                      <div className="player-avatar">
                        {player.name?.charAt(0) || '?'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-200 truncate">
                          {player.name}
                        </p>
                        <p className="text-[10px] text-gray-500">
                          {player.team_name || player.country || '—'}
                        </p>
                      </div>
                      <div className="text-right">
                        <FormScoreBadge score={player.form_score} />
                      </div>
                    </Link>
                  ))
              ) : (
                <div className="p-4">
                  <EmptyState 
                    title="No players found" 
                    message="No player data available for this format." 
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* RECENT RESULTS */}
        <div className="card">
          <div className="px-4 py-3 border-b border-surface-200/50 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                Recent Results
              </h2>
              <p className="text-[10px] text-gray-500 mt-0.5">Latest match outcomes</p>
            </div>
            <Link to="/matches" className="text-[10px] text-brand-400 hover:text-brand-300 transition-colors">
              View all →
            </Link>
          </div>

          <div className="divide-y divide-surface-200/30">
            {matches.isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-4 py-3">
                  <SkeletonMatch />
                </div>
              ))
            ) : matches.isError ? (
              <div className="p-4">
                <ErrorCard 
                  message="Failed to load matches" 
                  onRetry={() => matches.refetch()} 
                />
              </div>
            ) : (matches.data?.matches || []).length > 0 ? (
              (matches.data?.matches || []).slice(0, 6).map((match) => (
                <Link
                  key={match.id}
                  to={`/matches/${match.id}`}
                  className="block px-4 py-3 hover:bg-surface-100/50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-200">
                        {match.team_a || 'TBD'}
                      </span>
                      <span className="text-[10px] text-gray-600">vs</span>
                      <span className="text-sm font-semibold text-gray-200">
                        {match.team_b || 'TBD'}
                      </span>
                    </div>
                    <FormatBadge format={match.format} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-[10px] text-gray-500">
                      {match.match_date && <span>{match.match_date}</span>}
                      {match.venue && (
                        <>
                          <span>·</span>
                          <span className="truncate max-w-[150px]">{match.venue}</span>
                        </>
                      )}
                    </div>
                    <p className="text-[10px] font-medium text-brand-400 truncate max-w-[180px] text-right">
                      {match.result}
                    </p>
                  </div>
                </Link>
              ))
            ) : (
              <div className="p-4">
                <EmptyState 
                  title="No recent matches" 
                  message="No match data available for this format." 
                />
              </div>
            )}
          </div>
        </div>

        {/* VENUE INSIGHTS */}
        <div className="card">
          <div className="px-4 py-3 border-b border-surface-200/50 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                Venue Insights
              </h2>
              <p className="text-[10px] text-gray-500 mt-0.5">Ground analytics</p>
            </div>
            <Link to="/venues" className="text-[10px] text-brand-400 hover:text-brand-300 transition-colors">
              View all →
            </Link>
          </div>

          <div className="divide-y divide-surface-200/30">
            {venues.isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="px-4 py-3 space-y-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              ))
            ) : venues.isError ? (
              <div className="p-4">
                <ErrorCard 
                  message="Failed to load venues" 
                  onRetry={() => venues.refetch()} 
                />
              </div>
            ) : (venues.data?.venues || []).filter(v => v.total_matches && v.total_matches > 0).length > 0 ? (
              (venues.data?.venues || [])
                .filter(v => v.total_matches && v.total_matches > 0)
                .slice(0, 5)
                .map((venue) => (
                  <Link
                    key={venue.id}
                    to={`/venues/${venue.id}`}
                    className="block px-4 py-3 hover:bg-surface-100/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div>
                        <p className="text-sm font-medium text-gray-200">{venue.name}</p>
                        <p className="text-[10px] text-gray-500">
                          {venue.city}{venue.country ? `, ${venue.country}` : ''}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-bold text-gray-200">
                          {venue.total_matches}
                        </p>
                        <p className="text-[10px] text-gray-500">matches</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-gray-500">Avg 1st inn</span>
                        <span className="text-[10px] font-semibold text-gray-300">
                          {venue.avg_first_innings_score?.toFixed(0) || '—'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-gray-500">Chase win</span>
                        <span className="text-[10px] font-semibold text-gray-300">
                          {venue.chasing_win_pct?.toFixed(1) || '—'}%
                        </span>
                      </div>
                    </div>
                  </Link>
                ))
            ) : (
              <div className="p-4">
                <EmptyState 
                  title="No venues found" 
                  message="No venue data available for this format." 
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Data Source Footer */}
      <div className="card p-3">
        <p className="text-[10px] text-gray-500 text-center">
          <strong className="text-gray-400">Data:</strong> Historical data from{' '}
          <a 
            href="https://cricsheet.org" 
            target="_blank" 
            rel="noopener noreferrer" 
            className="text-brand-400 hover:text-brand-300"
          >
            Cricsheet
          </a>
          {liveAvailable && (
            <>
              {' '}· Live data: CricketData.org
            </>
          )}
          {' '}· Platform analytics computed from 4.13M match deliveries
        </p>
      </div>
    </div>
  )
}
