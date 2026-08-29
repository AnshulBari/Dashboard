import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Shield, TrendingUp, Activity } from 'lucide-react'
import { useTeam, useTeamAnalytics } from '@/hooks/useQueries'
import { SkeletonCard, Skeleton } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

export default function TeamDetail() {
  const { id } = useParams()
  const { data: team, isLoading: teamLoading, isError: teamError, refetch: refetchTeam } = useTeam(id || '')
  const { data: analytics, isLoading: analyticsLoading } = useTeamAnalytics(id || '')

  const isLoading = teamLoading || analyticsLoading

  if (teamError) {
    return (
      <div>
        <Link to="/teams" className="flex items-center text-sm text-gray-500 hover:text-gray-300 mb-6 transition-colors">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Teams
        </Link>
        <ErrorCard message="Failed to load team data" onRetry={() => refetchTeam()} />
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

  if (!team) {
    return (
      <div>
        <Link to="/teams" className="flex items-center text-sm text-gray-500 hover:text-gray-300 mb-6 transition-colors">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Teams
        </Link>
        <EmptyState title="Team not found" message="This team could not be found." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link to="/teams" className="flex items-center text-sm text-gray-500 hover:text-gray-300 transition-colors">
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to Teams
      </Link>

      {/* Team Header */}
      <div className="card p-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-brand-500/15 border border-brand-500/30 flex items-center justify-center">
              <Shield className="h-6 w-6 text-brand-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">{team.name}</h1>
              <p className="text-sm text-gray-500">
                {team.country || '—'} · {team.short_name || ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {team.overall_strength_score != null && (
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-brand-500/10 border-2 border-brand-500/30 flex items-center justify-center">
                  <span className="text-xl font-bold text-brand-400">{team.overall_strength_score.toFixed(1)}</span>
                </div>
                <p className="text-[10px] text-gray-500 mt-1">Overall</p>
              </div>
            )}
            {team.batting_strength_score != null && (
              <div className="text-center">
                <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                  <span className="text-lg font-bold text-emerald-400">{team.batting_strength_score.toFixed(1)}</span>
                </div>
                <p className="text-[10px] text-gray-500 mt-1">Batting</p>
              </div>
            )}
            {team.bowling_strength_score != null && (
              <div className="text-center">
                <div className="w-14 h-14 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center">
                  <span className="text-lg font-bold text-blue-400">{team.bowling_strength_score.toFixed(1)}</span>
                </div>
                <p className="text-[10px] text-gray-500 mt-1">Bowling</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Performance Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-gray-100">{team.matches || 0}</p>
          <p className="text-[10px] text-gray-500 mt-1">Matches</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-cricket-green">{team.wins || 0}</p>
          <p className="text-[10px] text-gray-500 mt-1">Wins</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-cricket-red">{team.losses || 0}</p>
          <p className="text-[10px] text-gray-500 mt-1">Losses</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-brand-400">{team.win_rate?.toFixed(1) || '—'}%</p>
          <p className="text-[10px] text-gray-500 mt-1">Win Rate</p>
        </div>
      </div>

      {/* Analytics */}
      {analytics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="h-4 w-4 text-brand-400" />
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Performance</h2>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100/50">
                <span className="text-xs text-gray-400">Avg 1st Innings</span>
                <span className="text-sm font-bold text-gray-200">
                  {analytics.avg_first_innings_score?.toFixed(0) || '—'}
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100/50">
                <span className="text-xs text-gray-400">Avg 2nd Innings</span>
                <span className="text-sm font-bold text-gray-200">
                  {analytics.avg_second_innings_score?.toFixed(0) || '—'}
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-surface-100/50">
                <span className="text-xs text-gray-400">Avg Economy</span>
                <span className="text-sm font-bold text-gray-200">
                  {analytics.avg_economy?.toFixed(2) || '—'}
                </span>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="h-4 w-4 text-brand-400" />
              <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Situational</h2>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-cricket-green/5 text-center border border-cricket-green/10">
                <p className="text-2xl font-bold text-cricket-green">
                  {analytics.chasing_win_pct?.toFixed(1) || '—'}%
                </p>
                <p className="text-[10px] text-gray-500 mt-1">Chasing Win</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-500/5 text-center border border-blue-500/10">
                <p className="text-2xl font-bold text-blue-400">
                  {analytics.defending_win_pct?.toFixed(1) || '—'}%
                </p>
                <p className="text-[10px] text-gray-500 mt-1">Defending Win</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
