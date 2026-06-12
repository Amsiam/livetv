import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';
import 'package:media_kit_video/media_kit_video_controls/src/controls/methods/video_state.dart';

import '../providers/hls_playlist_info_provider.dart';
import '../providers/player_settings_handle_provider.dart';
import '../../domain/stream_format.dart';
import '../utils/stream_quality_utils.dart';
import 'stream_player_scope.dart';

class LiveTvQualityButton extends ConsumerStatefulWidget {
  const LiveTvQualityButton({super.key});

  @override
  ConsumerState<LiveTvQualityButton> createState() =>
      _LiveTvQualityButtonState();
}

class _LiveTvQualityButtonState extends ConsumerState<LiveTvQualityButton> {
  StreamSubscription<Tracks>? _tracksSubscription;
  StreamSubscription<Track>? _trackSubscription;
  List<VideoTrack> _videoTracks = const [];
  VideoTrack _selectedTrack = VideoTrack.auto();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _bindPlayer());
  }

  @override
  void didUpdateWidget(covariant LiveTvQualityButton oldWidget) {
    super.didUpdateWidget(oldWidget);
    _bindPlayer();
  }

  void _bindPlayer() {
    _tracksSubscription?.cancel();
    _trackSubscription?.cancel();

    final player = controller(context).player;
    _videoTracks = selectableVideoTracks(player.state.tracks.video);
    _selectedTrack = player.state.track.video;

    _tracksSubscription = player.stream.tracks.listen((tracks) {
      if (!mounted) return;
      setState(() => _videoTracks = selectableVideoTracks(tracks.video));
    });
    _trackSubscription = player.stream.track.listen((track) {
      if (!mounted) return;
      setState(() => _selectedTrack = track.video);
    });
  }

  @override
  void dispose() {
    _tracksSubscription?.cancel();
    _trackSubscription?.cancel();
    super.dispose();
  }

  Future<void> _openQuality() async {
    final handle = ref.read(playerSettingsHandleProvider);
    if (handle.open != null) {
      await handle.open!(initialTab: 1);
      return;
    }
  }

  @override
  Widget build(BuildContext context) {
    final handle = ref.watch(playerSettingsHandleProvider);
    final streamUrl =
        StreamPlayerScope.maybeOf(context)?.streamUrl ?? handle.streamUrl;
    final hlsAsync = ref.watch(hlsPlaylistInfoProvider(streamUrl));
    final hlsInfo = hlsAsync.valueOrNull;
    final hlsHeights = hlsInfo?.variantHeights ?? const <int>[];
    final hlsParseComplete =
        detectStreamFormat(streamUrl) != StreamFormat.hls ||
        hlsAsync is AsyncData;
    final showQuality = supportsQualityMenu(
      streamUrl,
      _videoTracks,
      hlsVariantHeights: hlsHeights,
      hlsParseComplete: hlsParseComplete,
      playbackHeight: handle.playbackHeight,
    );

    if (handle.open == null || !showQuality) {
      return const SizedBox.shrink();
    }

    final controlsTheme = MaterialVideoControlsTheme.maybeOf(context);
    final isFullscreen = FullscreenInheritedWidget.maybeOf(context) != null;
    final theme = isFullscreen
        ? controlsTheme?.fullscreen ??
            kDefaultMaterialVideoControlsThemeDataFullscreen
        : controlsTheme?.normal ?? kDefaultMaterialVideoControlsThemeData;

    final label = currentQualityLabel(
      selected: _selectedTrack,
      available: _videoTracks,
    );

    return IconButton(
      onPressed: _openQuality,
      icon: const Icon(Icons.hd_outlined),
      iconSize: theme.buttonBarButtonSize,
      color: theme.buttonBarButtonColor,
      tooltip: 'Quality · $label',
    );
  }
}
