import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/stream_format.dart';
import '../../domain/stream_playback_settings.dart';

class StreamPlaybackSettingsNotifier
    extends Notifier<StreamPlaybackSettings> {
  @override
  StreamPlaybackSettings build() => const StreamPlaybackSettings();

  void setQuality(QualityPreset quality) {
    state = state.copyWith(quality: quality);
  }

  /// Picks [QualityPreset.auto] for HLS/DASH so the player uses adaptive bitrate.
  void selectAutoForAdaptiveStream(String streamUrl) {
    if (!isAdaptiveStreamUrl(streamUrl)) return;
    if (state.quality != QualityPreset.auto) {
      state = state.copyWith(quality: QualityPreset.auto);
    }
  }

  void ensureQualityInPresets(List<QualityPreset> presets) {
    if (presets.isEmpty || presets.contains(state.quality)) return;
    state = state.copyWith(quality: QualityPreset.auto);
  }

  void setMaxBitrateKbps(int? value) {
    state = value == null
        ? state.copyWith(clearMaxBitrate: true)
        : state.copyWith(maxBitrateKbps: value);
  }

  void setMinBitrateKbps(int? value) {
    state = value == null
        ? state.copyWith(clearMinBitrate: true)
        : state.copyWith(minBitrateKbps: value);
  }

  void setBufferStrategy(BufferStrategy strategy) {
    state = state.copyWith(bufferStrategy: strategy);
  }
}

final streamPlaybackSettingsProvider = NotifierProvider<
    StreamPlaybackSettingsNotifier, StreamPlaybackSettings>(
  StreamPlaybackSettingsNotifier.new,
);
