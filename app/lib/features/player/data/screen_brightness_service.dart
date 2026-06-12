import 'dart:async';

import 'package:screen_brightness_platform_interface/screen_brightness_platform_interface.dart';

import '../domain/player_brightness_mode.dart';

class ScreenBrightnessService {
  ScreenBrightnessService({ScreenBrightnessPlatform? platform})
      : _platform = platform ?? ScreenBrightnessPlatform.instance;

  final ScreenBrightnessPlatform _platform;

  Future<double> currentBrightness({required bool autoMode}) async {
    if (autoMode) {
      return _platform.system;
    }
    return _platform.application;
  }

  Stream<double> brightnessChanges({required bool autoMode}) {
    return autoMode
        ? _platform.onSystemScreenBrightnessChanged
        : _platform.onApplicationScreenBrightnessChanged;
  }

  Future<void> applyMode(PlayerBrightnessMode mode) async {
    if (mode == PlayerBrightnessMode.auto) {
      await _platform.resetApplicationScreenBrightness();
      return;
    }
    final system = await _platform.system;
    await _platform.setApplicationScreenBrightness(system);
  }

  Future<void> setBrightness({
    required double value,
    required bool autoMode,
  }) async {
    final clamped = value.clamp(0.0, 1.0);
    if (autoMode) {
      final canChange = await _platform.canChangeSystemBrightness;
      if (canChange) {
        await _platform.setSystemScreenBrightness(clamped);
        return;
      }
    }
    await _platform.setApplicationScreenBrightness(clamped);
  }
}
