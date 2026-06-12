import 'package:flutter_riverpod/flutter_riverpod.dart';

typedef OpenPlayerSettings = Future<void> Function({int initialTab});

class PlayerSettingsHandle {
  OpenPlayerSettings? open;
  String title = '';
  String streamUrl = '';
  int? playbackHeight;
}

final playerSettingsHandleProvider = Provider<PlayerSettingsHandle>(
  (ref) => PlayerSettingsHandle(),
);
