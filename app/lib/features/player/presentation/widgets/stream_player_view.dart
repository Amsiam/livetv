import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../../domain/player_brightness_mode.dart';
import '../../domain/stream_format.dart';
import '../../domain/stream_playback_settings.dart';
import '../../domain/video_display_mode.dart';
import '../providers/hls_playlist_info_provider.dart';
import '../providers/pip_mode_provider.dart';
import '../providers/player_brightness_mode_provider.dart';
import '../providers/stream_playback_settings_provider.dart';
import '../providers/player_settings_handle_provider.dart';
import '../providers/video_display_mode_provider.dart';
import '../utils/player_orientation.dart';
import '../utils/stream_playback_configurator.dart';
import '../utils/stream_quality_utils.dart';
import 'live_tv_player_controls.dart';
import 'live_tv_video_controls.dart';
import 'stream_player_scope.dart';
import 'player_settings_sheet.dart';

enum PlayerStatus { idle, loading, playing, error }

class StreamPlayerView extends ConsumerStatefulWidget {
  const StreamPlayerView({
    super.key,
    required this.streamUrl,
    required this.title,
    this.onError,
    this.onPlaybackFailed,
    this.onPlaying,
  });

  final String streamUrl;
  final String title;
  final VoidCallback? onError;
  final Future<bool> Function(String message)? onPlaybackFailed;
  final VoidCallback? onPlaying;

  @override
  ConsumerState<StreamPlayerView> createState() => _StreamPlayerViewState();
}

class _StreamPlayerViewState extends ConsumerState<StreamPlayerView> {
  static const _playbackTimeout = Duration(seconds: 25);
  static const _playheadConfirmThreshold = Duration(milliseconds: 500);

  late final Player _player;
  late final VideoController _controller;
  late final StreamPlaybackConfigurator _playbackConfigurator;
  late final PlayerSettingsHandle _settingsHandle;
  final List<StreamSubscription<dynamic>> _subscriptions = [];

  PlayerStatus _status = PlayerStatus.loading;
  String? _errorMessage;
  Timer? _playbackTimeoutTimer;
  Timer? _errorDebounce;
  int _loadGeneration = 0;
  bool _failureReported = false;
  bool _playbackConfirmed = false;

