import type { TvChannel } from '../api/types';
import { ChannelCard } from './ChannelCard';

interface ChannelGridProps {
  channels: TvChannel[];
  selectedId?: string;
  compact?: boolean;
}

export function ChannelGrid({ channels, selectedId, compact = false }: ChannelGridProps) {
  if (channels.length === 0) {
    return (
      <div className="state-box">
        <p>No channels found.</p>
      </div>
    );
  }

  return (
    <div className="channel-grid">
      {channels.map((channel) => (
        <ChannelCard
          key={channel.id}
          channel={channel}
          selected={channel.id === selectedId}
          compact={compact}
        />
      ))}
    </div>
  );
}
