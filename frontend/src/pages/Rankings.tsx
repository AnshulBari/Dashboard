import { useEffect, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { ArrowDown, ArrowUp, ExternalLink, Minus } from 'lucide-react'
import { useIccRankings } from '@/hooks/useQueries'
import CountryFlag from '@/components/ui/CountryFlag'
import { SkeletonTable } from '@/components/ui/Skeleton'
import ErrorCard from '@/components/ui/ErrorCard'

interface PageContext {
  format: string
}

const FORMATS = ['Test', 'ODI', 'T20I'] as const
const CATEGORIES = [
  { value: 'batting', label: 'Batting' },
  { value: 'bowling', label: 'Bowling' },
  { value: 'allrounder', label: 'All-rounder' },
  { value: 'teams', label: 'Teams' },
] as const

function formatFromGlobal(value: string): typeof FORMATS[number] {
  if (value === 'Test' || value === 'ODI' || value === 'T20I') return value
  if (value === 'T20') return 'T20I'
  return 'Test'
}

function displayDate(value?: string | null) {
  if (!value) return 'latest published table'
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('en-GB', {
        day: 'numeric', month: 'short', year: 'numeric',
      }).format(date)
}

function Movement({ change }: { change?: number | null }) {
  if (!change) {
    return <span className="inline-flex items-center gap-1 text-[10px] text-gray-500"><Minus size={11} /> —</span>
  }
  const UpOrDown = change > 0 ? ArrowUp : ArrowDown
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] font-semibold ${change > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
      <UpOrDown size={11} />{Math.abs(change)}
    </span>
  )
}

export default function Rankings() {
  const { format: globalFormat } = useOutletContext<PageContext>()
  const [rankFormat, setRankFormat] = useState<typeof FORMATS[number]>(() => formatFromGlobal(globalFormat))
  const [category, setCategory] = useState<typeof CATEGORIES[number]['value']>('batting')
  const [visibleCount, setVisibleCount] = useState(25)

  useEffect(() => {
    setRankFormat(formatFromGlobal(globalFormat))
  }, [globalFormat])

  useEffect(() => {
    setVisibleCount(25)
  }, [rankFormat, category])

  const query = useIccRankings(rankFormat, category)
  const rankings = query.data?.rankings || []
  const visibleRankings = useMemo(() => rankings.slice(0, visibleCount), [rankings, visibleCount])
  const isTeams = category === 'teams'
  const sourceLabel = query.data?.source === 'icc-official-snapshot'
    ? 'Official ICC snapshot'
    : 'Official ICC feed'

  return (
    <div>
      <div className="page-header items-end">
        <div>
          <p className="eyebrow mb-2">Official world tables</p>
          <h1 className="page-title">ICC rankings</h1>
          <p className="page-subtitle">
            Men&apos;s format-specific team and player ratings, published by the ICC.
          </p>
        </div>
        <div className="text-right text-xs text-gray-500">
          <p className="font-semibold text-gray-300">Updated {displayDate(query.data?.ranking_date)}</p>
          <p className="mt-1">Player tables refresh each Wednesday</p>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex border border-black/10 bg-white/60 p-1">
          {FORMATS.map(format => (
            <button
              key={format}
              type="button"
              onClick={() => setRankFormat(format)}
              className={`min-w-[76px] px-4 py-2 text-xs font-bold uppercase tracking-[.12em] transition-colors ${
                rankFormat === format
                  ? 'bg-[#315fd5] text-white'
                  : 'text-gray-500 hover:bg-white/70 hover:text-gray-900'
              }`}
            >
              {format}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap border border-black/10 bg-white/60 p-1">
          {CATEGORIES.map(item => (
            <button
              key={item.value}
              type="button"
              onClick={() => setCategory(item.value)}
              className={`px-4 py-2 text-xs font-semibold transition-colors ${
                category === item.value
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {query.isLoading ? (
        <SkeletonTable rows={15} />
      ) : query.isError ? (
        <ErrorCard message="Could not load the official ICC rankings" onRetry={() => query.refetch()} />
      ) : rankings.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="font-semibold text-gray-200">The ICC table is temporarily unavailable.</p>
          <p className="mt-2 text-sm text-gray-500">Try again shortly; Crease will also use its last verified snapshot.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-black/10 px-5 py-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[.18em] text-brand-500">{rankFormat} · {sourceLabel}</p>
              <h2 className="mt-1 text-lg font-semibold text-gray-100">
                {isTeams ? 'Team rankings' : `${CATEGORIES.find(item => item.value === category)?.label} rankings`}
              </h2>
            </div>
            <a
              href="https://www.icc-cricket.com/rankings"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-500 hover:underline"
            >
              View at ICC <ExternalLink size={13} />
            </a>
          </div>

          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th className="w-24">Rank</th>
                  <th>{isTeams ? 'Team' : 'Player'}</th>
                  {!isTeams && <th>Country</th>}
                  <th className="text-right">Rating</th>
                  {isTeams ? (
                    <>
                      <th className="text-right">Matches</th>
                      <th className="text-right">Points</th>
                    </>
                  ) : (
                    <th className="text-right">Career best</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {visibleRankings.map((row, index) => {
                  const team = row.team_name || row.country || row.team || 'Unknown'
                  const name = row.team_name || row.name || 'Unknown'
                  return (
                    <tr key={`${row.source_id || row.player_id || row.team_id || name}-${index}`}>
                      <td>
                        <div className="flex items-center gap-3">
                          <span className={`min-w-5 text-sm font-bold ${(row.rank || 0) <= 3 ? 'text-brand-500' : 'text-gray-500'}`}>
                            {row.rank}
                          </span>
                          <Movement change={row.change} />
                        </div>
                      </td>
                      <td>
                        <div className="flex items-center gap-3">
                          <CountryFlag team={team} size="sm" />
                          <span className="font-semibold text-gray-200">{name}</span>
                        </div>
                      </td>
                      {!isTeams && <td className="text-sm text-gray-400">{team}</td>}
                      <td className="text-right text-base font-bold text-gray-100">
                        {row.rating?.toLocaleString() ?? '—'}
                      </td>
                      {isTeams ? (
                        <>
                          <td className="text-right font-mono text-sm text-gray-300">{row.matches?.toLocaleString() ?? '—'}</td>
                          <td className="text-right font-mono text-sm text-gray-300">{row.points?.toLocaleString() ?? '—'}</td>
                        </>
                      ) : (
                        <td className="max-w-[340px] text-right text-xs text-gray-400">{row.career_best || '—'}</td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {visibleCount < rankings.length && (
            <button
              type="button"
              onClick={() => setVisibleCount(count => count + 25)}
              className="w-full border-t border-black/10 bg-white/30 px-4 py-3 text-xs font-bold uppercase tracking-[.12em] text-brand-500 hover:bg-white/60"
            >
              Show next {Math.min(25, rankings.length - visibleCount)}
            </button>
          )}
        </div>
      )}

      <div className="mt-4 border-l-2 border-brand-500 bg-white/55 px-4 py-3 text-xs text-gray-500">
        Ratings, rank movement and career-best values come directly from the ICC&apos;s published men&apos;s rankings.
        Team tables retain the ICC&apos;s own match and points totals. The ranking date is shown above so a cached result is never mistaken for a newer table.
      </div>
    </div>
  )
}
