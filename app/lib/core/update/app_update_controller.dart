import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/update/app_update_info.dart';
import 'package:livetv_app/core/update/app_update_service.dart';

class AppUpdateState {
  const AppUpdateState({
    this.info,
    this.checkComplete = false,
    this.optionalDismissed = false,
    this.isDownloading = false,
    this.progress = 0,
    this.errorMessage,
  });

  final AppUpdateInfo? info;
  final bool checkComplete;
  final bool optionalDismissed;
  final bool isDownloading;
  final double progress;
  final String? errorMessage;

  bool get shouldShowForceScreen =>
      checkComplete &&
      info != null &&
      info!.updateAvailable &&
      info!.forceUpdate;

  bool get shouldShowOptionalDialog =>
      checkComplete &&
      !optionalDismissed &&
      info != null &&
      info!.canInstall &&
      info!.updateAvailable &&
      !info!.forceUpdate;

  AppUpdateState copyWith({
    AppUpdateInfo? info,
    bool? checkComplete,
    bool? optionalDismissed,
    bool? isDownloading,
    double? progress,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AppUpdateState(
      info: info ?? this.info,
      checkComplete: checkComplete ?? this.checkComplete,
      optionalDismissed: optionalDismissed ?? this.optionalDismissed,
      isDownloading: isDownloading ?? this.isDownloading,
      progress: progress ?? this.progress,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

class AppUpdateController extends StateNotifier<AppUpdateState> {
  AppUpdateController(this._ref) : super(const AppUpdateState()) {
    checkForUpdate();
  }

  final Ref _ref;

  AppUpdateService get _service => _ref.read(appUpdateServiceProvider);

  Future<void> checkForUpdate() async {
    try {
      final info = await _service.checkForUpdate();
      state = state.copyWith(
        info: info,
        checkComplete: true,
        clearError: true,
      );
    } catch (error) {
      state = state.copyWith(
        checkComplete: true,
        errorMessage: error.toString(),
      );
    }
  }

  void dismissOptionalUpdate() {
    state = state.copyWith(optionalDismissed: true);
  }

  Future<void> downloadAndInstall() async {
    final info = state.info;
    if (info == null || !info.canInstall || state.isDownloading) return;

    state = state.copyWith(isDownloading: true, progress: 0, clearError: true);

    try {
      final filePath = await _service.downloadApk(
        info.downloadUrl,
        onProgress: (value) {
          state = state.copyWith(progress: value);
        },
      );
      await _service.installApk(filePath);
      state = state.copyWith(isDownloading: false, progress: 1);
    } catch (error) {
      state = state.copyWith(
        isDownloading: false,
        errorMessage: error.toString(),
      );
    }
  }
}

final appUpdateControllerProvider =
    StateNotifierProvider<AppUpdateController, AppUpdateState>((ref) {
  return AppUpdateController(ref);
});
