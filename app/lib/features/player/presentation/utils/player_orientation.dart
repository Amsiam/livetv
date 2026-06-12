import 'dart:async';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:native_device_orientation/native_device_orientation.dart';

const _orientationChannel = MethodChannel('com.livetv.livetv_app/orientation');

/// Orientations allowed on embedded player screens.
const playerPageOrientations = <DeviceOrientation>[
  DeviceOrientation.portraitUp,
  DeviceOrientation.landscapeLeft,
  DeviceOrientation.landscapeRight,
];

final _communicator = NativeDeviceOrientationCommunicator();
StreamSubscription<NativeDeviceOrientation>? _sensorSubscription;
NativeDeviceOrientation? _lastAppliedLandscape;
bool _playerFullscreenActive = false;

Future<void> applyPlayerPageOrientations() async {
  if (!Platform.isAndroid && !Platform.isIOS) return;
  if (Platform.isAndroid) {
    await _invokeAndroidOrientation('exitFullscreen');
  }
  await _setOrientations(playerPageOrientations);
}

Future<void> resetPlayerOrientations() async {
  if (!Platform.isAndroid && !Platform.isIOS) return;
  _playerFullscreenActive = false;
  await _stopSensorTracking();
  if (Platform.isAndroid) {
    await _invokeAndroidOrientation('exitFullscreen');
  }
  await _setOrientations(DeviceOrientation.values);
}

/// Lock landscape after the fullscreen route is visible (not before).
Future<void> preparePlayerFullscreen() async {
  if (!Platform.isAndroid && !Platform.isIOS) return;
  if (_playerFullscreenActive) return;
  _playerFullscreenActive = true;

  await _stopSensorTracking();
  _lastAppliedLandscape = null;

  if (Platform.isAndroid) {
    // Native SENSOR_LANDSCAPE handles left/right; avoid Dart sensor overrides
    // that fight the activity and rotate the whole app under the player.
    await _invokeAndroidOrientation('enterFullscreen');
    return;
  }

  await _setOrientations(const [
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);

  _sensorSubscription = _communicator
      .onOrientationChanged(useSensor: true)
      .listen(_applySensorOrientation);

  final current = await _communicator.orientation(useSensor: true);
  await _applySensorOrientation(current);
}

Future<void> _stopSensorTracking() async {
  await _sensorSubscription?.cancel();
  _sensorSubscription = null;
  _lastAppliedLandscape = null;
}

Future<void> _applySensorOrientation(
  NativeDeviceOrientation orientation,
) async {
  if (!_playerFullscreenActive) return;
  if (orientation != NativeDeviceOrientation.landscapeLeft &&
      orientation != NativeDeviceOrientation.landscapeRight) {
    return;
  }
  if (_lastAppliedLandscape == orientation) return;
  _lastAppliedLandscape = orientation;

  final deviceOrientation = orientation.deviceOrientation;
  if (deviceOrientation == null) return;
  await _setOrientations([deviceOrientation]);
}

/// Hide system UI after the fullscreen route is visible.
Future<void> applyPlayerFullscreenUi() async {
  if (!Platform.isAndroid && !Platform.isIOS) return;

  await SystemChrome.setEnabledSystemUIMode(
    SystemUiMode.immersiveSticky,
    overlays: [],
  );
}

Future<void> exitPlayerFullscreen() async {
  if (!Platform.isAndroid && !Platform.isIOS) return;
  if (!_playerFullscreenActive) return;
  _playerFullscreenActive = false;

  await _stopSensorTracking();

  await SystemChrome.setEnabledSystemUIMode(
    SystemUiMode.manual,
    overlays: SystemUiOverlay.values,
  );
  await applyPlayerPageOrientations();
}

/// Called from [Video.onEnterFullscreen] after the fullscreen route opens.
Future<void> handlePlayerEnterFullscreen() async {
  await preparePlayerFullscreen();
  await applyPlayerFullscreenUi();
}

/// Called from [Video.onExitFullscreen] when the fullscreen route closes.
Future<void> handlePlayerExitFullscreen() async {
  await exitPlayerFullscreen();
}

Future<void> _invokeAndroidOrientation(
  String method, [
  Map<String, String>? arguments,
]) async {
  try {
    await _orientationChannel.invokeMethod<void>(method, arguments);
  } catch (_) {
    // Ignore on platforms without the native handler.
  }
}

/// Clear preferred orientations first so Android re-enables the rotation sensor.
Future<void> _setOrientations(List<DeviceOrientation> orientations) async {
  await SystemChrome.setPreferredOrientations([]);
  await SystemChrome.setPreferredOrientations(orientations);
}
