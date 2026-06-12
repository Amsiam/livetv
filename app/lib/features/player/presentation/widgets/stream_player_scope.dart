import 'package:flutter/widgets.dart';

class StreamPlayerScope extends InheritedWidget {
  const StreamPlayerScope({
    super.key,
    required this.streamUrl,
    required this.applyPlaybackSettings,
    required super.child,
  });

  final String streamUrl;
  final Future<void> Function() applyPlaybackSettings;

  static StreamPlayerScope? maybeOf(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<StreamPlayerScope>();
  }

  @override
  bool updateShouldNotify(StreamPlayerScope oldWidget) {
    return streamUrl != oldWidget.streamUrl ||
        applyPlaybackSettings != oldWidget.applyPlaybackSettings;
  }
}
