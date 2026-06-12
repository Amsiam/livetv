import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchMatch, reportMatchChannelFailure } from '../api/client';
import { effectiveSources, type MatchChannel, type MatchDetail } from '../api/types';
import { SourceBar } from '../components/SourceBar';
import { VideoPlayer } from '../components/VideoPlayer';
import { formatMatchSchedule } from '../utils/matchTime';

export function MatchWatchPage() {
  const { matchId = '' } = useParams();
  const [match, setMatch] = useState<MatchDetail | null>(null);
  const [activeChannelIndex, setActiveChannelIndex] = useState(0);
  const [activeSourceIndex, setActiveSourceIndex] = useState(0);
  const [playerKey, setPlayerKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const triedSourceIds = useRef(new Set<string>());

  const channels = match?.channels ?? [];
  const activeChannel = channels[activeChannelIndex];
  const sources = useMemo(
    () => (activeChannel ? effectiveSources(activeChannel) : []),
    [activeChannel],
  );
  const activeSource = sources[activeSourceIndex] ?? sources[0];

  const loadMatch = useCallback(async () => {
    if (!matchId) {
      return;
    }

    setLoading(true);
    setError(null);
    triedSourceIds.current.clear();

    try {
      const detail = await fetchMatch(matchId);
      setMatch(detail);
      setActiveChannelIndex(0);
      setActiveSourceIndex(0);
      setPlayerKey((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load match');
      setMatch(null);
    } finally {
      setLoading(false);
    }
  }, [matchId]);

  useEffect(() => {
    void loadMatch();
  }, [loadMatch]);

  const tryNextSource = useCallback(async () => {
    if (!activeChannel || sources.length <= 1) {
      return false;
    }

    const current = sources[activeSourceIndex];
    if (current && !triedSourceIds.current.has(current.id)) {
      triedSourceIds.current.add(current.id);
      void reportMatchChannelFailure(current.id).catch(() => {});
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
  }, [activeChannel, activeSourceIndex, sources]);

  const handlePlaybackError = useCallback(
    async (message: string) => {
      const switched = await tryNextSource();
      if (!switched) {
        setError(message);
      }
    },
    [tryNextSource],
  );

  const selectChannel = (index: number) => {
    if (index === activeChannelIndex) {
      return;
    }
    setActiveChannelIndex(index);
    setActiveSourceIndex(0);
    triedSourceIds.current.clear();
    setPlayerKey((value) => value + 1);
    setError(null);
  };

  const selectSource = (index: number) => {
    if (index === activeSourceIndex) {
      return;
    }
    setActiveSourceIndex(index);
    triedSourceIds.current.clear();
    setPlayerKey((value) => value + 1);
    setError(null);
  };

  if (loading) {
    return (
      <main className="page">
        <div className="state-box">
          <p>Loading match…</p>
        </div>
      </main>
    );
  }

  if (!match || !activeChannel || !activeSource) {
    return (
      <main className="page">
        <div className="state-box">
          <p>{error ?? 'Match not found or no channels available.'}</p>
          <Link to="/" className="btn-primary">
            Back to matches
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
          title={match.display_title}
          onError={(message) => void handlePlaybackError(message)}
          onPlaying={() => setError(null)}
        />
        <div className="player-meta">
          <h1>{match.display_title}</h1>
          <p>
            {[
              match.sport,
              match.status === 'live' ? 'Live now' : null,
              formatMatchSchedule(match.starts_at, match.ends_at),
            ]
              .filter(Boolean)
              .join(' · ')}
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
        <div className="side-panel-header">Broadcast channels</div>
        <div className="channel-grid">
          {channels.map((channel: MatchChannel, index: number) => (
            <button
              key={channel.id}
              type="button"
              className={`channel-card${index === activeChannelIndex ? ' selected' : ''}`}
              onClick={() => selectChannel(index)}
              style={{ textAlign: 'left', width: '100%' }}
            >
              <div className="channel-logo-wrap">
                {channel.logo_url ? (
                  <img src={channel.logo_url} alt="" loading="lazy" />
                ) : (
                  <span className="channel-logo-fallback" aria-hidden>
                    {channel.name.slice(0, 1).toUpperCase()}
                  </span>
                )}
              </div>
              <div>
                <h3 className="channel-name">{channel.name}</h3>
                <p className="channel-meta">
                  {channel.source_count > 1
                    ? `${channel.source_count} sources`
                    : channel.language}
                </p>
              </div>
            </button>
          ))}
        </div>
      </aside>
    </main>
  );
}
