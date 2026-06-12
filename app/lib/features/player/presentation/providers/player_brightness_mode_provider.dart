import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/screen_brightness_service.dart';
import '../../domain/player_brightness_mode.dart';

class PlayerBrightnessModeNotifier extends Notifier<PlayerBrightnessMode> {
  @override
  PlayerBrightnessMode build() => PlayerBrightnessMode.auto;

  void setMode(PlayerBrightnessMode mode) {
    if (state == mode) return;
    state = mode;
    unawaited(ref.read(screenBrightnessServiceProvider).applyMode(mode));
  }
}

final screenBrightnessServiceProvider = Provider<ScreenBrightnessService>(
  (ref) => ScreenBrightnessService(),
);

final playerBrightnessModeProvider =
    NotifierProvider<PlayerBrightnessModeNotifier, PlayerBrightnessMode>(
  PlayerBrightnessModeNotifier.new,
);
