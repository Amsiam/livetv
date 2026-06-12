import 'dart:async';

import 'package:android_pip/android_pip.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final pipModeProvider = StateProvider<bool>((ref) => false);

final pipServiceProvider = Provider<PipService>((ref) {
  return PipService(
    onModeChanged: (active) {
      ref.read(pipModeProvider.notifier).state = active;
    },
  );
});

class PipService {
  PipService({required this.onModeChanged}) {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      _pip = AndroidPIP(
        onPipEntered: () => onModeChanged(true),
        onPipExited: () => onModeChanged(false),
        onPipMaximised: () => onModeChanged(false),
      );
    }
  }

  final void Function(bool) onModeChanged;
  AndroidPIP? _pip;

  Future<bool> get isAvailable async {
    if (_pip == null) return false;
    return AndroidPIP.isPipAvailable;
  }

  Future<bool> enter() async {
    if (_pip == null) return false;
    return _pip!.enterPipMode(aspectRatio: const [16, 9]);
  }
}
