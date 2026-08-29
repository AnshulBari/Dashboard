import { useOutletContext } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Shield } from 'lucide-react'
import { useTeamList } from '@/hooks/useQueries'
import { SkeletonTable } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'

interface PageContext {
  format: string
}

export default function Teams() {
  const { format } = useOutletContext<PageContext>()
  const { data, isLoading, isError, refetch } = useTeamList({ 
    format: format === 'All' ? 'T20' : format 
  })

  const teams = data?.teams || []

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Teams</h1>
        <p className="page-subtitle">
          Team intelligence · {format === 'All' ? 'T20' : format}
        </p>
      </div>

      {isLoading ? (
        <SkeletonTable rows={8} />
      ) : isError ? (
        <ErrorCard message="Failed to load teams" onRetry={() => refetch()} />
      ) : teams.length === 0 ? (
        <EmptyState 
          icon={<Shield className="h-10 w-10 text-gray-600" />}
          title="No teams found" 
          message="No team data available for this selection." 
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {teams.map((team, idx) => (
            <Link
              key={team.id}
              to={`/teams/${team.id}`}
              className="card-glow p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-gray-600 w-5">{idx + 1}</span>
                  <div>
                    <p className="text-sm font-semibold text-gray-100">{team.name}</p>
                    <p className="text-[10px] text-gray-500">
                      {team.country || '—'} · {team.matches || 0} matches
                    </p>
                  </div>
                </div>
                {team.overall_strength_score != null && (
                  <div className="text-right">
                    <p className="text-lg font-bold text-brand-400">
                      {team.overall_strength_score.toFixed(1)}
                    </p>
                    <p className="text-[10px] text-gray-500">strength</p>
                  </div>
                )}
              </div>
              
              <div className="flex items-center gap-4 text-[10px]">
                <div>
                  <span className="text-gray-500">W/L</span>
                  <span className="ml-1 font-semibold text-gray-300">
                    {team.wins || 0}/{team.losses || 0}
                  </span>
                </div>
                {team.win_rate != null && (
                  <div>
                    <span className="text-gray-500">Win%</span>
                    <span className="ml-1 font-semibold text-gray-300">
                      {team.win_rate.toFixed(1)}%
                    </span>
                  </div>
                )}
                {team.avg_first_innings_score != null && (
                  <div>
                    <span className="text-gray-500">Avg</span>
                    <span className="ml-1 font-semibold text-gray-300">
                      {team.avg_first_innings_score.toFixed(0)}
                    </span>
                  </div>
                )}
              </div>

              {team.overall_strength_score != null && (
                <div className="mt-3 h-1 bg-surface-200/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500/60 rounded-full"
                    style={{ width: `${Math.min(team.overall_strength_score, 100)}%` }}
                  />
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
