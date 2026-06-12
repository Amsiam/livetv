import 'package:flutter/material.dart';
import 'package:media_kit/media_kit.dart';

import 'stream_quality_panel.dart';

class StreamQualitySheet extends StatelessWidget {
  const StreamQualitySheet({
    super.key,
    required this.streamUrl,
    required this.tracks,
    required this.selectedTrack,
    required this.onApply,
  });

  final String streamUrl;
  final List<VideoTrack> tracks;
  final VideoTrack selectedTrack;
  final Future<void> Function() onApply;

  static Future<void> show(
    BuildContext context, {
    required String streamUrl,
    required List<VideoTrack> tracks,
    required VideoTrack selectedTrack,
    required Future<void> Function() onApply,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useRootNavigator: true,
      showDragHandle: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          bottom: 16 + MediaQuery.viewPaddingOf(context).bottom,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Playback quality',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              StreamQualityPanel(
                streamUrl: streamUrl,
                tracks: tracks,
                selectedTrack: selectedTrack,
                onApply: onApply,
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return StreamQualityPanel(
      streamUrl: streamUrl,
      tracks: tracks,
      selectedTrack: selectedTrack,
      onApply: onApply,
    );
  }
}
