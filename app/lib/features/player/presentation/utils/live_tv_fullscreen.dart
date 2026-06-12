import 'package:flutter/material.dart';
import 'package:media_kit_video/media_kit_video.dart';

import 'player_orientation.dart';

/// Open the media_kit fullscreen route first, then lock landscape in
/// [handlePlayerEnterFullscreen] so the embedded page does not rotate early.
Future<void> enterLiveTvFullscreen(BuildContext context) async {
  if (!context.mounted) return;
  await enterFullscreen(context);
}

/// Close fullscreen and always restore embedded orientations.
Future<void> exitLiveTvFullscreen(BuildContext context) async {
  if (!context.mounted) return;
  await exitFullscreen(context);
  await exitPlayerFullscreen();
}

/// Toggle fullscreen with correct orientation ordering.
Future<void> toggleLiveTvFullscreen(BuildContext context) async {
  if (isFullscreen(context)) {
    await exitLiveTvFullscreen(context);
  } else {
    await enterLiveTvFullscreen(context);
  }
}
