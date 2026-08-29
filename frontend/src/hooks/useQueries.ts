import { useQuery } from '@tanstack/react-query'
import { 
  playerApi, teamApi, matchApi, venueApi, 
  competitionApi, matchupApi, rankingApi, liveApi,
  queryKeys 
} from '@/lib/api'

// ============================================================
// Player Hooks
// ============================================================

export function usePlayerList(params?: {
  format?: string
  role?: string
  country?: string
  sort_by?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: queryKeys.player.list(params as Record<string, string>),
    queryFn: () => playerApi.list(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function usePlayer(id: string, format?: string) {
  return useQuery({
    queryKey: queryKeys.player.detail(id, format),
    queryFn: () => playerApi.get(id, format),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerForm(id: string, format?: string) {
  return useQuery({
    queryKey: queryKeys.player.form(id, format),
    queryFn: () => playerApi.getForm(id, format),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerBatting(id: string, format?: string) {
  return useQuery({
    queryKey: queryKeys.player.batting(id, format),
    queryFn: () => playerApi.getBatting(id, format),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerBowling(id: string, format?: string) {
  return useQuery({
    queryKey: queryKeys.player.bowling(id, format),
    queryFn: () => playerApi.getBowling(id, format),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerMatchups(id: string, type: 'batting' | 'bowling' = 'batting', format?: string) {
  return useQuery({
    queryKey: queryKeys.player.matchups(id, type),
    queryFn: () => playerApi.getMatchups(id, type, format),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerAffiliations(id: string) {
  return useQuery({
    queryKey: queryKeys.player.affiliations(id),
    queryFn: () => playerApi.getAffiliations(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000, // 10 minutes - affiliations change rarely
  })
}

export function usePlayerCareer(id: string) {
  return useQuery({
    queryKey: queryKeys.player.career(id),
    queryFn: () => playerApi.getCareer(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerByYear(id: string, format: string, batting = true) {
  return useQuery({
    queryKey: queryKeys.player.byYear(id, format),
    queryFn: () => playerApi.getByYear(id, format, batting),
    enabled: !!id && !!format,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerByCompetition(id: string, format: string, batting = true) {
  return useQuery({
    queryKey: queryKeys.player.byCompetition(id, format),
    queryFn: () => playerApi.getByCompetition(id, format, batting),
    enabled: !!id && !!format,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerVsOpponent(id: string, format: string, batting = true) {
  return useQuery({
    queryKey: queryKeys.player.vsOpponent(id, format),
    queryFn: () => playerApi.getVsOpponent(id, format, batting),
    enabled: !!id && !!format,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerHistory(id: string, format: string, limit = 20) {
  return useQuery({
    queryKey: queryKeys.player.history(id, format),
    queryFn: () => playerApi.getHistory(id, format, limit),
    enabled: !!id && !!format,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePlayerProgression(id: string, format: string) {
  return useQuery({
    queryKey: queryKeys.player.progression(id, format),
    queryFn: () => playerApi.getProgression(id, format),
    enabled: !!id && !!format,
    staleTime: 5 * 60 * 1000,
  })
}

// ============================================================
// Team Hooks
// ============================================================

export function useTeamList(params?: { format?: string; sort_by?: string; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.team.list(params as Record<string, string>),
    queryFn: () => teamApi.list(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useTeam(id: string, format?: string) {
  return useQuery({
    queryKey: queryKeys.team.detail(id, format),
    queryFn: () => teamApi.get(id, format),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTeamAnalytics(id: string, format?: string) {
  return useQuery({
    queryKey: queryKeys.team.analytics(id, format),
    queryFn: () => teamApi.getAnalytics(id, format),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTeamByFormat(id: string) {
  return useQuery({
    queryKey: queryKeys.team.byFormat(id),
    queryFn: () => teamApi.getByFormat(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTeamHistory(id: string, format: string, limit = 20) {
  return useQuery({
    queryKey: queryKeys.team.history(id, format),
    queryFn: () => teamApi.getHistory(id, format, limit),
    enabled: !!id && !!format,
    staleTime: 5 * 60 * 1000,
  })
}

// ============================================================
// Match Hooks
// ============================================================

export function useMatchList(params?: {
  format?: string
  team?: string
  competition?: string
  season?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: queryKeys.match.list(params as Record<string, string>),
    queryFn: () => matchApi.list(params),
    staleTime: 2 * 60 * 1000, // 2 minutes - recent matches may update
  })
}

export function useMatch(id: string) {
  return useQuery({
    queryKey: queryKeys.match.detail(id),
    queryFn: () => matchApi.get(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  })
}

export function useMatchScorecard(id: string) {
  return useQuery({
    queryKey: queryKeys.match.scorecard(id),
    queryFn: () => matchApi.getScorecard(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  })
}

// ============================================================
// Venue Hooks
// ============================================================

export function useVenueList(params?: { format?: string; country?: string; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.venue.list(params as Record<string, string>),
    queryFn: () => venueApi.list(params),
    staleTime: 10 * 60 * 1000, // 10 minutes - venues rarely change
  })
}

export function useVenueAnalytics(id: string, format?: string) {
  return useQuery({
    queryKey: queryKeys.venue.analytics(id, format),
    queryFn: () => venueApi.getAnalytics(id, format),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  })
}

// ============================================================
// Competition Hooks
// ============================================================

export function useCompetitionList(params?: { format?: string; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.competition.list(params as Record<string, string>),
    queryFn: () => competitionApi.list(params),
    staleTime: 10 * 60 * 1000,
  })
}

export function useCompetition(id: string) {
  return useQuery({
    queryKey: queryKeys.competition.detail(id),
    queryFn: () => competitionApi.get(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  })
}

export function useCompetitionSummary(id: string) {
  return useQuery({
    queryKey: queryKeys.competition.summary(id),
    queryFn: () => competitionApi.getSummary(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  })
}

// ============================================================
// Matchup Hooks
// ============================================================

export function useMatchupList(params?: { format?: string; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.matchup.list(params as Record<string, string>),
    queryFn: () => matchupApi.list(params),
    staleTime: 5 * 60 * 1000,
  })
}

// ============================================================
// Rankings Hooks
// ============================================================

export function usePlatformRankings(format: string, category: string, limit = 25) {
  return useQuery({
    queryKey: queryKeys.ranking.platform(format, category),
    queryFn: () => rankingApi.getPlatform(format, category, limit),
    staleTime: 60 * 60 * 1000, // 1 hour - rankings don't change often
  })
}

export function useIccRankings(format: string, category: string) {
  return useQuery({
    queryKey: queryKeys.ranking.icc(format, category),
    queryFn: () => rankingApi.getIcc(format, category),
    staleTime: 60 * 60 * 1000,
  })
}

// ============================================================
// Live Hooks
// ============================================================

export function useLiveMatches() {
  return useQuery({
    queryKey: queryKeys.live.matches,
    queryFn: () => liveApi.getMatches(),
    refetchInterval: 30 * 1000, // 30 seconds - matches the backend cache
    refetchIntervalInBackground: true,
    staleTime: 15 * 1000, // 15 seconds
  })
}

export function useLiveMatch(matchId: string) {
  return useQuery({
    queryKey: queryKeys.live.match(matchId),
    queryFn: () => liveApi.getMatchState(matchId),
    enabled: !!matchId,
    refetchInterval: 30 * 1000,
    refetchIntervalInBackground: true,
    staleTime: 15 * 1000,
  })
}
