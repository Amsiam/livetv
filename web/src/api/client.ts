import type { MatchDetail, MatchSummary, Paginated, TvChannel, TvRegion } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/v1';

async function apiGet<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const response = await fetch(url.toString(), {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`API ${response.status}: ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

async function apiPost(path: string): Promise<void> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  const response = await fetch(url.toString(), { method: 'POST' });
  if (!response.ok && response.status !== 204) {
    throw new Error(`API ${response.status}: ${response.statusText}`);
  }
}

export function fetchChannels(params: {
  grouped?: boolean;
  region?: string;
  category?: string;
  search?: string;
  page?: number;
} = {}): Promise<Paginated<TvChannel>> {
  return apiGet('/tv-channels/', {
    grouped: params.grouped ?? true,
    region: params.region,
    category: params.category,
    search: params.search,
    page: params.page,
  });
}

export function fetchChannel(id: string): Promise<TvChannel> {
  return apiGet(`/tv-channels/${id}/`);
}

export function fetchRegions(): Promise<TvRegion[]> {
  return apiGet('/tv-channels/regions/');
}

export function reportChannelFailure(sourceId: string): Promise<void> {
  return apiPost(`/tv-channels/${sourceId}/report-failure/`);
}

export function recordChannelView(channelId: string): Promise<void> {
  return apiPost(`/tv-channels/${channelId}/record-view/`);
}

export function fetchMatches(params: {
  status?: string;
  sport?: string;
  search?: string;
  page?: number;
} = {}): Promise<Paginated<MatchSummary>> {
  return apiGet('/matches/', {
    status: params.status,
    sport: params.sport,
    search: params.search,
    page: params.page,
  });
}

export function fetchMatch(id: string): Promise<MatchDetail> {
  return apiGet(`/matches/${id}/`);
}

export function reportMatchChannelFailure(channelId: string): Promise<void> {
  return apiPost(`/channels/${channelId}/report-failure/`);
}
