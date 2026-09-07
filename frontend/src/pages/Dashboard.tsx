import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { 
  Users, Shield, Trophy, MapPin, Radio, 
  TrendingUp, WifiOff, Target,
  Clock, ChevronRight, Activity, Globe
} from 'lucide-react'
import { usePlayerList, useTeamList, useMatchList, useVenueList, useLiveMatches } from '@/hooks/useQueries'
import { SkeletonCard, SkeletonMatch, Skeleton } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
import FormatBadge from '@/components/ui/FormatBadge'
import type { PlayerRow, MatchRow } from '@/lib/api'

interface DashboardContext { format: string }

// ============================================================
// Player Tab Categories
// ============================================================
type PlayerTab = 'batting' | 'bowling' | 'form'

const PLAYER_TABS: { key: PlayerTab; label: string; sort: string }[] = [
  { key: 'form', label: 'In Form', sort: 'form_score' },
  { key: 'batting', label: 'Batting', sort: 'batting_average' },
  { key: 'bowling', label: 'Bowling', sort: 'career_wickets' },
]

// ============================================================
// Sub-components
// ============================================================

function StatCard({ label, value, icon: Icon, color, trend }: {
  label: string; value: string | number; icon: React.ElementType
  color: string; trend?: { value: string; positive: boolean }
}) {
  return (
    <div className="card-glass p-4 group hover:bg-white/[0.05] transition-all duration-300">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label mb-1">{label}</p>
          <p className="text-2xl font-bold text-gray-100">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-xl ${color} flex items-center justify-center opacity-60 group-hover:opacity-100 transition-opacity`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
      {trend && (
        <p className={`mt-2 text-[11px] font-medium ${trend.positive ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend.value}
        </p>
      )}
    </div>
  )
}

function PlayerListItem({ player, rank, statLabel }: { player: PlayerRow; rank: number; statLabel: string }) {
  const statValue = statLabel === 'batting_average' 
    ? player.batting_average?.toFixed(1)
    : statLabel === 'career_wickets' 
    ? player.career_wickets
    : statLabel === 'form_score'
    ? player.form_score?.toFixed(1)
    : null

  const statDisplay = statLabel === 'batting_average' ? 'AVG'
    : statLabel === 'career_wickets' ? 'WKTS'
    : 'FORM'

  return (
    <Link to={`/players/${player.id}`} className="player-row group">
      <span className="text-[10px] font-bold text-gray-600 w-4 text-right">{rank}</span>
      <div className="player-avatar group-hover:border-emerald-500/30 transition-colors">
        {player.name?.charAt(0) || '?'}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-200 truncate group-hover:text-emerald-400 transition-colors">
          {player.name}
        </p>
        <p className="text-[11px] text-gray-500">
          {player.team_name || player.country || '—'}
          {player.role && <span className="ml-1.5 text-gray-600">· {player.role}</span>}
        </p>
      </div>
      <div className="text-right flex flex-col items-end">
        {statValue != null && (
          <span className="text-sm font-bold text-emerald-400">{statDisplay === 'FORM' ? statValue : statDisplay === 'AVG' ? statValue : statValue}</span>
        )}
        <span className="text-[9px] text-gray-600 uppercase tracking-wider">{statDisplay}</span>
      </div>
    </Link>
  )
}

function MatchCard({ match }: { match: MatchRow }) {
  const resultColor = match.result_type === 'win' ? 'text-emerald-400'
    : match.result_type === 'loss' ? 'text-red-400'
    : 'text-gray-400'

  return (
    <Link to={`/matches/${match.id}`} className="match-card group">
      <div className="flex items-center justify-between mb-3">
        <FormatBadge format={match.format} />
        {match.competition_name && (
          <span className="text-[10px] text-gray-500 truncate max-w-[120px]">{match.competition_name}</span>
        )}
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-200 truncate group-hover:text-emerald-400 transition-colors">
            {match.team_a || 'TBD'}
          </p>
        </div>
        <div className="mx-3 flex flex-col items-center">
          <span className="text-[10px] font-bold text-gray-500 bg-white/5 px-2 py-0.5 rounded-md">VS</span>
        </div>
        <div className="flex-1 min-w-0 text-right">
          <p className="text-sm font-semibold text-gray-200 truncate group-hover:text-emerald-400 transition-colors">
            {match.team_b || 'TBD'}
          </p>
        </div>
      </div>
      
      <div className="mt-3 flex items-center justify-between text-[10px]">
        <span className="text-gray-500">{match.match_date || '—'}</span>
        <span className={`font-semibold ${resultColor} truncate max-w-[180px]`}>
          {match.result}
        </span>
      </div>
    </Link>
  )
}

