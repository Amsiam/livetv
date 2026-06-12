import type { StreamSource } from '../api/types';

interface SourceBarProps {
  sources: StreamSource[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function SourceBar({ sources, activeIndex, onSelect }: SourceBarProps) {
  if (sources.length <= 1) {
    return null;
  }

  return (
    <div className="source-bar" role="tablist" aria-label="Stream sources">
      {sources.map((source, index) => (
        <button
          key={source.id}
          type="button"
          role="tab"
          aria-selected={index === activeIndex}
          className={`source-btn${index === activeIndex ? ' active' : ''}`}
          onClick={() => onSelect(index)}
        >
          {source.label || `Source ${index + 1}`}
        </button>
      ))}
    </div>
  );
}
