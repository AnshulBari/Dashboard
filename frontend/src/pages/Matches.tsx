import { useOutletContext } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { Trophy } from 'lucide-react'
import { useMatchList } from '@/hooks/useQueries'
import { SkeletonMatch } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'
import EmptyState from '@/components/ui/EmptyState'
import FormatBadge from '@/components/ui/FormatBadge'

interface PageContext {
  format: string
}

export default function Matches() {
  const { format } = useOutletContext<PageContext>()
  const { data, isLoading, isError, refetch } = useMatchList({ 
    format: format === 'All' ? undefined : format, 
    limit: 50 
  })

  const matches = data?.matches || []

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Matches</h1>
        <p className="page-subtitle">
          Match results and historical data · {format === 'All' ? 'All formats' : format}
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => <SkeletonMatch key={i} />)}
        </div>
      ) : isError ? (
        <ErrorCard message="Failed to load matches" onRetry={() => refetch()} />
      ) : matches.length === 0 ? (
        <EmptyState 
          icon={<Trophy className="h-10 w-10 text-gray-600" />}
          title="No matches found" 
          message="No match data available for this selection." 
        />
      ) : (
        <div className="space-y-2">
          {matches.map((match) => (
            <Link
              key={match.id}
              to={`/matches/${match.id}`}
              className="match-card block"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-3">
                  <FormatBadge format={match.format} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-gray-100">
                        {match.team_a || 'TBD'}
                      </span>
                      <span className="text-[10px] text-gray-600">vs</span>
                      <span className="text-sm font-bold text-gray-100">
                        {match.team_b || 'TBD'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      {match.match_date && (
                        <span className="text-[10px] text-gray-500">{match.match_date}</span>
                      )}
                      {match.venue && (
                        <>
                          <span className="text-[10px] text-gray-600">·</span>
                          <span className="text-[10px] text-gray-500 truncate max-w-[200px]">
                            {match.venue}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-right sm:min-w-[200px]">
                  <p className="text-[10px] font-medium text-brand-400">
                    {match.result}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
