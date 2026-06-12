import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/player_brightness_mode.dart';
import '../providers/player_brightness_mode_provider.dart';

class PlayerBrightnessPanel extends ConsumerWidget {
  const PlayerBrightnessPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(playerBrightnessModeProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Brightness gesture',
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 4),
        ...PlayerBrightnessMode.values.map((option) {
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
              ref.read(playerBrightnessModeProvider.notifier).setMode(option);
            },
          );
        }),
      ],
    );
  }
}
