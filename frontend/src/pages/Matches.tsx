import { Link, useOutletContext } from 'react-router-dom'
import { Trophy } from 'lucide-react'
import { useMatchList } from '@/hooks/useQueries'
import { SkeletonMatch } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
import FormatBadge from '@/components/ui/FormatBadge'
interface PageContext { format: string }

export default function Matches() {
  const { format } = useOutletContext<PageContext>()
  const matches = useMatchList({ format: format === 'All' ? undefined : format, limit: 50 })

  return (
    <div className="space-y-5">
      <div className="page-header">
        <h1 className="page-title flex items-center gap-2">
          <Trophy className="h-5 w-5 text-emerald-400" />
          Matches
        </h1>
        <p className="page-subtitle">
          {matches.data?.total?.toLocaleString() || '—'} matches · {format === 'All' ? 'All formats' : format}
        </p>
      </div>

      {matches.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 10 }).map((_, i) => <SkeletonMatch key={i} />)}
        </div>
      ) : matches.isError ? (
        <ErrorCard message="Failed to load matches" onRetry={() => matches.refetch()} />
      ) : (matches.data?.matches || []).length > 0 ? (
        <div className="space-y-2">
          {(matches.data?.matches || []).map(match => (
            <Link
              key={match.id}
              to={`/matches/${match.id}`}
              className="card-solid p-4 hover:bg-white/[0.04] transition-all duration-200 group block"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-sm font-semibold text-gray-200 truncate group-hover:text-emerald-400 transition-colors">
                    {match.team_a || 'TBD'}
                  </span>
                  <span className="text-[10px] text-gray-600 font-medium">vs</span>
                  <span className="text-sm font-semibold text-gray-200 truncate group-hover:text-emerald-400 transition-colors">
                    {match.team_b || 'TBD'}
                  </span>
                </div>
                <FormatBadge format={match.format} />
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-2 text-gray-500">
                  {match.match_date && <span>{match.match_date}</span>}
                  {match.venue && (
                    <><span>·</span><span className="truncate max-w-[200px]">{match.venue}</span></>
                  )}
                  {match.competition_name && (
                    <><span>·</span><span className="truncate max-w-[150px]">{match.competition_name}</span></>
                  )}
                </div>
                <span className="font-medium text-emerald-400 truncate max-w-[200px]">{match.result}</span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No matches found" message="Try adjusting your format filter." />
      )}
    </div>
  )
}