function LiveMatchCard({ match }: { match: any }) {
  return (
    <div className="match-card-live">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {match.match_type && <FormatBadge format={match.match_type} />}
          {match.venue && (
            <span className="text-[10px] text-gray-500 truncate max-w-[150px]">{match.venue}</span>
          )}
        </div>
        <span className="live-badge">
          <span className="live-dot" />
          LIVE
        </span>
      </div>
      {match.teams && match.teams.length >= 2 && (
        <div className="flex items-center justify-between mt-2">
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-100">{match.teams[0]?.name || 'TBA'}</p>
            {match.teams[0]?.scores && (
              <p className="text-xs font-mono text-emerald-400">{match.teams[0].scores}</p>
            )}
          </div>
          <span className="text-xs text-gray-500 font-medium px-3">vs</span>
          <div className="flex-1 text-right">
            <p className="text-sm font-semibold text-gray-100">{match.teams[1]?.name || 'TBA'}</p>
            {match.teams[1]?.scores && (
              <p className="text-xs font-mono text-emerald-400">{match.teams[1].scores}</p>
            )}
          </div>
        </div>
      )}
      {match.status && (
        <p className="text-[10px] text-gray-500 mt-2 text-center">{match.status}</p>
      )}
    </div>
  )
}

// ============================================================
// Main Dashboard
// ============================================================
export default function Dashboard() {
  const { format } = useOutletContext<DashboardContext>()
  const [playerTab, setPlayerTab] = useState<PlayerTab>('form')
  
  const activeTab = PLAYER_TABS.find(t => t.key === playerTab)!
  
  const players = usePlayerList({ 
    format: format === 'All' ? undefined : format, 
    sort_by: activeTab.sort, 
    limit: 10 
  })
  const matches = useMatchList({ format: format === 'All' ? undefined : format, limit: 8 })
  const venues = useVenueList({ format: format === 'All' ? undefined : format, limit: 8 })
  const teams = useTeamList({ format: format === 'All' ? undefined : format, limit: 10 })
  const live = useLiveMatches()

  const isLoading = players.isLoading || teams.isLoading || matches.isLoading || venues.isLoading
  const liveMatches = live.data?.data || []
  const liveAvailable = live.data?.provider_available ?? false
  const playerList = players.data?.players || []
  const filteredPlayers = playerTab === 'bowling' 
    ? playerList.filter(p => p.career_wickets != null && p.career_wickets > 0)
    : playerTab === 'batting'
    ? playerList.filter(p => p.batting_average != null && p.batting_average > 0)
    : playerList.filter(p => p.form_score != null)

  return (
    <div className="space-y-5 hero-gradient">
      {/* ============================================================
          HEADER — compact welcome
          ============================================================ */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">
            Cricket Intelligence
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {format === 'All' ? 'All formats' : format} · Powered by 8,250 historical matches
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-[10px] text-gray-600">
          <Activity className="h-3 w-3" />
          <span>Data: Cricsheet</span>
        </div>
      </div>

      {/* ============================================================
          STAT CARDS — summary counts
          ============================================================ */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard 
              label="Players" value={players.data?.total?.toLocaleString() || '—'} 
              icon={Users} color="bg-emerald-500/20"
            />
            <StatCard 
              label="Teams" value={teams.data?.total?.toLocaleString() || '—'} 
              icon={Shield} color="bg-blue-500/20"
            />
            <StatCard 
              label="Matches" value={matches.data?.total?.toLocaleString() || '—'} 
              icon={Trophy} color="bg-amber-500/20"
            />
            <StatCard 
              label="Venues" value={venues.data?.total?.toLocaleString() || '—'} 
              icon={MapPin} color="bg-purple-500/20"
            />
          </>
        )}
      </div>

      {/* ============================================================
          THREE-COLUMN LAYOUT
          ============================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        
        {/* ============================================================
            LEFT COLUMN — Top Performers (tabbed)
            ============================================================ */}
        <div className="lg:col-span-4">
          <div className="card-solid overflow-hidden">
            {/* Header with tabs */}
            <div className="px-4 pt-4 pb-3 border-b border-white/5">
              <div className="section-header mb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                  <h2 className="section-title">Top Performers</h2>
                </div>
                <Link to="/players" className="section-link">
                  View All
                </Link>
              </div>
              {/* Tab switcher */}
              <div className="tabs">
                {PLAYER_TABS.map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setPlayerTab(tab.key)}
                    className={`tab flex-1 ${playerTab === tab.key ? 'tab-active' : 'tab-inactive'}`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Player list */}
            <div className="max-h-[480px] overflow-y-auto divide-y divide-white/[0.03]">
              {players.isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                ))
              ) : players.isError ? (
                <div className="p-4">
                  <ErrorCard message="Failed to load player data" onRetry={() => players.refetch()} />
                </div>
              ) : filteredPlayers.length > 0 ? (
                filteredPlayers.slice(0, 8).map((player, idx) => (
                  <PlayerListItem 
                    key={player.id} 
                    player={player} 
                    rank={idx + 1} 
                    statLabel={activeTab.sort}
                  />
                ))
              ) : (
                <div className="p-6">
                  <EmptyState title="No players found" message={`No ${playerTab} data available for this format.`} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ============================================================
            CENTER COLUMN — Live + Recent Matches
            ============================================================ */}
        <div className="lg:col-span-5 space-y-4">
          {/* Live Now */}
          <div className="card-solid overflow-hidden">
            <div className="px-4 pt-4 pb-3 border-b border-white/5">
              <div className="section-header">
                <div className="flex items-center gap-2">
                  <Radio className="h-4 w-4 text-emerald-400" />
                  <h2 className="section-title">Live Now</h2>
                  {liveAvailable && <span className="live-badge ml-1"><span className="live-dot" /> LIVE</span>}
                </div>
                {!liveAvailable && (
                  <span className="flex items-center gap-1.5 text-[10px] text-gray-600">
                    <WifiOff className="h-3 w-3" />
                    Offline
                  </span>
                )}
              </div>
            </div>
            <div className="p-4">
              {live.isLoading ? (
                <div className="space-y-3">
                  <SkeletonMatch /><SkeletonMatch />
                </div>
              ) : liveMatches.length > 0 ? (
                <div className="space-y-3">
                  {liveMatches.slice(0, 3).map((match: any) => (
                    <LiveMatchCard key={match.id} match={match} />
                  ))}
                  <Link to="/live" className="flex items-center justify-center gap-1 mt-2 text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
                    View all live matches <ChevronRight className="h-3 w-3" />
                  </Link>
                </div>
              ) : (
                <EmptyState
                  icon={<Radio className="h-8 w-8 text-gray-600" />}
                  title="No live matches right now"
                  message={liveAvailable 
                    ? "Check back later for live match updates." 
                    : "Configure CRICKETDATA_API_KEY to enable live scores."}
                />
              )}
            </div>
          </div>

          {/* Recent Results */}
          <div className="card-solid overflow-hidden">
            <div className="px-4 pt-4 pb-3 border-b border-white/5">
              <div className="section-header">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-400" />
                  <h2 className="section-title">Recent Results</h2>
                </div>
                <Link to="/matches" className="section-link">View All</Link>
              </div>
            </div>
            <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {matches.isLoading ? (
                Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
              ) : matches.isError ? (
                <div className="col-span-2 p-4"><ErrorCard message="Failed to load matches" onRetry={() => matches.refetch()} /></div>
              ) : (matches.data?.matches || []).length > 0 ? (
                (matches.data?.matches || []).slice(0, 4).map(match => (
                  <MatchCard key={match.id} match={match} />
                ))
              ) : (
                <div className="col-span-2"><EmptyState title="No recent matches" message="No match data available." /></div>
              )}
            </div>
          </div>
        </div>

        {/* ============================================================
            RIGHT COLUMN — Venue Insights + Team Strength
            ============================================================ */}
        <div className="lg:col-span-3 space-y-4">
          {/* Venue Insights */}
          <div className="card-solid overflow-hidden">
            <div className="px-4 pt-4 pb-3 border-b border-white/5">
              <div className="section-header">
                <div className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-purple-400" />
                  <h2 className="section-title">Top Venues</h2>
                </div>
                <Link to="/venues" className="section-link">View All</Link>
              </div>
            </div>
            <div className="p-3">
              {venues.isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="px-3 py-2.5 space-y-2"><Skeleton className="h-4 w-3/4" /><Skeleton className="h-3 w-1/2" /></div>
                ))
              ) : venues.isError ? (
                <div className="p-3"><ErrorCard message="Failed" onRetry={() => venues.refetch()} /></div>
              ) : (venues.data?.venues || []).filter(v => v.total_matches && v.total_matches > 0).length > 0 ? (
                (venues.data?.venues || []).filter(v => v.total_matches && v.total_matches > 0).slice(0, 6).map(venue => (
                  <Link key={venue.id} to={`/venues/${venue.id}`} className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/[0.03] transition-colors group">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-200 truncate group-hover:text-emerald-400 transition-colors">{venue.name}</p>
                      <p className="text-[10px] text-gray-500">{venue.city}{venue.country ? `, ${venue.country}` : ''}</p>
                    </div>
                    <div className="text-right ml-2">
                      <p className="text-xs font-bold text-gray-300">{venue.total_matches}</p>
                      <p className="text-[9px] text-gray-600">matches</p>
                    </div>
                  </Link>
                ))
              ) : (
                <div className="p-3"><EmptyState title="No venues" message="No data." /></div>
              )}
            </div>
          </div>

          {/* Team Strength */}
          <div className="card-solid overflow-hidden">
            <div className="px-4 pt-4 pb-3 border-b border-white/5">
              <div className="section-header">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-amber-400" />
                  <h2 className="section-title">Team Strength</h2>
                </div>
                <Link to="/teams" className="section-link">View All</Link>
              </div>
            </div>
            <div className="p-3">
              {teams.isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="px-3 py-2"><Skeleton className="h-4 w-3/4" /></div>
                ))
              ) : (teams.data?.teams || []).length > 0 ? (
                (teams.data?.teams || []).slice(0, 6).map((team, idx) => (
                  <Link key={team.id} to={`/teams/${team.id}`} className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/[0.03] transition-colors group">
                    <span className="text-[10px] font-bold text-gray-600 w-4">{idx + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-200 truncate group-hover:text-emerald-400 transition-colors">{team.name}</p>
                      {team.win_rate != null && (
                        <div className="mt-1 h-1 bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-emerald-500/60 rounded-full" style={{ width: `${Math.min(team.win_rate, 100)}%` }} />
                        </div>
                      )}
                    </div>
                    <span className="text-xs font-bold text-gray-400">{team.win_rate != null ? `${team.win_rate.toFixed(0)}%` : '—'}</span>
                  </Link>
                ))
              ) : (
                <div className="p-3"><EmptyState title="No teams" message="No data." /></div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-4">
        <p className="text-[10px] text-gray-600">
          <strong className="text-gray-500">Data:</strong> Historical data from{' '}
          <a href="https://cricsheet.org" target="_blank" rel="noopener noreferrer" className="text-emerald-400 hover:text-emerald-300">Cricsheet</a>
          {liveAvailable && ' · Live data: CricketData.org'}
          {' '} · Platform analytics computed from 4.13M match deliveries
        </p>
      </div>
    </div>
  )
}
