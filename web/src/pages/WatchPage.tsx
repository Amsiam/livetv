import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  fetchChannel,
  fetchChannels,
  recordChannelView,
  reportChannelFailure,
} from '../api/client';
import { effectiveSources, type TvChannel } from '../api/types';
import { SourceBar } from '../components/SourceBar';
import { VideoPlayer } from '../components/VideoPlayer';

export function WatchPage() {
  const navigate = useNavigate();
  const { channelId = '' } = useParams();
  const [channel, setChannel] = useState<TvChannel | null>(null);
  const [related, setRelated] = useState<TvChannel[]>([]);
  const [activeSourceIndex, setActiveSourceIndex] = useState(0);
  const [playerKey, setPlayerKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const triedSourceIds = useRef(new Set<string>());
  const viewRecorded = useRef(false);

  const sources = useMemo(
    () => (channel ? effectiveSources(channel) : []),
    [channel],
  );

  const activeSource = sources[activeSourceIndex] ?? sources[0];

  const loadChannel = useCallback(async () => {
    if (!channelId) {
      return;
    }

    setLoading(true);
    setError(null);
    viewRecorded.current = false;
    triedSourceIds.current.clear();

    try {
      const detail = await fetchChannel(channelId);
      setChannel(detail);

      const initialIndex = effectiveSources(detail).findIndex((source) => source.id === channelId);
      setActiveSourceIndex(initialIndex >= 0 ? initialIndex : 0);
      setPlayerKey((value) => value + 1);

      if (detail.category) {
        const list = await fetchChannels({
          grouped: true,
          category: detail.category,
        });
        setRelated(list.results);
      } else {
        setRelated([detail]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load channel');
      setChannel(null);
      setRelated([]);
    } finally {
      setLoading(false);
    }
  }, [channelId]);

  useEffect(() => {
    void loadChannel();
  }, [loadChannel]);

  useEffect(() => {
    if (!channel || viewRecorded.current) {
      return;
    }

    viewRecorded.current = true;
    void recordChannelView(channel.id).catch(() => {});
  }, [channel]);

  const tryNextSource = useCallback(async () => {
    if (!channel || sources.length <= 1) {
      return false;
    }

    const current = sources[activeSourceIndex];
    if (current && !triedSourceIds.current.has(current.id)) {
      triedSourceIds.current.add(current.id);
      void reportChannelFailure(current.id).catch(() => {});
    }

    for (let offset = 1; offset < sources.length; offset += 1) {
      const nextIndex = (activeSourceIndex + offset) % sources.length;
      const candidate = sources[nextIndex];
      if (triedSourceIds.current.has(candidate.id)) {
        continue;
      }

      setActiveSourceIndex(nextIndex);
      setPlayerKey((value) => value + 1);
      return true;
    }

    return false;
  }, [activeSourceIndex, channel, sources]);

  const handlePlaybackError = useCallback(
    async (message: string) => {
      const switched = await tryNextSource();
      if (!switched) {
        setError(message);
      }
    },
    [tryNextSource],
  );

  const selectSource = (index: number) => {
    if (index === activeSourceIndex) {
      return;
    }
    setActiveSourceIndex(index);
    triedSourceIds.current.clear();
    setPlayerKey((value) => value + 1);
    setError(null);
  };

  const selectRelatedChannel = (picked: TvChannel) => {
    if (picked.id === channel?.id) {
      return;
    }
    void navigate(`/watch/${picked.id}`);
  };

  if (loading) {
    return (
      <main className="page">
        <div className="state-box">
          <p>Loading channel…</p>
        </div>
      </main>
    );
  }

  if (!channel || !activeSource) {
    return (
      <main className="page">
        <div className="state-box">
          <p>{error ?? 'Channel not found.'}</p>
          <Link to="/tv" className="btn-primary">
            Back to channels
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="page watch-layout">
      <section className="player-shell">
        <VideoPlayer
          key={`${playerKey}:${activeSource.id}`}
          streamUrl={activeSource.stream_url}
          title={channel.name}
          onError={(message) => void handlePlaybackError(message)}
          onPlaying={() => setError(null)}
        />
        <div className="player-meta">
          <h1>{channel.name}</h1>
          <p>
            {[channel.category, channel.region].filter(Boolean).join(' · ')}
          </p>
          <SourceBar
            sources={sources}
            activeIndex={activeSourceIndex}
            onSelect={selectSource}
          />
          {error ? (
            <p style={{ color: 'var(--danger)', marginTop: '0.75rem' }}>{error}</p>
          ) : null}
        </div>
      </section>

      <aside className="side-panel">
        <div className="side-panel-header">
          {channel.category ? `${channel.category} channels` : 'More channels'}
        </div>
        <div className="channel-grid">
          {related.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`channel-card${item.id === channel.id ? ' selected' : ''}`}
              onClick={() => selectRelatedChannel(item)}
              style={{ textAlign: 'left', width: '100%' }}
            >
              <div className="channel-logo-wrap">
                {item.logo_url ? (
                  <img src={item.logo_url} alt="" loading="lazy" />
                ) : (
                  <span className="channel-logo-fallback" aria-hidden>
                    {item.name.slice(0, 1).toUpperCase()}
                  </span>
                )}
              </div>
              <div>
                <h3 className="channel-name">{item.name}</h3>
                <p className="channel-meta">
                  {item.source_count > 1 ? `${item.source_count} sources` : item.region}
                </p>
              </div>
            </button>
          ))}
        </div>
      </aside>
    </main>
  );
}
