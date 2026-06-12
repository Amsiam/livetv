export interface StreamSource {
  id: string;
  stream_url: string;
  label: string;
  host?: string;
  kind?: 'match' | 'catalog';
}

export interface TvChannel {
  id: string;
  name: string;
  region: string;
  category: string;
  logo_url: string;
  stream_url: string;
  updated_at: string | null;
  source_count: number;
  sources: StreamSource[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface TvRegion {
  region: string;
  channel_count: number;
}

export interface MatchSummary {
  id: string;
  display_title: string;
  title: string;
  sport: string;
  home_team: string;
  away_team: string;
  starts_at: string;
  ends_at: string;
  status: 'scheduled' | 'live' | 'ended';
  poster_url: string;
  round: string;
  sort_order: number;
}

export interface MatchChannel {
  id: string;
  name: string;
  language: string;
  logo_url: string;
  stream_url: string;
  priority: number;
  is_active: boolean;
  source_count: number;
  sources: StreamSource[];
}

export interface MatchDetail extends MatchSummary {
  channels: MatchChannel[];
}

interface SourceCarrier {
  id: string;
  stream_url: string;
  sources: StreamSource[];
}

export function effectiveSources(channel: SourceCarrier): StreamSource[] {
  if (channel.sources.length > 0) {
    return channel.sources;
  }
  return [
    {
      id: channel.id,
      stream_url: channel.stream_url,
      label: 'Source 1',
    },
  ];
}
