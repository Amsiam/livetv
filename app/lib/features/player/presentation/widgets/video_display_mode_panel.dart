import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/video_display_mode.dart';
import '../providers/video_display_mode_provider.dart';

class VideoDisplayModePanel extends ConsumerWidget {
  const VideoDisplayModePanel({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(videoDisplayModeProvider);

    return Column(
      children: VideoDisplayMode.values.map((option) {
        final selected = mode == option;
        return ListTile(
          dense: true,
          visualDensity: VisualDensity.compact,
          contentPadding: const EdgeInsets.symmetric(horizontal: 4),
          leading: Icon(
            selected ? Icons.radio_button_checked : Icons.radio_button_off,
            size: 22,
          ),
          title: Text(option.label),
          subtitle: Text(option.description),
          trailing: Icon(option.icon, size: 20),
          onTap: () {
            ref.read(videoDisplayModeProvider.notifier).setMode(option);
          },
        );
      }).toList(),
    );
  }
}
