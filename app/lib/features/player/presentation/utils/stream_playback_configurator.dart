import 'package:media_kit/media_kit.dart';

import '../../domain/stream_format.dart';
import '../../domain/stream_playback_settings.dart';
import 'stream_quality_utils.dart';

class StreamPlaybackConfigurator {
  const StreamPlaybackConfigurator(this._player);

  final Player _player;

  Future<void> applyNetworkOptions(String url) async {
    final platform = _player.platform;
    if (platform is! NativePlayer) return;

    final uri = Uri.tryParse(url);
    final origin = uri?.origin ?? '';

    await platform.setProperty('force-seekable', 'yes');
    await platform.setProperty('network-timeout', '15');
    await platform.setProperty(
      'user-agent',
      'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    );
    if (origin.isNotEmpty) {
      await platform.setProperty('referrer', '$origin/');
    }
  }

  Future<void> applyBufferSettings(StreamPlaybackSettings settings) async {
    final platform = _player.platform;
    if (platform is! NativePlayer) return;

    final bytes = settings.bufferBytes;
    await platform.setProperty('demuxer-max-bytes', '$bytes');
    await platform.setProperty('demuxer-max-back-bytes', '$bytes');
    await platform.setProperty('cache-secs', '${settings.cacheSecs}');
  }

  Future<void> applyQuality({
    required String url,
    required StreamPlaybackSettings settings,
    required List<VideoTrack> tracks,
  }) async {
    final selectable = tracksMeetingMinBitrate(
      selectableVideoTracks(tracks),
      settings.minBitrateKbps,
    );

    if (settings.quality == QualityPreset.auto) {
      await _player.setVideoTrack(VideoTrack.auto());
      await _applyHlsBitrateCap(url: url, settings: settings);
      return;
    }

    final targetHeight = settings.targetHeight;
    if (targetHeight == null) return;

    final track = pickTrackForHeight(selectable, targetHeight);
    if (track != null) {
      await _player.setVideoTrack(track);
      return;
    }

    if (usesHlsBitrateCap(url, tracks)) {
      await _player.setVideoTrack(VideoTrack.auto());
      await _applyHlsBitrateCap(url: url, settings: settings);
    }
  }

  Future<void> _applyHlsBitrateCap({
    required String url,
    required StreamPlaybackSettings settings,
  }) async {
    final platform = _player.platform;
    if (platform is! NativePlayer) return;

    if (detectStreamFormat(url) != StreamFormat.hls) return;

    final presetCap = settings.hlsBitrateCapBps;
    final userCap = settings.maxBitrateKbps != null && settings.maxBitrateKbps! > 0
        ? settings.maxBitrateKbps! * 1000
        : null;

    int? cap;
    if (presetCap != null && userCap != null) {
      cap = presetCap < userCap ? presetCap : userCap;
    } else {
      cap = presetCap ?? userCap;
    }

    if (cap != null && cap > 0) {
      await platform.setProperty('hls-bitrate', '$cap');
      return;
    }

    await platform.setProperty('hls-bitrate', 'max');
  }
}
