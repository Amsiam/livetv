import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../providers/pip_mode_provider.dart';
import '../providers/player_settings_handle_provider.dart';
import '../utils/live_tv_fullscreen.dart';
import 'live_tv_display_mode_button.dart';
import 'live_tv_player_settings_button.dart';
import 'live_tv_quality_button.dart';

MaterialVideoControlsThemeData liveTvControlsTheme(BuildContext context) {
  final theme = MaterialVideoControlsTheme.maybeOf(context);
  final isFullscreen = FullscreenInheritedWidget.maybeOf(context) != null;
  if (theme == null) {
    return isFullscreen
        ? kDefaultMaterialVideoControlsThemeDataFullscreen
        : kDefaultMaterialVideoControlsThemeData;
  }
  return isFullscreen ? theme.fullscreen : theme.normal;
}

const _primaryControls = [
  Spacer(flex: 2),
  MaterialPlayOrPauseButton(iconSize: 48),
  Spacer(flex: 2),
];

const _bottomControls = [
  MaterialPositionIndicator(),
  Spacer(),
  LiveTvDisplayModeButton(),
  LiveTvQualityButton(),
  LiveTvPipButton(),
  LiveTvFullscreenButton(),
];

const _fullscreenTopControls = [
  Expanded(child: LiveTvPlayerTopTitle()),
  LiveTvPlayerSettingsButton(),
];

const liveTvPlayerControlsNormal = MaterialVideoControlsThemeData(
  automaticallyImplySkipNextButton: false,
  automaticallyImplySkipPreviousButton: false,
  // Live HLS: no seek bar — avoids media_kit MaterialSeekBar crash on dispose
  // and seeking is not meaningful on live streams.
  displaySeekBar: false,
  volumeGesture: false,
  brightnessGesture: false,
  seekGesture: false,
  gesturesEnabledWhileControlsVisible: true,
  seekOnDoubleTap: false,
  topButtonBar: [],
  primaryButtonBar: _primaryControls,
  bottomButtonBar: _bottomControls,
  bottomButtonBarMargin: EdgeInsets.only(left: 12, right: 8),
);

MaterialVideoControlsThemeData liveTvPlayerControlsFullscreen({
  required bool manualBrightnessGesture,
}) =>
    MaterialVideoControlsThemeData(
      automaticallyImplySkipNextButton: false,
      automaticallyImplySkipPreviousButton: false,
      displaySeekBar: false,
      volumeGesture: true,
      brightnessGesture: manualBrightnessGesture,
      seekGesture: false,
      gesturesEnabledWhileControlsVisible: true,
      seekOnDoubleTap: false,
      topButtonBar: _fullscreenTopControls,
      topButtonBarMargin: EdgeInsets.only(left: 16, right: 8, top: 8),
      primaryButtonBar: [
        Spacer(flex: 2),
        MaterialPlayOrPauseButton(iconSize: 56),
        Spacer(flex: 2),
      ],
      bottomButtonBar: _bottomControls,
      bottomButtonBarMargin: EdgeInsets.only(left: 16, right: 8, bottom: 42),
    );

class LiveTvPlayerTopTitle extends ConsumerWidget {
  const LiveTvPlayerTopTitle({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final title = ref.watch(playerSettingsHandleProvider).title;
    if (title.isEmpty) return const SizedBox.shrink();

    final controlsTheme = liveTvControlsTheme(context);

    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        title,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: controlsTheme.buttonBarButtonColor,
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class LiveTvFullscreenButton extends StatelessWidget {
  const LiveTvFullscreenButton({super.key});

  @override
  Widget build(BuildContext context) {
    final controlsTheme = liveTvControlsTheme(context);

    return IconButton(
      onPressed: () => unawaited(toggleLiveTvFullscreen(context)),
      icon: Icon(
        isFullscreen(context) ? Icons.fullscreen_exit : Icons.fullscreen,
      ),
      iconSize: controlsTheme.buttonBarButtonSize,
      color: controlsTheme.buttonBarButtonColor,
      tooltip: isFullscreen(context) ? 'Exit fullscreen' : 'Fullscreen',
    );
  }
}

class LiveTvPipButton extends ConsumerStatefulWidget {
  const LiveTvPipButton({super.key});

  @override
  ConsumerState<LiveTvPipButton> createState() => _LiveTvPipButtonState();
}

class _LiveTvPipButtonState extends ConsumerState<LiveTvPipButton> {
  bool _available = false;

  @override
  void initState() {
    super.initState();
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      unawaited(_checkAvailability());
    }
  }

  Future<void> _checkAvailability() async {
    final available = await ref.read(pipServiceProvider).isAvailable;
    if (mounted) {
      setState(() => _available = available);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_available) return const SizedBox.shrink();

    final controlsTheme = liveTvControlsTheme(context);

    return IconButton(
      onPressed: () => unawaited(ref.read(pipServiceProvider).enter()),
      icon: const Icon(Icons.picture_in_picture_alt_outlined),
      iconSize: controlsTheme.buttonBarButtonSize,
      color: controlsTheme.buttonBarButtonColor,
      tooltip: 'Picture in picture',
    );
  }
}
