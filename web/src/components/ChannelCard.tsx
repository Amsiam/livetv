import { Link } from 'react-router-dom';
import type { TvChannel } from '../api/types';

interface ChannelCardProps {
  channel: TvChannel;
  selected?: boolean;
  compact?: boolean;
}

export function ChannelCard({ channel, selected = false, compact = false }: ChannelCardProps) {
  const subtitle = [
    channel.category,
    channel.source_count > 1 ? `${channel.source_count} sources` : '',
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <Link
      to={`/watch/${channel.id}`}
      className={`channel-card${selected ? ' selected' : ''}`}
      aria-current={selected ? 'page' : undefined}
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
        {!compact && subtitle ? <p className="channel-meta">{subtitle}</p> : null}
      </div>
    </Link>
  );
}
