import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/update/app_update_controller.dart';
import 'package:livetv_app/core/update/app_update_info.dart';

/// Checks for APK updates on launch and blocks or prompts the user.
class AppUpdateGate extends ConsumerWidget {
  const AppUpdateGate({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final updateState = ref.watch(appUpdateControllerProvider);

    if (updateState.shouldShowForceScreen) {
      return _ForceUpdateScreen(state: updateState);
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        child,
        if (updateState.shouldShowOptionalDialog)
          _OptionalUpdateOverlay(
            info: updateState.info!,
            onLater: () =>
                ref.read(appUpdateControllerProvider.notifier).dismissOptionalUpdate(),
            onUpdate: () =>
                ref.read(appUpdateControllerProvider.notifier).downloadAndInstall(),
          ),
        if (updateState.isDownloading) _DownloadingOverlay(state: updateState),
      ],
    );
  }
}

/// In-tree overlay — [showDialog] fails from [MaterialApp.builder] (no Navigator).
class _OptionalUpdateOverlay extends StatelessWidget {
  const _OptionalUpdateOverlay({
    required this.info,
    required this.onLater,
    required this.onUpdate,
  });

  final AppUpdateInfo info;
  final VoidCallback onLater;
  final VoidCallback onUpdate;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: Colors.black54,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: Card(
            margin: const EdgeInsets.all(24),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Update available (${info.versionName})',
                    style: theme.textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    info.releaseNotes.isNotEmpty
                        ? info.releaseNotes
                        : 'A newer version of Live TV is available.',
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(onPressed: onLater, child: const Text('Later')),
                      const SizedBox(width: 8),
                      FilledButton(onPressed: onUpdate, child: const Text('Update')),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DownloadingOverlay extends StatelessWidget {
  const _DownloadingOverlay({required this.state});

  final AppUpdateState state;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.black54,
      child: Center(
        child: Card(
          margin: const EdgeInsets.all(32),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('Downloading update…'),
                const SizedBox(height: 16),
                SizedBox(
                  width: 220,
                  child: LinearProgressIndicator(
                    value: state.progress > 0 ? state.progress : null,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ForceUpdateScreen extends ConsumerWidget {
  const _ForceUpdateScreen({required this.state});

  final AppUpdateState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final info = state.info!;
    final theme = Theme.of(context);
    final canInstall = info.canInstall;

    return PopScope(
      canPop: false,
      child: Material(
        color: Colors.black,
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Spacer(),
                Icon(Icons.system_update_alt, size: 72, color: theme.colorScheme.primary),
                const SizedBox(height: 24),
                Text(
                  'Update required',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                Text(
                  'Please install version ${info.versionName} to continue using Live TV.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyLarge?.copyWith(color: Colors.white70),
                ),
                if (info.releaseNotes.isNotEmpty) ...[
                  const SizedBox(height: 20),
                  Text(
                    info.releaseNotes,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
                if (!canInstall) ...[
                  const SizedBox(height: 20),
                  Text(
                    'Update package is not available yet. Please try again later.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                ],
                const Spacer(),
                if (state.isDownloading) ...[
                  LinearProgressIndicator(value: state.progress > 0 ? state.progress : null),
                  const SizedBox(height: 12),
                  Text(
                    '${(state.progress * 100).clamp(0, 100).toStringAsFixed(0)}% downloaded',
                    textAlign: TextAlign.center,
                  ),
                ] else if (state.errorMessage != null) ...[
                  Text(
                    state.errorMessage!,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                  const SizedBox(height: 12),
                ],
                if (canInstall)
                  FilledButton(
                    onPressed: state.isDownloading
                        ? null
                        : () =>
                            ref.read(appUpdateControllerProvider.notifier).downloadAndInstall(),
                    child: Text(state.isDownloading ? 'Downloading…' : 'Download update'),
                  ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: state.isDownloading
                      ? null
                      : () => ref.read(appUpdateControllerProvider.notifier).checkForUpdate(),
                  child: const Text('Retry check'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
