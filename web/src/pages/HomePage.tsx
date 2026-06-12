import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchChannels, fetchRegions } from '../api/client';
import type { TvChannel, TvRegion } from '../api/types';
import { ChannelGrid } from '../components/ChannelGrid';

export function HomePage() {
  const [channels, setChannels] = useState<TvChannel[]>([]);
  const [regions, setRegions] = useState<TvRegion[]>([]);
  const [region, setRegion] = useState('');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let cancelled = false;

    async function loadRegions() {
      try {
        const data = await fetchRegions();
        if (!cancelled) {
          setRegions(data);
        }
      } catch {
        // Regions are optional for browsing.
      }
    }

    void loadRegions();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadPage = useCallback(
    async (nextPage: number, append: boolean) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const data = await fetchChannels({
          grouped: true,
          region: region || undefined,
          search: debouncedSearch || undefined,
          page: nextPage,
        });

        setChannels((current) => (append ? [...current, ...data.results] : data.results));
        setPage(nextPage);
        setHasMore(Boolean(data.next));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load channels');
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [debouncedSearch, region],
  );

  useEffect(() => {
    void loadPage(1, false);
  }, [loadPage]);

  const topRegions = useMemo(
    () => regions.filter((item) => item.region).slice(0, 12),
    [regions],
  );

  return (
    <main className="page">
      <div className="filters" style={{ marginBottom: '1rem' }}>
        <button
          type="button"
          className={`chip${region === '' ? ' active' : ''}`}
          onClick={() => setRegion('')}
        >
          All regions
        </button>
        {topRegions.map((item) => (
          <button
            key={item.region}
            type="button"
            className={`chip${region === item.region ? ' active' : ''}`}
            onClick={() => setRegion(item.region)}
          >
            {item.region}
          </button>
        ))}
      </div>

      <div className="search-box" style={{ marginBottom: '1.25rem' }}>
        <input
          type="search"
          placeholder="Search channels…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Search channels"
        />
      </div>

      {loading ? (
        <div className="state-box">
          <p>Loading channels…</p>
        </div>
      ) : error ? (
        <div className="state-box">
          <p>{error}</p>
          <button type="button" className="btn-primary" onClick={() => void loadPage(1, false)}>
            Retry
          </button>
        </div>
      ) : (
        <>
          <h2 className="section-title">
            {region ? `${region} channels` : 'Popular channels'}
          </h2>
          <ChannelGrid channels={channels} />
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
