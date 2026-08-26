/**
 * API Client for the Cricket Intelligence Platform.
 *
 * All requests go through /api/* which is proxied to the backend.
 * In production, the VITE_API_URL env var overrides the base URL.
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`)
  
  if (!response.ok) {
    const errorBody = await response.text()
    throw new Error(
      `API error ${response.status}: ${errorBody || response.statusText}`
    )
  }
  
  return response.json()
}

// ============================================================
// Player API
// ============================================================

export const playerApi = {
  list: (params?: {
    format?: string
    role?: string
    country?: string
    sortBy?: string
    limit?: number
    offset?: number
  }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.role) query.set('role', params.role)
    if (params?.country) query.set('country', params.country)
    if (params?.sortBy) query.set('sort_by', params.sortBy)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))
    return fetchJson(`/players?${query}`)
  },

  get: (id: string) => fetchJson(`/players/${id}`),

  getForm: (id: string) => fetchJson(`/players/${id}/form`),

  getBatting: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson(`/players/${id}/batting${query}`)
  },

  getBowling: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson(`/players/${id}/bowling${query}`)
  },

  getMatchups: (id: string, type: 'batting' | 'bowling' = 'batting') =>
    fetchJson(`/players/${id}/matchups?type=${type}`),
}

// ============================================================
// Team API
// ============================================================

export const teamApi = {
  list: (params?: { format?: string; sortBy?: string }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.sortBy) query.set('sort_by', params.sortBy)
    return fetchJson(`/teams?${query}`)
  },

  get: (id: string) => fetchJson(`/teams/${id}`),

  getAnalytics: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson(`/teams/${id}/analytics${query}`)
  },
}

// ============================================================
// Venue API
// ============================================================

export const venueApi = {
  list: (params?: { format?: string; country?: string }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.country) query.set('country', params.country)
    return fetchJson(`/venues?${query}`)
  },

  getAnalytics: (id: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson(`/venues/${id}/analytics${query}`)
  },
}

// ============================================================
// Match API
// ============================================================

export const matchApi = {
  list: (params?: {
    format?: string
    team?: string
    limit?: number
    offset?: number
  }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.team) query.set('team', params.team)
    if (params?.limit) query.set('limit', String(params.limit))
    if (params?.offset) query.set('offset', String(params.offset))
    return fetchJson(`/matches?${query}`)
  },

  get: (id: string) => fetchJson(`/matches/${id}`),
}

// ============================================================
// Matchup API
// ============================================================

export const matchupApi = {
  list: (params?: { format?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.format) query.set('format', params.format)
    if (params?.limit) query.set('limit', String(params.limit))
    return fetchJson(`/matchups?${query}`)
  },

  get: (batterId: string, bowlerId: string, format?: string) => {
    const query = format ? `?format=${format}` : ''
    return fetchJson(`/matchups/${batterId}/${bowlerId}${query}`)
  },
}

// ============================================================
// Rankings API
// ============================================================

export const rankingApi = {
  get: (format: string, category: string) =>
    fetchJson(`/rankings?format=${format}&category=${category}`),
}

// ============================================================
// News API
// ============================================================

export const newsApi = {
  list: (params?: { category?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.category) query.set('category', params.category)
    if (params?.limit) query.set('limit', String(params.limit))
    return fetchJson(`/news?${query}`)
  },
}

// ============================================================
// Live API
// ============================================================

export const liveApi = {
  getMatches: () => fetchJson('/live'),

  getMatchState: (matchId: string) => fetchJson(`/live/${matchId}/state`),
}
