import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:livetv_app/features/player/presentation/providers/pip_mode_provider.dart';

class MainShell extends ConsumerWidget {
  const MainShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pipMode = ref.watch(pipModeProvider);

    return Scaffold(
      body: pipMode
          ? MediaQuery.removePadding(
              context: context,
              removeTop: true,
              removeBottom: true,
              child: navigationShell,
            )
          : navigationShell,
      bottomNavigationBar: pipMode
          ? null
          : NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: navigationShell.goBranch,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.sports_soccer_outlined),
            selectedIcon: Icon(Icons.sports_soccer),
            label: 'Matches',
          ),
          NavigationDestination(
            icon: Icon(Icons.live_tv_outlined),
            selectedIcon: Icon(Icons.live_tv),
            label: 'TV',
          ),
        ],
      ),
    );
  }
}

