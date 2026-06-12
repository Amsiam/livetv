import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../providers/player_settings_handle_provider.dart';

class LiveTvPlayerSettingsButton extends ConsumerWidget {
  const LiveTvPlayerSettingsButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final open = ref.watch(playerSettingsHandleProvider).open;
    if (open == null) return const SizedBox.shrink();

    final controlsTheme = _controlsTheme(context);

    return IconButton(
      onPressed: open,
      icon: const Icon(Icons.tune),
      iconSize: controlsTheme.buttonBarButtonSize,
      color: controlsTheme.buttonBarButtonColor,
      tooltip: 'Player settings',
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
