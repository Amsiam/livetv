import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/app.dart';
import 'package:livetv_app/core/monitoring/crash_reporting.dart';
import 'package:media_kit/media_kit.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await configureCrashReporting();
  MediaKit.ensureInitialized();
  runApp(
    ProviderScope(
      observers: [CrashlyticsProviderObserver()],
      child: const LiveTvApp(),
    ),
  );
}
