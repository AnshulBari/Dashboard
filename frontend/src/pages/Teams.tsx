import { Link, useOutletContext } from 'react-router-dom'
import { Shield } from 'lucide-react'
import { useTeamList } from '@/hooks/useQueries'
import { Skeleton } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

interface PageContext { format: string }

export default function Teams() {
  const { format } = useOutletContext<PageContext>()
  const teams = useTeamList({ format: format === 'All' ? undefined : format, limit: 100 })

  return (
    <div className="space-y-5">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2">
          <Shield className="h-5 w-5 text-emerald-400" />
          Teams
        </h1>
        <p className="page-subtitle">
          {teams.data?.teams?.length || '—'} teams · {format === 'All' ? 'All formats' : format}
        </p>
      </div>

      {teams.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="card-solid p-4 space-y-3"><Skeleton className="h-5 w-3/4" /><Skeleton className="h-4 w-1/2" /></div>
          ))}
        </div>
      ) : teams.isError ? (
        <ErrorCard message="Failed to load teams" onRetry={() => teams.refetch()} />
      ) : (teams.data?.teams || []).length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(teams.data?.teams || []).map((team, idx) => (
            <Link
              key={team.id}
              to={`/teams/${team.id}`}
              className="card-solid p-4 hover:bg-white/[0.04] transition-all duration-200 group"
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-[10px] font-bold text-gray-600 w-4">{idx + 1}</span>
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center text-sm font-bold text-gray-300 border border-white/10">
                  {team.short_name?.charAt(0) || team.name?.charAt(0) || '?'}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-200 truncate group-hover:text-emerald-400 transition-colors">{team.name}</p>
                  <p className="text-[11px] text-gray-500">{team.short_name || team.country || '—'}</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-3">
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">P</p>
                  <p className="text-xs font-semibold text-gray-300">{team.matches || 0}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">W</p>
                  <p className="text-xs font-semibold text-emerald-400">{team.wins || 0}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">Win%</p>
                  <p className="text-xs font-semibold text-gray-300">{team.win_rate?.toFixed(0) || '—'}%</p>
                </div>
              </div>
              {team.win_rate != null && (
                <div className="mt-3 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500/60 rounded-full transition-all duration-500" style={{ width: `${Math.min(team.win_rate, 100)}%` }} />
                </div>
              )}
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No teams found" message="Try adjusting your format filter." />
      )}
    </div>
  )
}
