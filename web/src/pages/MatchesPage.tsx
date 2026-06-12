import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchMatches } from '../api/client';
import type { MatchSummary } from '../api/types';
import { formatMatchCardTime } from '../utils/matchTime';

const STATUS_FILTERS = [
  { value: 'live', label: 'Live' },
  { value: '', label: 'All' },
  { value: 'scheduled', label: 'Upcoming' },
] as const;

function statusLabel(status: MatchSummary['status']) {
  if (status === 'live') return 'LIVE';
  if (status === 'ended') return 'Ended';
  return 'Upcoming';
}

export function MatchesPage() {
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [status, setStatus] = useState('live');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPage = useCallback(
    async (nextPage: number, append: boolean) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const data = await fetchMatches({
          status: status || undefined,
          page: nextPage,
        });
        setMatches((current) => (append ? [...current, ...data.results] : data.results));
        setPage(nextPage);
        setHasMore(Boolean(data.next));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load matches');
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [status],
  );

  useEffect(() => {
    void loadPage(1, false);
  }, [loadPage]);

  return (
    <main className="page">
      <div className="filters" style={{ marginBottom: '1.25rem' }}>
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.label}
            type="button"
            className={`chip${status === filter.value ? ' active' : ''}`}
            onClick={() => setStatus(filter.value)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="state-box">
          <p>Loading matches…</p>
        </div>
      ) : error ? (
        <div className="state-box">
          <p>{error}</p>
          <button type="button" className="btn-primary" onClick={() => void loadPage(1, false)}>
            Retry
          </button>
        </div>
      ) : matches.length === 0 ? (
        <div className="state-box">
          <p>No matches found.</p>
        </div>
      ) : (
        <>
          <div className="match-grid">
            {matches.map((match) => (
              <Link key={match.id} to={`/matches/${match.id}`} className="match-card">
                <div className="match-poster">
                  {match.poster_url ? (
                    <img src={match.poster_url} alt="" loading="lazy" />
                  ) : (
                    <div className="match-poster-fallback">
                      <span>{match.home_team.slice(0, 1)}</span>
                      <span className="match-vs">vs</span>
                      <span>{match.away_team.slice(0, 1)}</span>
                    </div>
                  )}
                  <span className={`match-badge match-badge--${match.status}`}>
                    {statusLabel(match.status)}
                  </span>
                </div>
                <div className="match-card-body">
                  <h3>{match.display_title}</h3>
                  <p className="match-card-time">
                    {formatMatchCardTime(match.status, match.starts_at, match.ends_at)}
                  </p>
                  <p>{[match.sport, match.round].filter(Boolean).join(' · ')}</p>
                </div>
              </Link>
            ))}
          </div>
          {hasMore ? (
            <div className="load-more-wrap">
              <button
                type="button"
                className="btn-primary"
                disabled={loadingMore}
                onClick={() => void loadPage(page + 1, true)}
              >
                {loadingMore ? 'Loading…' : 'Load more'}
              </button>
            </div>
          ) : null}
        </>
      )}
    </main>
  );
}
