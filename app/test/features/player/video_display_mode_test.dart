import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/features/player/domain/video_display_mode.dart';

void main() {
  test('maps display modes to BoxFit', () {
    expect(VideoDisplayMode.fit.boxFit, BoxFit.contain);
    expect(VideoDisplayMode.fill.boxFit, BoxFit.cover);
    expect(VideoDisplayMode.stretch.boxFit, BoxFit.fill);
    expect(VideoDisplayMode.center.boxFit, BoxFit.none);
  });
}
