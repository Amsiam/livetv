import 'package:media_kit/media_kit.dart';

import '../../domain/stream_format.dart';
import '../../domain/stream_playback_settings.dart';

const _reservedTrackIds = {'auto', 'no'};

List<VideoTrack> selectableVideoTracks(List<VideoTrack> tracks) {
  return tracks
      .where(
        (track) =>
            !_reservedTrackIds.contains(track.id) && (track.h ?? 0) > 0,
      )
      .toList()
    ..sort((a, b) => (b.h ?? 0).compareTo(a.h ?? 0));
}

List<VideoTrack> tracksMeetingMinBitrate(
  List<VideoTrack> tracks,
  int? minBitrateKbps,
) {
  if (minBitrateKbps == null) return tracks;
  final minBps = minBitrateKbps * 1000;
  final filtered = tracks
      .where((track) => (track.bitrate ?? minBps) >= minBps)
      .toList();
  return filtered.isEmpty ? tracks : filtered;
}

bool hasQualityPresetForHeight(int presetHeight, List<int> variantHeights) {
  final tolerance = (presetHeight * 0.2).round();
  for (final variantHeight in variantHeights) {
    if ((variantHeight - presetHeight).abs() <= tolerance) return true;
  }
  return false;
}

bool hasQualityPreset(List<VideoTrack> tracks, QualityPreset preset) {
  if (preset == QualityPreset.auto) return true;
  final height = StreamPlaybackSettings(quality: preset).targetHeight;
  if (height == null) return true;

  final tolerance = (height * 0.2).round();
  for (final track in tracks) {
    final trackHeight = track.h ?? 0;
    if (trackHeight <= 0) continue;
    if ((trackHeight - height).abs() <= tolerance) return true;
  }
  return false;
}

List<QualityPreset> availableQualityPresetsForHeights(List<int> variantHeights) {
  final presets = <QualityPreset>[QualityPreset.auto];
  for (final preset in [
    QualityPreset.p1080,
    QualityPreset.p720,
    QualityPreset.p480,
    QualityPreset.p360,
  ]) {
    final height = StreamPlaybackSettings(quality: preset).targetHeight;
    if (height != null && hasQualityPresetForHeight(height, variantHeights)) {
      presets.add(preset);
    }
  }
  return presets;
}

List<QualityPreset> availableQualityPresets(
  List<VideoTrack> tracks, {
  int? minBitrateKbps,
}) {
  final selectable = tracksMeetingMinBitrate(
    selectableVideoTracks(tracks),
    minBitrateKbps,
  );
  final presets = <QualityPreset>[QualityPreset.auto];
  for (final preset in [
    QualityPreset.p1080,
    QualityPreset.p720,
    QualityPreset.p480,
    QualityPreset.p360,
  ]) {
    if (hasQualityPreset(selectable, preset)) {
      presets.add(preset);
    }
  }
  return presets;
}

bool isAdaptiveBitrateStream(
  String streamUrl,
  List<VideoTrack> tracks, {
  List<int> hlsVariantHeights = const [],
}) {
  if (selectableVideoTracks(tracks).length > 1) return true;
  if (hlsVariantHeights.length > 1) return true;
  return isAdaptiveStreamUrl(streamUrl);
}

bool supportsQualityMenu(
  String streamUrl,
  List<VideoTrack> tracks, {
  List<int> hlsVariantHeights = const [],
  bool hlsParseComplete = false,
  int? playbackHeight,
}) {
  return qualityPresetsForStream(
        streamUrl,
        tracks,
        hlsVariantHeights: hlsVariantHeights,
        hlsParseComplete: hlsParseComplete,
        playbackHeight: playbackHeight,
      ).length >
      1;
}

List<QualityPreset> qualityPresetsForStream(
  String streamUrl,
  List<VideoTrack> tracks, {
  int? minBitrateKbps,
  List<int> hlsVariantHeights = const [],
  bool hlsParseComplete = false,
  int? playbackHeight,
}) {
  final selectable = selectableVideoTracks(tracks);
  if (selectable.length > 1) {
    return availableQualityPresets(tracks, minBitrateKbps: minBitrateKbps);
  }

  if (hlsVariantHeights.isNotEmpty) {
    return availableQualityPresetsForHeights(hlsVariantHeights);
  }

  final format = detectStreamFormat(streamUrl);
  if (format == StreamFormat.hls && hlsParseComplete) {
    if (playbackHeight != null && playbackHeight > 0) {
      return availableQualityPresetsForHeights([playbackHeight]);
    }
    return const [QualityPreset.auto];
  }

  if (format == StreamFormat.dash) {
    return QualityPreset.values;
  }

  return const [QualityPreset.auto];
}

bool usesHlsBitrateCap(
  String streamUrl,
  List<VideoTrack> tracks, {
  List<int> hlsVariantHeights = const [],
}) {
  return detectStreamFormat(streamUrl) == StreamFormat.hls &&
      selectableVideoTracks(tracks).length <= 1 &&
      hlsVariantHeights.isEmpty;
}

VideoTrack? pickTrackForHeight(List<VideoTrack> tracks, int targetHeight) {
  if (tracks.isEmpty) return null;

  final descending = [...tracks]
    ..sort((a, b) => (b.h ?? 0).compareTo(a.h ?? 0));
  for (final track in descending) {
    final height = track.h ?? 0;
    if (height > 0 && height <= targetHeight) return track;
  }

  final ascending = [...tracks]
    ..sort((a, b) => (a.h ?? 0).compareTo(b.h ?? 0));
  return ascending.firstWhere(
    (track) => (track.h ?? 0) > 0,
    orElse: () => ascending.first,
  );
}

String currentQualityLabel({
  required VideoTrack selected,
  required List<VideoTrack> available,
}) {
  if (selected.id == 'auto') return 'Auto';

  final height = selected.h;
  if (height != null && height > 0) return '${height}p';
  if (selected.bitrate != null && selected.bitrate! > 0) {
    return '${(selected.bitrate! / 1000).round()} kbps';
  }
  return selected.title ?? 'Manual';
}
