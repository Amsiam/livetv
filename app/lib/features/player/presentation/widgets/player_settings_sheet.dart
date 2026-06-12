import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit/media_kit.dart';

import 'player_brightness_panel.dart';
import 'stream_quality_panel.dart';
import 'video_display_mode_panel.dart';

class PlayerSettingsSheet extends ConsumerStatefulWidget {
  const PlayerSettingsSheet({
    super.key,
    required this.title,
    required this.streamUrl,
    required this.tracks,
    required this.selectedTrack,
    required this.onApply,
    this.initialTab = 0,
  });

  final String title;
  final String streamUrl;
  final List<VideoTrack> tracks;
  final VideoTrack selectedTrack;
  final Future<void> Function() onApply;
  final int initialTab;

  static Future<void> show(
    BuildContext context, {
    required String title,
    required String streamUrl,
    required List<VideoTrack> tracks,
    required VideoTrack selectedTrack,
    required Future<void> Function() onApply,
    int initialTab = 0,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useRootNavigator: true,
      showDragHandle: true,
      builder: (context) {
        final maxHeight = MediaQuery.sizeOf(context).height * 0.52;
        return ConstrainedBox(
          constraints: BoxConstraints(maxHeight: maxHeight),
          child: PlayerSettingsSheet(
            title: title,
            streamUrl: streamUrl,
            tracks: tracks,
            selectedTrack: selectedTrack,
            onApply: onApply,
            initialTab: initialTab,
          ),
        );
      },
    );
  }

  @override
  ConsumerState<PlayerSettingsSheet> createState() =>
      _PlayerSettingsSheetState();
}

class _PlayerSettingsSheetState extends ConsumerState<PlayerSettingsSheet>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: widget.initialTab.clamp(0, 1),
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              widget.title,
              style: Theme.of(context).textTheme.titleSmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
        TabBar(
          controller: _tabController,
          tabAlignment: TabAlignment.fill,
          labelPadding: EdgeInsets.zero,
          tabs: const [
            Tab(height: 40, text: 'Display'),
            Tab(height: 40, text: 'Quality'),
          ],
        ),
        Flexible(
          child: TabBarView(
            controller: _tabController,
            children: [
              SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    PlayerBrightnessPanel(),
                    SizedBox(height: 8),
                    VideoDisplayModePanel(),
                  ],
                ),
              ),
              SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
                child: StreamQualityPanel(
                  streamUrl: widget.streamUrl,
                  tracks: widget.tracks,
                  selectedTrack: widget.selectedTrack,
                  onApply: widget.onApply,
                  compact: true,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
