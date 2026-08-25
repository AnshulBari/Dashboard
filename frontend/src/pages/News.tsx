import { ExternalLink } from 'lucide-react'

const sampleNews = [
  { id: '1', title: 'India clinch T20I series 4-1 against Australia', source: 'ICC', date: '2024-01-15', category: 'match', description: 'India completed a dominant series victory with a 7-wicket win in the final T20I at the MCG.' },
  { id: '2', title: 'Suryakumar Yadav rises to No.1 in T20I rankings', source: 'ICC', date: '2024-01-15', category: 'player', description: 'SKY leapfrogs Babar Azam to claim the top ranking after a stellar series performance.' },
  { id: '3', title: 'England announce squad for IPL and T20 World Cup', source: 'ECB', date: '2024-01-14', category: 'tournament', description: 'The ECB has named a 16-player squad for the upcoming tournament cycle.' },
  { id: '4', title: 'ICC Men\'s T20 World Cup 2024 schedule released', source: 'ICC', date: '2024-01-13', category: 'tournament', description: 'The full schedule for the ICC Men\'s T20 World Cup 2024 has been announced.' },
  { id: '5', title: 'Jasprit Bumrah returns from injury for ODIs', source: 'BCCI', date: '2024-01-12', category: 'player', description: 'The fast bowler has been cleared to play after recovering from a back injury.' },
]

const categoryColors: Record<string, string> = {
  match: 'bg-blue-100 text-blue-800',
  player: 'bg-emerald-100 text-emerald-800',
  tournament: 'bg-amber-100 text-amber-800',
}

export default function News() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Cricket News</h1>
        <p className="page-subtitle">
          Headlines aggregated from RSS feeds — link to original sources
        </p>
      </div>

      <div className="space-y-3">
        {sampleNews.map((article) => (
          <div key={article.id} className="card-hover p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`badge ${categoryColors[article.category] || 'bg-gray-100 text-gray-800'}`}>
                    {article.category}
                  </span>
                  <span className="text-xs text-gray-400">{article.source}</span>
                  <span className="text-xs text-gray-400">·</span>
                  <span className="text-xs text-gray-400">{article.date}</span>
                </div>
                <h3 className="text-base font-semibold text-gray-900">{article.title}</h3>
                <p className="text-sm text-gray-500 mt-1">{article.description}</p>
              </div>
              <a
                href="#"
                className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 whitespace-nowrap"
              >
                Read more
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
