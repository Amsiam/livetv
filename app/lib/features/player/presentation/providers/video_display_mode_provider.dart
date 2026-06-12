import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/video_display_mode.dart';

class VideoDisplayModeNotifier extends Notifier<VideoDisplayMode> {
  @override
  VideoDisplayMode build() => VideoDisplayMode.fit;

  void setMode(VideoDisplayMode mode) => state = mode;

  void cycle() {
    final values = VideoDisplayMode.values;
    final next = (values.indexOf(state) + 1) % values.length;
    state = values[next];
  }
}

final videoDisplayModeProvider =
    NotifierProvider<VideoDisplayModeNotifier, VideoDisplayMode>(
  VideoDisplayModeNotifier.new,
);
