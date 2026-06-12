import 'package:flutter/material.dart';

enum PlayerBrightnessMode {
  auto,
  manual,
}

extension PlayerBrightnessModeX on PlayerBrightnessMode {
  String get label => switch (this) {
        PlayerBrightnessMode.auto => 'Auto',
        PlayerBrightnessMode.manual => 'Manual',
      };

  String get description => switch (this) {
        PlayerBrightnessMode.auto =>
          'Matches device brightness (0–10). Changes with system slider.',
        PlayerBrightnessMode.manual =>
          'Adjust brightness in-app only; does not change system setting.',
      };

  IconData get icon => switch (this) {
        PlayerBrightnessMode.auto => Icons.brightness_auto,
        PlayerBrightnessMode.manual => Icons.brightness_6_outlined,
      };
}

/// Device brightness as an integer level 0–10 (matches common Android UI).
int brightnessLevelTen(double normalized) =>
    (normalized.clamp(0.0, 1.0) * 10).round().clamp(0, 10);

double brightnessFromLevelTen(int level) =>
    (level.clamp(0, 10) / 10).toDouble();
