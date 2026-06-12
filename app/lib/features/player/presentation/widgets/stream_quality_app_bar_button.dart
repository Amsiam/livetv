import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/player_settings_handle_provider.dart';

class StreamQualityAppBarButton extends ConsumerWidget {
  const StreamQualityAppBarButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final handle = ref.watch(playerSettingsHandleProvider);
    final open = handle.open;
    if (open == null) return const SizedBox.shrink();

    return IconButton(
      onPressed: () => open(initialTab: 0),
      icon: const Icon(Icons.tune),
      tooltip: 'Player settings',
    );
  }
}
