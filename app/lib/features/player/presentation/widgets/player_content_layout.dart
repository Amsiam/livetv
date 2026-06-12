import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/features/player/presentation/providers/pip_mode_provider.dart';

/// Keeps the [player] widget mounted while toggling PiP and resizes it to fill
/// the screen in PiP mode instead of the 16:9 slot.
class PlayerContentLayout extends ConsumerWidget {
  const PlayerContentLayout({
    super.key,
    required this.player,
    required this.belowPlayer,
  });

  final Widget player;
  final Widget belowPlayer;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pipMode = ref.watch(pipModeProvider);

    return LayoutBuilder(
      builder: (context, constraints) {
        final maxHeight = constraints.maxHeight;
        final maxWidth = constraints.maxWidth;
        final videoHeight = pipMode
            ? maxHeight
            : (maxWidth * 9 / 16).clamp(0, maxHeight).toDouble();

        // Keep a stable Stack so the player state is not recreated on PiP toggle.
        return Stack(
          clipBehavior: Clip.hardEdge,
          fit: StackFit.expand,
          children: [
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              height: videoHeight,
              child: player,
            ),
            if (!pipMode)
              Positioned(
                top: videoHeight,
                left: 0,
                right: 0,
                bottom: 0,
                child: belowPlayer,
              ),
          ],
        );
      },
    );
  }
}
