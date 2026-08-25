// ============================================================
// Player Types
// ============================================================

export interface Player {
  id: string
  name: string
  fullName?: string
  role: 'batsman' | 'bowler' | 'allrounder' | 'wicketkeeper'
  country?: string
  teamName?: string
  battingStyle?: string
  bowlingStyle?: string
  bowlingType?: string
}

export interface PlayerSummary extends Player {
  formScore?: number
  battingRating?: number
  consistency?: number
  careerRuns?: number
  careerWickets?: number
  battingAverage?: number
  strikeRate?: number
}

export interface PlayerBattingStats {
  matches: number
  innings: number
  runs: number
  average: number
  strikeRate: number
  fours: number
  sixes: number
  fifties: number
  hundreds: number
  highestScore: number
  ballsFaced: number
  notOuts: number
  boundaryPct: number
  dotBallPct: number
  phases: {
    powerplay: PhaseStats
    middle: PhaseStats
    death: PhaseStats
  }
}

export interface PlayerBowlingStats {
  matches: number
  innings: number
  wickets: number
  economy: number
  bowlingAverage: number
  strikeRate: number
  bestBowling?: string
  overs: number
  runsConceded: number
  maidens: number
  phases: {
    powerplay: PhaseStats
    middle: PhaseStats
    death: PhaseStats
  }
}

export interface PhaseStats {
  runs?: number
  balls?: number
  wickets?: number
  strikeRate: number
  economy?: number
}

export interface PlayerFormScore {
  playerId: string
  formScore: number
  components: {
    recentPerformance: { score: number; weight: number }
    consistency: { score: number; weight: number }
    oppositionStrength: { score: number; weight: number }
    venuePerformance: { score: number; weight: number }
    matchSituation: { score: number; weight: number }
    efficiency: { score: number; weight: number }
  }
}

export interface PlayerMatchup {
  opponentId: string
  opponentName: string
  totalBalls: number
  totalRuns: number
  wickets: number
  strikeRate: number
  average?: number
  dotBalls: number
  boundaries: number
  sixes: number
}

// ============================================================
// Team Types
// ============================================================

export interface Team {
  id: string
  name: string
  shortName: string
  country?: string
}

export interface TeamSummary extends Team {
  overallStrength?: number
  battingStrength?: number
  bowlingStrength?: number
  winRate?: number
  matches?: number
}

export interface TeamAnalytics {
  teamId: string
  format: string
  performance: {
    matches: number
    wins: number
    winRate: number
    avgTotalScore: number
    avgPowerplayScore: number
    avgMiddleScore: number
    avgDeathScore: number
  }
  bowling: {
    avgEconomy: number
    avgPowerplayEconomy: number
    avgMiddleEconomy: number
    avgDeathEconomy: number
  }
  situational: {
    chasingWinPct: number
    defendingWinPct: number
  }
}

// ============================================================
// Venue Types
// ============================================================

export interface Venue {
  id: string
  name: string
  city?: string
  country?: string
  capacity?: number
}

export interface VenueAnalytics {
  venueId: string
  format: string
  matches: number
  avgFirstInningsScore?: number
  avgSecondInningsScore?: number
  chasingWinPct?: number
  defendingWinPct?: number
  avgPowerplayRuns?: number
  avgMiddleRuns?: number
  avgDeathRuns?: number
  paceWicketsPct?: number
  spinWicketsPct?: number
  boundaryFrequency?: number
  highestTotal?: number
  lowestTotal?: number
}

// ============================================================
// Match Types
// ============================================================

export interface Match {
  id: string
  format: string
  date: string
  venue?: string
  teamA: string
  teamB: string
  result?: string
  winMargin?: number
  winType?: string
}

// ============================================================
// Matchup Types
// ============================================================

export interface HeadToHeadMatchup {
  batterId: string
  batterName: string
  bowlerId: string
  bowlerName: string
  format: string
  totalBalls: number
  totalRuns: number
  wickets: number
  strikeRate: number
  average?: number
  dotBalls: number
  boundaries: number
  sixes: number
}

// ============================================================
// News Types
// ============================================================

export interface NewsArticle {
  id: string
  title: string
  source?: string
  url: string
  publicationDate?: string
  description?: string
  category?: string
}

// ============================================================
// API Response Types
// ============================================================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
  hasMore: boolean
}

// ============================================================
// Chart Data Types
// ============================================================

export interface ChartDataPoint {
  name: string
  value: number
  [key: string]: string | number
}

export interface FormChartData {
  match: string
  runs: number
  balls: number
  strikeRate: number
  isOut: boolean
}
