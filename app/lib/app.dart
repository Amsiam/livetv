import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/bootstrap/session_bootstrap.dart';
import 'package:livetv_app/core/routing/app_router.dart';
import 'package:livetv_app/core/theme/app_theme.dart';
import 'package:livetv_app/core/update/app_update_controller.dart';
import 'package:livetv_app/core/update/app_update_gate.dart';
import 'package:livetv_app/features/player/presentation/providers/pip_mode_provider.dart';

class LiveTvApp extends ConsumerWidget {
  const LiveTvApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(sessionBootstrapProvider);
    ref.watch(pipServiceProvider);
    ref.watch(appUpdateControllerProvider);
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'Live TV',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark,
      routerConfig: router,
      builder: (context, child) {
        return AppUpdateGate(
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }
}
