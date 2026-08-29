/**
 * Centralized API Client for the Cricket Intelligence Platform.
 * 
 * All requests go through /api/* which is proxied to the backend.
 * In production, the VITE_API_URL env var overrides the base URL.
 * 
 * IMPORTANT: The browser communicates only with our backend.
 * CRICKETDATA_API_KEY is never exposed to the frontend.
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export class ApiError extends Error {
  status: number
  body: string

  constructor(status: number, body: string) {
    super(`API error ${status}: ${body}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export async function fetchJson<T>(endpoint: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  
  if (!response.ok) {
    const errorBody = await response.text()
    throw new ApiError(response.status, errorBody || response.statusText)
  }
  
  return response.json()
}

// ============================================================
// Query Key Factories
// ============================================================

export const queryKeys = {
  // Player
  player: {
    all: ['players'] as const,
    list: (params?: Record<string, string>) => ['players', 'list', params] as const,
    detail: (id: string, format?: string) => ['players', 'detail', id, format] as const,
    form: (id: string, format?: string) => ['players', 'form', id, format] as const,
    batting: (id: string, format?: string) => ['players', 'batting', id, format] as const,
    bowling: (id: string, format?: string) => ['players', 'bowling', id, format] as const,
    matchups: (id: string, type?: string) => ['players', 'matchups', id, type] as const,
    affiliations: (id: string) => ['players', 'affiliations', id] as const,
    career: (id: string) => ['players', 'career', id] as const,
    byYear: (id: string, format: string) => ['players', 'byYear', id, format] as const,
    byCompetition: (id: string, format: string) => ['players', 'byCompetition', id, format] as const,
    bySeason: (id: string, format: string) => ['players', 'bySeason', id, format] as const,
    vsOpponent: (id: string, format: string) => ['players', 'vsOpponent', id, format] as const,
    atVenue: (id: string, format: string) => ['players', 'atVenue', id, format] as const,
    history: (id: string, format: string) => ['players', 'history', id, format] as const,
    progression: (id: string, format: string) => ['players', 'progression', id, format] as const,
  },
  // Team
  team: {
    all: ['teams'] as const,
    list: (params?: Record<string, string>) => ['teams', 'list', params] as const,
    detail: (id: string, format?: string) => ['teams', 'detail', id, format] as const,
    analytics: (id: string, format?: string) => ['teams', 'analytics', id, format] as const,
    byFormat: (id: string) => ['teams', 'byFormat', id] as const,
    byYear: (id: string, format: string) => ['teams', 'byYear', id, format] as const,
    vsTeam: (id: string, opponentId: string, format?: string) => ['teams', 'vsTeam', id, opponentId, format] as const,
    atVenue: (id: string, format: string) => ['teams', 'atVenue', id, format] as const,
    byCompetition: (id: string) => ['teams', 'byCompetition', id] as const,
    history: (id: string, format: string) => ['teams', 'history', id, format] as const,
    trend: (id: string, format: string) => ['teams', 'trend', id, format] as const,
  },
  // Match
  match: {
    all: ['matches'] as const,
    list: (params?: Record<string, string>) => ['matches', 'list', params] as const,
    detail: (id: string) => ['matches', 'detail', id] as const,
    scorecard: (id: string) => ['matches', 'scorecard', id] as const,
  },
  // Venue
  venue: {
    all: ['venues'] as const,
    list: (params?: Record<string, string>) => ['venues', 'list', params] as const,
    analytics: (id: string, format?: string) => ['venues', 'analytics', id, format] as const,
    byFormat: (id: string) => ['venues', 'byFormat', id] as const,
    teams: (id: string, format: string) => ['venues', 'teams', id, format] as const,
    players: (id: string, format: string) => ['venues', 'players', id, format] as const,
  },
  // Competition
  competition: {
    all: ['competitions'] as const,
    list: (params?: Record<string, string>) => ['competitions', 'list', params] as const,
    detail: (id: string) => ['competitions', 'detail', id] as const,
    seasons: (id: string) => ['competitions', 'seasons', id] as const,
    summary: (id: string) => ['competitions', 'summary', id] as const,
    seasonMatches: (seasonId: string) => ['competitions', 'seasonMatches', seasonId] as const,
  },
  // Matchups
  matchup: {
    all: ['matchups'] as const,
    list: (params?: Record<string, string>) => ['matchups', 'list', params] as const,
    detail: (batterId: string, bowlerId: string, format?: string) => ['matchups', 'detail', batterId, bowlerId, format] as const,
  },
  // Rankings
  ranking: {
    platform: (format: string, category: string) => ['rankings', 'platform', format, category] as const,
    icc: (format: string, category: string) => ['rankings', 'icc', format, category] as const,
  },
  // Live
  live: {
    matches: ['live', 'matches'] as const,
    match: (id: string) => ['live', 'match', id] as const,
  },
  // Analytics
  analytics: {
    dataCompleteness: ['analytics', 'dataCompleteness'] as const,
  },
} as const

// ============================================================
// API Functions (for use with React Query)
// ============================================================

// Player API
export const playerApi = {
  list: (params?: {
    format?: string
    role?: string
    country?: string
    sort_by?: string
    sort_order?: string
    limit?: number
    offset?: number
  }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.role) query.set('role', params.role)
    if (params?.country) query.set('country', params.country)
    if (params?.sort_by) query.set('sort_by', params.sort_by)
    if (params?.sort_order) query.set('sort_order', params.sort_order)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))
    return fetchJson<{ players: PlayerRow[]; total: number; limit: number; offset: number }>(`/players?${query}`)
  },
  
  get: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<PlayerDetail>(`/players/${id}${query}`)
  },
  
  getForm: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<PlayerFormResponse>(`/players/${id}/form${query}`)
  },
  
  getBatting: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<PlayerBattingStats>(`/players/${id}/batting${query}`)
  },
  
  getBowling: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<PlayerBowlingStats>(`/players/${id}/bowling${query}`)
  },
  
  getMatchups: (id: string, type: 'batting' | 'bowling' = 'batting', format?: string) => {
    const query = new URLSearchParams({ type })
    if (format) query.set('format', format)
    return fetchJson<{ player_id: string; type: string; matchups: PlayerMatchupRow[] }>(`/players/${id}/matchups?${query}`)
  },
  
  getAffiliations: (id: string) => {
    return fetchJson<{ player_id: string; affiliations: PlayerAffiliation[]; total: number }>(`/players/${id}/affiliations`)
  },
  
  // Analytics
  getCareer: (id: string) => fetchJson<PlayerCareer>(`/analytics/players/${id}/career`),
  getByYear: (id: string, format: string, batting = true) => 
    fetchJson<{ player_id: string; format: string; by_year: YearlyStats[] }>(`/analytics/players/${id}/by-year?format=${format}&batting=${batting}`),
  getByCompetition: (id: string, format: string, batting = true) => 
    fetchJson<{ player_id: string; format: string; by_competition: CompetitionStats[] }>(`/analytics/players/${id}/by-competition?format=${format}&batting=${batting}`),
  getBySeason: (id: string, format: string, batting = true) => 
    fetchJson<{ player_id: string; format: string; by_season: SeasonStats[] }>(`/analytics/players/${id}/by-season?format=${format}&batting=${batting}`),
  getVsOpponent: (id: string, format: string, batting = true) => 
    fetchJson<{ player_id: string; format: string; vs_opponent: OpponentStats[] }>(`/analytics/players/${id}/vs-opponent?format=${format}&batting=${batting}`),
  getAtVenue: (id: string, format: string) => 
    fetchJson<{ player_id: string; format: string; at_venue: VenuePlayerStats[] }>(`/analytics/players/${id}/at-venue?format=${format}`),
  getHistory: (id: string, format: string, limit = 20) => 
    fetchJson<{ player_id: string; format: string; matches: MatchHistoryRow[] }>(`/analytics/players/${id}/history?format=${format}&limit=${limit}`),
  getProgression: (id: string, format: string) => 
    fetchJson<{ player_id: string; format: string; progression: ProgressionPoint[] }>(`/analytics/players/${id}/progression?format=${format}`),
}

// Team API
export const teamApi = {
  list: (params?: { format?: string; sort_by?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.sort_by) query.set('sort_by', params.sort_by)
    if (params?.limit) query.set('limit', String(params.limit))
    return fetchJson<{ teams: TeamRow[]; total: number }>(`/teams?${query}`)
  },
  
  get: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<TeamDetail>(`/teams/${id}${query}`)
  },
  
  getAnalytics: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<TeamAnalytics>(`/teams/${id}/analytics${query}`)
  },
  
  getByFormat: (id: string) => fetchJson<{ team_id: string; by_format: FormatStats[] }>(`/analytics/teams/${id}/by-format`),
  getByYear: (id: string, format: string) => 
    fetchJson<{ team_id: string; format: string; by_year: TeamYearStats[] }>(`/analytics/teams/${id}/by-year?format=${format}`),
  getVsTeam: (id: string, opponentId: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<TeamVsTeamResult>(`/analytics/teams/${id}/vs-team/${opponentId}${query}`)
  },
  getHistory: (id: string, format: string, limit = 20) => 
    fetchJson<{ team_id: string; format: string; matches: MatchHistoryRow[] }>(`/analytics/teams/${id}/history?format=${format}&limit=${limit}`),
}

// Match API
export const matchApi = {
  list: (params?: {
    format?: string
    team?: string
    competition?: string
    season?: string
    limit?: number
    offset?: number
  }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.team) query.set('team', params.team)
    if (params?.competition) query.set('competition', params.competition)
    if (params?.season) query.set('season', params.season)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))
    return fetchJson<{ matches: MatchRow[]; total: number; limit: number; offset: number }>(`/matches?${query}`)
  },
  
  get: (id: string) => fetchJson<MatchDetail>(`/matches/${id}`),
  
  getScorecard: (id: string) => fetchJson<MatchScorecard>(`/analytics/matches/${id}/detail`),
}

// Venue API
export const venueApi = {
  list: (params?: { format?: string; country?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.country) query.set('country', params.country)
    if (params?.limit) query.set('limit', String(params.limit))
    return fetchJson<{ venues: VenueRow[]; total: number }>(`/venues?${query}`)
  },
  
  getAnalytics: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson<VenueAnalytics>(`/venues/${id}/analytics${query}`)
  },
  
  getByFormat: (id: string) => fetchJson<{ venue_id: string; by_format: FormatStats[] }>(`/analytics/venues/${id}/by-format`),
}

// Competition API
export const competitionApi = {
  list: (params?: { format?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.limit) query.set('limit', String(params.limit))
    return fetchJson<{ competitions: CompetitionRow[]; total: number }>(`/competitions?${query}`)
  },
  
  get: (id: string) => fetchJson<CompetitionDetail>(`/competitions/${id}`),
  
  getSeasons: (id: string) => fetchJson<{ seasons: SeasonRow[]; total: number }>(`/competitions/${id}/seasons`),
  
  getSummary: (id: string) => fetchJson<CompetitionSummary>(`/analytics/competitions/${id}/summary`),
}

// Matchup API
export const matchupApi = {
  list: (params?: { format?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.limit) query.set('limit', String(params.limit))
    return fetchJson<{ matchups: MatchupRow[]; total: number }>(`/matchups?${query}`)
  },
}

// Rankings API
export const rankingApi = {
  getPlatform: (format: string, category: string, limit = 25) =>
    fetchJson<{ source: string; format: string; category: string; rankings: RankingRow[]; total: number }>(
      `/rankings/platform?format=${format}&category=${category}&limit=${limit}`
    ),
  
  getIcc: (format: string, category: string) =>
    fetchJson<{ rankings: RankingRow[]; provider_available: boolean }>(
      `/rankings/icc?format=${format}&category=${category}`
    ),
}

// Live API
export const liveApi = {
  getMatches: () => fetchJson<LiveMatchesResponse>('/live'),
  getMatchState: (matchId: string) => fetchJson<LiveMatchDetail>(`/live/${matchId}`),
}

// ============================================================
// Type Definitions
// ============================================================

export interface PlayerRow {
  id: string
  name: string
  role: string | null
  country: string | null
  team_name: string | null
  form_score: number | null
  batting_average: number | null
  strike_rate: number | null
  career_runs: number | null
  career_wickets: number | null
}

export interface PlayerDetail {
  id: string
  name: string
  full_name: string | null
  role: string | null
  country: string | null
  team_name: string | null
  batting_style: string | null
  bowling_style: string | null
  bowling_type: string | null
  form_score: number | null
  matches: number | null
  innings: number | null
  runs: number | null
  batting_average: number | null
  strike_rate: number | null
  highest_score: number | null
  fours: number | null
  sixes: number | null
  fifties: number | null
  hundreds: number | null
  balls_faced: number | null
  not_outs: number | null
  boundary_pct: number | null
  dot_ball_pct: number | null
  powerplay_runs: number | null
  powerplay_strike_rate: number | null
  middle_runs: number | null
  middle_strike_rate: number | null
  death_runs: number | null
  death_strike_rate: number | null
  bowling?: {
    matches: number | null
    innings: number | null
    overs: number | null
    balls_bowled: number | null
    wickets: number | null
    runs_conceded: number | null
    bowling_average: number | null
    strike_rate: number | null
    economy: number | null
    dot_ball_pct: number | null
  } | null
}

export interface PlayerFormResponse {
  player_id: string
  form_score: number
  components: {
    recent_performance: { score: number; weight: number }
    consistency: { score: number; weight: number }
    opposition_strength: { score: number; weight: number }
    venue_performance: { score: number; weight: number }
    match_situation: { score: number; weight: number }
    efficiency: { score: number; weight: number }
  }
  recent_innings_count: number
}

export interface PlayerBattingStats {
  player_id?: string
  format?: string
  period?: string
  matches: number | null
  innings: number | null
  runs: number | null
  batting_average: number | null
  strike_rate: number | null
  highest_score: number | null
  fours: number | null
  sixes: number | null
  fifties: number | null
  hundreds: number | null
  balls_faced: number | null
  not_outs: number | null
  boundary_pct: number | null
  dot_ball_pct: number | null
  powerplay_runs: number | null
  powerplay_strike_rate: number | null
  middle_runs: number | null
  middle_strike_rate: number | null
  death_runs: number | null
  death_strike_rate: number | null
}

export interface PlayerBowlingStats {
  player_id?: string
  format?: string
  period?: string
  matches: number | null
  innings: number | null
  overs: number | null
  balls_bowled: number | null
  wickets: number | null
  runs_conceded: number | null
  bowling_average: number | null
  strike_rate: number | null
  economy: number | null
  dot_ball_pct: number | null
}

export interface PlayerMatchupRow {
  opponent_id: string
  opponent_name: string
  total_balls: number
  total_runs: number
  total_wickets: number
  strike_rate: number
  batting_average: number | null
  dot_balls: number
  boundaries: number
  sixes: number
}

export interface PlayerAffiliation {
  id: string
  format: string
  season: string | null
  is_current: boolean
  team_name: string
  team_short: string | null
  competition_name: string | null
  start_date: string | null
  end_date: string | null
}

export interface PlayerCareer {
  player_id: string
  formats: {
    format: string
    matches: number
    innings: number
    runs: number
    average: number
    strike_rate: number
    wickets: number | null
    economy: number | null
  }[]
}

export interface YearlyStats {
  year: number
  matches: number
  innings: number
  runs: number
  average: number | null
  strike_rate: number | null
  not_outs?: number
  hundreds?: number
  fifties?: number
}

export interface CompetitionStats {
  competition_id: string | null
  competition_name: string | null
  matches: number
  innings: number
  runs: number
  average: number | null
  strike_rate: number | null
}

export interface SeasonStats {
  season_id: string | null
  season_name: string | null
  competition_name: string | null
  matches: number
  innings: number
  runs: number
  average: number | null
  strike_rate: number | null
}

export interface OpponentStats {
  opponent_id: string | null
  opponent_name: string | null
  matches: number
  innings: number
  runs: number
  average: number | null
  strike_rate: number | null
  wickets?: number | null
}

export interface VenuePlayerStats {
  venue_id: string | null
  venue_name: string | null
  matches: number
  innings: number
  runs: number
  average: number | null
  strike_rate: number | null
}

export interface MatchHistoryRow {
  match_id: string
  match_date: string | null
  team_a: string | null
  team_b: string | null
  venue: string | null
  competition: string | null
  result: string | null
  runs: number | null
  balls: number | null
  not_out: boolean | null
  wickets_taken: number | null
  overs_bowled: number | null
  runs_conceded: number | null
}

export interface ProgressionPoint {
  year: number
  cumulative_runs: number | null
  cumulative_matches: number | null
  cumulative_innings: number | null
}

export interface TeamRow {
  id: string
  name: string
  short_name: string | null
  country: string | null
  matches: number | null
  wins: number | null
  losses: number | null
  win_rate: number | null
  batting_strength_score: number | null
  bowling_strength_score: number | null
  overall_strength_score: number | null
  avg_first_innings_score: number | null
  avg_second_innings_score: number | null
  avg_economy: number | null
  chasing_win_pct: number | null
  defending_win_pct: number | null
}

export interface TeamDetail extends TeamRow {}

export interface TeamAnalytics {
  team_id: string
  format: string
  period: string
  matches: number | null
  wins: number | null
  losses: number | null
  win_rate: number | null
  avg_first_innings_score: number | null
  avg_second_innings_score: number | null
  avg_economy: number | null
  chasing_win_pct: number | null
  defending_win_pct: number | null
  batting_strength_score: number | null
  bowling_strength_score: number | null
  overall_strength_score: number | null
}

export interface FormatStats {
  format: string
  matches: number
  wins: number | null
  losses: number | null
  win_rate: number | null
}

export interface TeamYearStats {
  year: number
  matches: number
  wins: number | null
  losses: number | null
  win_rate: number | null
}

export interface TeamVsTeamResult {
  team_a_id: string
  team_b_id: string
  format: string | null
  matches: number
  team_a_wins: number
  team_b_wins: number
  draws: number
  ties: number
  no_results: number
}

export interface MatchRow {
  id: string
  match_date: string | null
  format: string
  win_margin: number | null
  win_type: string | null
  result_type: string | null
  team_a: string | null
  team_b: string | null
  winner: string | null
  venue: string | null
  toss_decision: string | null
  competition_name: string | null
  season_name: string | null
  result: string
}

export interface MatchDetail extends MatchRow {}

export interface MatchScorecard {
  match_id: string
  format: string | null
  match_date: string | null
  team_a: string | null
  team_b: string | null
  venue: string | null
  result: string | null
  innings: {
    innings_number: number
    team: string | null
    team_id: string | null
    runs: number | null
    wickets: number | null
    overs: number | null
    extras: number | null
    batting: {
      player_id: string | null
      player_name: string
      runs: number | null
      balls: number | null
      fours: number | null
      sixes: number | null
      strike_rate: number | null
      dismissal: string | null
    }[]
    bowling: {
      player_id: string | null
      player_name: string
      overs: number | null
      maidens: number | null
      runs: number | null
      wickets: number | null
      economy: number | null
      extras?: number | null
    }[]
  }[]
}

export interface VenueRow {
  id: string
  name: string
  city: string | null
  country: string | null
  total_matches: number | null
  avg_first_innings_score: number | null
  avg_second_innings_score: number | null
  chasing_win_pct: number | null
  pace_wickets_pct: number | null
}

export interface VenueAnalytics {
  venue_id: string
  format: string
  name: string | null
  city: string | null
  country: string | null
  total_matches: number | null
  avg_first_innings_score: number | null
  avg_second_innings_score: number | null
  chasing_win_pct: number | null
  defending_win_pct: number | null
  pace_wickets_pct: number | null
  spin_wickets_pct: number | null
  highest_total: number | null
  lowest_total: number | null
}

export interface CompetitionRow {
  id: string
  name: string
  short_name: string | null
  format: string | null
  governing_body: string | null
  season: string | null
}

export interface CompetitionDetail extends CompetitionRow {
  seasons: SeasonRow[]
}

export interface SeasonRow {
  id: string
  name: string
  start_date: string | null
  end_date: string | null
}

export interface CompetitionSummary {
  competition_id: string
  name: string
  format: string | null
  total_matches: number
  seasons: {
    season_id: string
    season_name: string
    matches: number
    teams: number
  }[]
}

export interface MatchupRow {
  batter_id: string
  bowler_id: string
  format: string
  total_balls: number
  total_runs: number
  total_wickets: number
  strike_rate: number
  batting_average: number | null
  dot_balls: number
  boundaries: number
  sixes: number
  batter_name: string | null
  bowler_name: string | null
}

export interface RankingRow {
  id: string
  rank: number
  name: string
  country: string | null
  team: string | null
  rating: number | null
  runs: number | null
  wickets: number | null
  batting_average: number | null
  strike_rate: number | null
  economy: number | null
  form_score: number | null
}

export interface LiveMatch {
  id: string
  name: string | null
  status: string | null
  match_type: string | null
  venue: string | null
  teams: {
    name: string
    shortname: string | null
    scores: string | null
  }[]
  date_start: string | null
  date_end: string | null
  current_innings?: number | null
  score?: {
    inning: string
    runs: number
    wickets: number
    overs: number
    description: string
  }[]
}

export interface LiveMatchesResponse {
  data: LiveMatch[]
  source: string
  fetched_at: string
  cached: boolean
  stale: boolean
  provider_available: boolean
}

export interface LiveMatchDetail {
  data: LiveMatch | null
  source: string
  fetched_at: string
  cached: boolean
  stale: boolean
  provider_available: boolean
}