  @override
  void initState() {
    super.initState();
    _settingsHandle = ref.read(playerSettingsHandleProvider);
    final settings = ref.read(streamPlaybackSettingsProvider);
    _player = Player(
      configuration: PlayerConfiguration(
        bufferSize: settings.bufferBytes,
      ),
    );
    _controller = VideoController(_player);
    _playbackConfigurator = StreamPlaybackConfigurator(_player);
    _bindPlayerStreams();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _settingsHandle.open = _openPlayerSettings;
      _settingsHandle.title = widget.title;
      _settingsHandle.streamUrl = widget.streamUrl;
      unawaited(
        ref.read(screenBrightnessServiceProvider).applyMode(
              ref.read(playerBrightnessModeProvider),
            ),
      );
    });
    unawaited(_load(widget.streamUrl));
  }

  Future<void> _openPlayerSettings({int initialTab = 0}) async {
    if (!mounted) return;
    await PlayerSettingsSheet.show(
      context,
      title: widget.title,
      streamUrl: widget.streamUrl,
      tracks: selectableVideoTracks(_player.state.tracks.video),
      selectedTrack: _player.state.track.video,
      onApply: () => _applyPlaybackSettings(_player.state.tracks.video),
      initialTab: initialTab,
    );
  }

  void _bindPlayerStreams() {
    _subscriptions
      ..add(_player.stream.videoParams.listen((params) {
        final height = params.h ?? 0;
        if (height > 0) {
          _settingsHandle.playbackHeight = height;
        }
        if ((params.w ?? 0) > 0 && height > 0) {
          _markPlaybackStarted();
        }
      }))
      ..add(_player.stream.position.listen((position) {
        if (position >= _playheadConfirmThreshold) {
          _markPlaybackStarted();
        }
      }))
      ..add(_player.stream.error.listen(_onPlayerError))
      ..add(_player.stream.tracks.listen((tracks) {
        unawaited(_applyPlaybackSettings(tracks.video));
      }));
  }

  @override
  void didUpdateWidget(covariant StreamPlayerView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.streamUrl != widget.streamUrl) {
      ref
          .read(streamPlaybackSettingsProvider.notifier)
          .selectAutoForAdaptiveStream(widget.streamUrl);
      _settingsHandle.title = widget.title;
      _settingsHandle.streamUrl = widget.streamUrl;
      unawaited(_load(widget.streamUrl));
    } else if (oldWidget.title != widget.title) {
      _settingsHandle.title = widget.title;
    }
  }

  void _onPipModeChanged(bool? previous, bool next) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (!_playbackConfirmed) return;

      _playbackConfirmed = true;
      _playbackTimeoutTimer?.cancel();
      _errorDebounce?.cancel();

      if (_status != PlayerStatus.playing || _errorMessage != null) {
        setState(() {
          _status = PlayerStatus.playing;
          _errorMessage = null;
        });
      }

      if (!_player.state.playing) {
        unawaited(_player.play());
      }
    });
  }

  void _onSettingsChanged(StreamPlaybackSettings? previous, StreamPlaybackSettings next) {
    if (previous == next) return;
    unawaited(_applyPlaybackSettings(_player.state.tracks.video));
  }

  bool get _showLoadingOverlay =>
      _status != PlayerStatus.error && !_playbackConfirmed;

  bool _isNonFatalStreamError(String error) {
    final lower = error.toLowerCase();
    return lower.contains('seekable') ||
        lower.contains('cannot seek') ||
        lower.contains('force-seekable') ||
        lower.contains('ffurl') ||
        lower.contains('tcp') ||
        RegExp(r'0x[0-9a-f]+').hasMatch(lower);
  }

  void _markPlaybackStarted() {
    if (!mounted) return;
    _playbackConfirmed = true;
    _errorDebounce?.cancel();
    _playbackTimeoutTimer?.cancel();
    if (_status == PlayerStatus.playing && _errorMessage == null) return;
    setState(() {
      _status = PlayerStatus.playing;
      _errorMessage = null;
    });
    widget.onPlaying?.call();
  }

  void _onPlayerError(String error) {
    if (!mounted || _isNonFatalStreamError(error)) return;
    if (_playbackConfirmed) return;

    _errorDebounce?.cancel();
    _errorDebounce = Timer(const Duration(milliseconds: 800), () {
      if (!mounted || _playbackConfirmed) return;
      unawaited(_failPlayback(error));
    });
  }

  Future<void> _failPlayback(String message) async {
    if (!mounted || _failureReported || _playbackConfirmed) return;

    _playbackTimeoutTimer?.cancel();
    _errorDebounce?.cancel();

    final handled = await widget.onPlaybackFailed?.call(message) ?? false;
    if (handled) return;

    _failureReported = true;

    if (!mounted) return;
    setState(() {
      _status = PlayerStatus.error;
      _errorMessage = message;
    });
    widget.onError?.call();
  }

  void _startPlaybackTimeout(int generation) {
    _playbackTimeoutTimer?.cancel();
    _playbackTimeoutTimer = Timer(_playbackTimeout, () {
      if (!mounted || generation != _loadGeneration) return;
      if (!_playbackConfirmed) {
        _failPlayback('Stream timed out. Tap Retry or try another channel.');
      }
    });
  }

  Future<void> _applyPlaybackSettings(List<VideoTrack> tracks) async {
    if (!mounted) return;

    _syncQualityForStream(tracks);

    final settings = ref.read(streamPlaybackSettingsProvider);
    await _playbackConfigurator.applyBufferSettings(settings);
    await _playbackConfigurator.applyQuality(
      url: widget.streamUrl,
      settings: settings,
      tracks: tracks,
    );
  }

  void _syncQualityForStream(List<VideoTrack> tracks) {
    final hlsAsync = ref.read(hlsPlaylistInfoProvider(widget.streamUrl));
    final hlsHeights = hlsAsync.valueOrNull?.variantHeights ?? const <int>[];
    final hlsParseComplete =
        detectStreamFormat(widget.streamUrl) != StreamFormat.hls ||
        hlsAsync is AsyncData;
    final settings = ref.read(streamPlaybackSettingsProvider);
    final presets = qualityPresetsForStream(
      widget.streamUrl,
      tracks,
      minBitrateKbps: settings.minBitrateKbps,
      hlsVariantHeights: hlsHeights,
      hlsParseComplete: hlsParseComplete,
      playbackHeight: _settingsHandle.playbackHeight,
    );

    ref.read(streamPlaybackSettingsProvider.notifier).ensureQualityInPresets(presets);
  }

  Future<void> _load(String url) async {
    final generation = ++_loadGeneration;
    _failureReported = false;
    _playbackConfirmed = false;
    _errorDebounce?.cancel();
    _playbackTimeoutTimer?.cancel();

    setState(() {
      _status = PlayerStatus.loading;
      _errorMessage = null;
    });
    _startPlaybackTimeout(generation);

    if (url.trim().isEmpty) {
      _failPlayback('No stream URL for this channel.');
      return;
    }

    final settings = ref.read(streamPlaybackSettingsProvider);
    await _playbackConfigurator.applyNetworkOptions(url);
    await _playbackConfigurator.applyBufferSettings(settings);
    unawaited(_startPlayer(url, generation));
  }

  Future<void> _startPlayer(String url, int generation) async {
    try {
      await _player.open(Media(url), play: true);
      if (!mounted || generation != _loadGeneration) return;
      await _applyPlaybackSettings(_player.state.tracks.video);
    } catch (error) {
      if (!mounted || generation != _loadGeneration) return;
      _failPlayback(error.toString());
    }
  }

  @override
  void dispose() {
    _playbackTimeoutTimer?.cancel();
    _errorDebounce?.cancel();
    for (final subscription in _subscriptions) {
      subscription.cancel();
    }
    _settingsHandle.open = null;
    _settingsHandle.title = '';
    _settingsHandle.streamUrl = '';
    _settingsHandle.playbackHeight = null;
    _player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pipMode = ref.watch(pipModeProvider);
    final displayMode = ref.watch(videoDisplayModeProvider);
    final brightnessMode = ref.watch(playerBrightnessModeProvider);
    ref.listen(pipModeProvider, _onPipModeChanged);
    ref.listen(streamPlaybackSettingsProvider, _onSettingsChanged);

    final videoFit = pipMode ? BoxFit.cover : displayMode.boxFit;

    final video = Video(
      key: const ValueKey('live-tv-video'),
      controller: _controller,
      controls: pipMode ? null : liveTvVideoControls,
      fit: videoFit,
      alignment: displayMode == VideoDisplayMode.center
          ? Alignment.center
          : Alignment.center,
      onEnterFullscreen: handlePlayerEnterFullscreen,
      onExitFullscreen: handlePlayerExitFullscreen,
    );

    return StreamPlayerScope(
      streamUrl: widget.streamUrl,
      applyPlaybackSettings: () => _applyPlaybackSettings(_player.state.tracks.video),
      child: ClipRect(
        child: Stack(
          fit: StackFit.expand,
          clipBehavior: Clip.hardEdge,
          children: [
            ColoredBox(
              color: Colors.black,
              child: pipMode
                  ? video
                  : MaterialVideoControlsTheme(
                      normal: liveTvPlayerControlsNormal,
                      fullscreen: liveTvPlayerControlsFullscreen(
                        manualBrightnessGesture:
                            brightnessMode == PlayerBrightnessMode.manual,
                      ),
                      child: video,
                    ),
            ),
            if (_showLoadingOverlay)
              const Positioned.fill(
                child: ColoredBox(
                  color: Colors.black,
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),
            if (_status == PlayerStatus.error)
              Positioned.fill(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final compact = constraints.maxHeight < 220;
                    final padding = compact ? 8.0 : 12.0;
                    final iconSize = compact ? 24.0 : 36.0;
                    final spacing = compact ? 4.0 : 8.0;

                    return SingleChildScrollView(
                      padding: EdgeInsets.all(padding),
                      child: ConstrainedBox(
                        constraints: BoxConstraints(
                          minHeight: constraints.maxHeight - padding * 2,
                          maxWidth: constraints.maxWidth - padding * 2,
                        ),
                        child: Center(
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            child: SizedBox(
                              width: constraints.maxWidth - padding * 2,
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.error_outline,
                                    size: iconSize,
                                    color: Colors.white70,
                                  ),
                                  SizedBox(height: spacing),
                                  Text(
                                    'Playback failed',
                                    textAlign: TextAlign.center,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleSmall
                                        ?.copyWith(
                                          color: Colors.white,
                                          fontSize: compact ? 12 : 14,
                                        ),
                                  ),
                                  if (_errorMessage != null) ...[
                                    SizedBox(height: spacing),
                                    Text(
                                      _errorMessage!,
                                      textAlign: TextAlign.center,
                                      maxLines: compact ? 2 : 3,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        color: Colors.white60,
                                        fontSize: compact ? 10 : 12,
                                      ),
                                    ),
                                  ],
                                  SizedBox(height: spacing),
                                  FilledButton(
                                    onPressed: () =>
                                        unawaited(_load(widget.streamUrl)),
                                    style: FilledButton.styleFrom(
                                      padding: EdgeInsets.symmetric(
                                        horizontal: 16,
                                        vertical: compact ? 6 : 10,
                                      ),
                                      minimumSize: Size(0, compact ? 32 : 36),
                                    ),
                                    child: const Text('Retry'),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}
