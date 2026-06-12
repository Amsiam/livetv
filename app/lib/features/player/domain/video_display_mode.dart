import 'package:flutter/material.dart';

enum VideoDisplayMode {
  fit,
  fill,
  stretch,
  center,
}

extension VideoDisplayModeX on VideoDisplayMode {
  BoxFit get boxFit => switch (this) {
        VideoDisplayMode.fit => BoxFit.contain,
        VideoDisplayMode.fill => BoxFit.cover,
        VideoDisplayMode.stretch => BoxFit.fill,
        VideoDisplayMode.center => BoxFit.none,
      };

  String get label => switch (this) {
        VideoDisplayMode.fit => 'Fit',
        VideoDisplayMode.fill => 'Fill screen',
        VideoDisplayMode.stretch => 'Stretch',
        VideoDisplayMode.center => 'Original size',
      };

  String get description => switch (this) {
        VideoDisplayMode.fit => 'Full video, black bars if needed',
        VideoDisplayMode.fill => 'Crops edges to cover the screen',
        VideoDisplayMode.stretch => 'Stretches to fill width and height',
        VideoDisplayMode.center => 'Native resolution, centered',
      };

  IconData get icon => switch (this) {
        VideoDisplayMode.fit => Icons.fit_screen_outlined,
        VideoDisplayMode.fill => Icons.crop_free,
        VideoDisplayMode.stretch => Icons.aspect_ratio,
        VideoDisplayMode.center => Icons.photo_size_select_small_outlined,
      };
}
