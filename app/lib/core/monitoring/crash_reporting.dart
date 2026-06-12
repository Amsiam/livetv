import 'package:dio/dio.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/monitoring/performance_monitoring.dart';
import 'package:livetv_app/firebase_options.dart';

bool get _crashReportingSupported => !kIsWeb;

/// Initializes Firebase, Performance, and Crashlytics error reporting.
Future<void> configureCrashReporting() async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  await configurePerformanceMonitoring();

  if (!_crashReportingSupported) {
    FlutterError.onError = FlutterError.presentError;
    return;
  }

  final crashlytics = FirebaseCrashlytics.instance;
  await crashlytics.setCrashlyticsCollectionEnabled(kReleaseMode);

  if (kReleaseMode) {
    FlutterError.onError = crashlytics.recordFlutterFatalError;
    PlatformDispatcher.instance.onError = (error, stack) {
      crashlytics.recordError(error, stack, fatal: true);
      return true;
    };
  } else {
    FlutterError.onError = FlutterError.presentError;
  }
}

/// Records a non-fatal error (API failures, provider errors, etc.).
Future<void> recordAppError(
  Object error,
  StackTrace stack, {
  String? reason,
  bool fatal = false,
}) async {
  if (!kReleaseMode || !_crashReportingSupported) return;

  await FirebaseCrashlytics.instance.recordError(
    error,
    stack,
    reason: reason,
    fatal: fatal,
  );
}

void recordDioError(DioException error) {
  if (!kReleaseMode || !_crashReportingSupported) return;

  final request = error.requestOptions;
  FirebaseCrashlytics.instance.setCustomKey('api_path', request.path);
  final statusCode = error.response?.statusCode;
  if (statusCode != null) {
    FirebaseCrashlytics.instance.setCustomKey('http_status', statusCode);
  }

  recordAppError(
    error,
    error.stackTrace,
    reason: 'Dio ${error.type.name} ${request.method} ${request.path}',
  );
}

class CrashlyticsProviderObserver extends ProviderObserver {
  @override
  void providerDidFail(
    ProviderBase<Object?> provider,
    Object error,
    StackTrace stackTrace,
    ProviderContainer container,
  ) {
    recordAppError(
      error,
      stackTrace,
      reason: 'Provider ${provider.name ?? provider.runtimeType}',
    );
  }
}
