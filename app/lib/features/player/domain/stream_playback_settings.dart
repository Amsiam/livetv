enum QualityPreset {
  auto,
  p1080,
  p720,
  p480,
  p360,
}

enum BufferStrategy {
  low,
  balanced,
  high,
}

class StreamPlaybackSettings {
  const StreamPlaybackSettings({
    this.quality = QualityPreset.auto,
    this.maxBitrateKbps,
    this.minBitrateKbps,
    this.bufferStrategy = BufferStrategy.balanced,
  });

  final QualityPreset quality;
  final int? maxBitrateKbps;
  final int? minBitrateKbps;
  final BufferStrategy bufferStrategy;

  int? get targetHeight => switch (quality) {
        QualityPreset.auto => null,
        QualityPreset.p1080 => 1080,
        QualityPreset.p720 => 720,
        QualityPreset.p480 => 480,
        QualityPreset.p360 => 360,
      };

  /// mpv `hls-bitrate` cap (bps) when variants are not exposed as tracks.
  int? get hlsBitrateCapBps => switch (quality) {
        QualityPreset.auto => null,
        QualityPreset.p1080 => 5_000_000,
        QualityPreset.p720 => 2_500_000,
        QualityPreset.p480 => 1_200_000,
        QualityPreset.p360 => 800_000,
      };

  int get bufferBytes => switch (bufferStrategy) {
        BufferStrategy.low => 16 * 1024 * 1024,
        BufferStrategy.balanced => 32 * 1024 * 1024,
        BufferStrategy.high => 64 * 1024 * 1024,
      };

  int get cacheSecs => switch (bufferStrategy) {
        BufferStrategy.low => 2,
        BufferStrategy.balanced => 5,
        BufferStrategy.high => 10,
      };

  StreamPlaybackSettings copyWith({
    QualityPreset? quality,
    int? maxBitrateKbps,
    bool clearMaxBitrate = false,
    int? minBitrateKbps,
    bool clearMinBitrate = false,
    BufferStrategy? bufferStrategy,
  }) {
    return StreamPlaybackSettings(
      quality: quality ?? this.quality,
      maxBitrateKbps:
          clearMaxBitrate ? null : (maxBitrateKbps ?? this.maxBitrateKbps),
      minBitrateKbps:
          clearMinBitrate ? null : (minBitrateKbps ?? this.minBitrateKbps),
      bufferStrategy: bufferStrategy ?? this.bufferStrategy,
    );
  }
}

String qualityPresetLabel(QualityPreset preset) {
  switch (preset) {
    case QualityPreset.auto:
      return 'Auto';
    case QualityPreset.p1080:
      return '1080p';
    case QualityPreset.p720:
      return '720p';
    case QualityPreset.p480:
      return '480p';
    case QualityPreset.p360:
      return '360p';
  }
}

String bufferStrategyLabel(BufferStrategy strategy) {
  switch (strategy) {
    case BufferStrategy.low:
      return 'Low (live)';
    case BufferStrategy.balanced:
      return 'Balanced';
    case BufferStrategy.high:
      return 'High';
  }
}
