import 'package:flutter/foundation.dart';
import 'package:media_kit/media_kit.dart';

import '../../domain/stream_format.dart';
import '../../domain/stream_playback_settings.dart';
import 'stream_quality_utils.dart';

/// mpv `setProperty` exists on mobile/desktop only; web uses a stub [NativePlayer].
Future<void> _setNativePlayerProperty(
  Player player,
  String name,
  String value,
) async {
  if (kIsWeb) return;
  final platform = player.platform;
  if (platform is NativePlayer) {
    await (platform as dynamic).setProperty(name, value);
  }
}

class StreamPlaybackConfigurator {
  const StreamPlaybackConfigurator(this._player);

  final Player _player;

  Future<void> applyNetworkOptions(String url) async {
    final uri = Uri.tryParse(url);
    final origin = uri?.origin ?? '';

    await _setNativePlayerProperty(_player, 'force-seekable', 'yes');
    await _setNativePlayerProperty(_player, 'network-timeout', '15');
    await _setNativePlayerProperty(
      _player,
      'user-agent',
      'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    );
    if (origin.isNotEmpty) {
      await _setNativePlayerProperty(_player, 'referrer', '$origin/');
    }
  }

  Future<void> applyBufferSettings(StreamPlaybackSettings settings) async {
    final bytes = settings.bufferBytes;
    await _setNativePlayerProperty(_player, 'demuxer-max-bytes', '$bytes');
    await _setNativePlayerProperty(_player, 'demuxer-max-back-bytes', '$bytes');
    await _setNativePlayerProperty(_player, 'cache-secs', '${settings.cacheSecs}');
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
    if (kIsWeb) return;
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
      await _setNativePlayerProperty(_player, 'hls-bitrate', '$cap');
      return;
    }

    await _setNativePlayerProperty(_player, 'hls-bitrate', 'max');
  }
}
