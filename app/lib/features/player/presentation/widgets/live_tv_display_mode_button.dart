import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../../domain/video_display_mode.dart';
import '../providers/player_settings_handle_provider.dart';
import '../providers/video_display_mode_provider.dart';

class LiveTvDisplayModeButton extends ConsumerWidget {
  const LiveTvDisplayModeButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(videoDisplayModeProvider);
    final handle = ref.watch(playerSettingsHandleProvider);
    final controlsTheme = _controlsTheme(context);

    return IconButton(
      onPressed: () async {
        if (handle.open != null) {
          await handle.open!(initialTab: 0);
        }
      },
      onLongPress: () {
        ref.read(videoDisplayModeProvider.notifier).cycle();
      },
      icon: Icon(mode.icon),
      iconSize: controlsTheme.buttonBarButtonSize,
      color: controlsTheme.buttonBarButtonColor,
      tooltip: 'Display: ${mode.label} (long-press to cycle)',
    );
  }

  MaterialVideoControlsThemeData _controlsTheme(BuildContext context) {
    final theme = MaterialVideoControlsTheme.maybeOf(context);
    final isFullscreen = FullscreenInheritedWidget.maybeOf(context) != null;
    if (theme == null) {
      return isFullscreen
          ? kDefaultMaterialVideoControlsThemeDataFullscreen
          : kDefaultMaterialVideoControlsThemeData;
    }
    return isFullscreen ? theme.fullscreen : theme.normal;
  }
}
