import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/features/player/domain/stream_format.dart';
import 'package:livetv_app/features/player/domain/stream_playback_settings.dart';
import 'package:livetv_app/features/player/presentation/utils/stream_quality_utils.dart';
import 'package:media_kit/media_kit.dart';

VideoTrack _track(String id, int height, {int? bitrate}) {
  return VideoTrack(
    id,
    null,
    null,
    h: height,
    bitrate: bitrate,
  );
}

void main() {
  group('isAdaptiveStreamUrl', () {
    test('treats HLS and DASH as adaptive', () {
      expect(
        isAdaptiveStreamUrl('https://cdn.example.com/live.m3u8'),
        isTrue,
      );
      expect(
        isAdaptiveStreamUrl('https://cdn.example.com/manifest.mpd'),
        isTrue,
      );
      expect(
        isAdaptiveStreamUrl('https://cdn.example.com/video.mp4'),
        isFalse,
      );
    });
  });

  group('isAdaptiveBitrateStream', () {
    test('detects multiple HLS variants', () {
      expect(
        isAdaptiveBitrateStream(
          'https://cdn.example.com/live.m3u8',
          [VideoTrack.auto()],
          hlsVariantHeights: [720, 1080],
        ),
        isTrue,
      );
    });

    test('detects multiple exposed tracks', () {
      expect(
        isAdaptiveBitrateStream(
          'https://cdn.example.com/live.m3u8',
          [VideoTrack.auto(), _track('1', 720), _track('2', 1080)],
        ),
        isTrue,
      );
    });
  });

  group('detectStreamFormat', () {
    test('detects HLS', () {
      expect(
        detectStreamFormat('https://cdn.example.com/live/playlist.m3u8'),
        StreamFormat.hls,
      );
    });

    test('detects DASH', () {
      expect(
        detectStreamFormat('https://cdn.example.com/manifest.mpd'),
        StreamFormat.dash,
      );
    });
  });

  group('selectableVideoTracks', () {
    test('filters auto and no tracks', () {
      final tracks = [
        VideoTrack.auto(),
        _track('1', 720),
        VideoTrack.no(),
      ];
      expect(selectableVideoTracks(tracks).map((t) => t.id), ['1']);
    });
  });

  group('pickTrackForHeight', () {
    test('picks closest height', () {
      final tracks = [_track('1', 360), _track('2', 720), _track('3', 1080)];
      expect(pickTrackForHeight(tracks, 720)?.id, '2');
      expect(pickTrackForHeight(tracks, 1080)?.id, '3');
    });
  });

  group('qualityPresetsForStream', () {
    test('returns only Auto until HLS playlist is parsed', () {
      expect(
        qualityPresetsForStream(
          'https://cdn.example.com/live.m3u8',
          [VideoTrack.auto()],
        ),
        [QualityPreset.auto],
      );
    });

    test('returns Auto and 720p for single parsed variant', () {
      expect(
        qualityPresetsForStream(
          'https://cdn.example.com/live.m3u8',
          [VideoTrack.auto()],
          hlsVariantHeights: [720],
          hlsParseComplete: true,
        ),
        [QualityPreset.auto, QualityPreset.p720],
      );
    });

    test('hides 360p when stream has only 720p', () {
      final presets = qualityPresetsForStream(
        'https://cdn.example.com/live.m3u8',
        [VideoTrack.auto()],
        hlsVariantHeights: [720],
        hlsParseComplete: true,
      );
      expect(presets, isNot(contains(QualityPreset.p360)));
      expect(presets, isNot(contains(QualityPreset.p1080)));
    });

    test('supportsQualityMenu when multiple presets exist', () {
      expect(
        supportsQualityMenu(
          'https://cdn.example.com/live.m3u8',
          [VideoTrack.auto()],
          hlsVariantHeights: [720],
          hlsParseComplete: true,
        ),
        isTrue,
      );
    });
  });

  group('availableQualityPresets', () {
    test('includes auto and matching presets', () {
      final tracks = [_track('1', 480), _track('2', 720), _track('3', 1080)];
      expect(
        availableQualityPresets(tracks),
        [
          QualityPreset.auto,
          QualityPreset.p1080,
          QualityPreset.p720,
          QualityPreset.p480,
        ],
      );
    });

    test('respects min bitrate floor', () {
      final tracks = [
        _track('1', 480, bitrate: 800_000),
        _track('2', 720, bitrate: 2_500_000),
        _track('3', 1080, bitrate: 5_000_000),
      ];
      expect(
        availableQualityPresets(tracks, minBitrateKbps: 2000),
        [QualityPreset.auto, QualityPreset.p1080, QualityPreset.p720],
      );
    });
  });
}
