import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/widgets/ad_banner.dart';
import 'package:livetv_app/core/widgets/channel_grid.dart';
import 'package:livetv_app/features/player/presentation/providers/pip_mode_provider.dart';
import 'package:livetv_app/features/player/presentation/utils/player_orientation.dart';
import 'package:livetv_app/features/player/presentation/widgets/player_content_layout.dart';
import 'package:livetv_app/features/player/presentation/widgets/stream_player_view.dart';
import 'package:livetv_app/features/player/presentation/widgets/stream_quality_app_bar_button.dart';
import 'package:livetv_app/features/tv_channels/data/tv_channel_repository.dart';
import 'package:livetv_app/features/tv_channels/domain/tv_channel.dart';
import 'package:livetv_app/features/tv_channels/presentation/providers/tv_channel_providers.dart';
import 'package:livetv_app/core/widgets/stream_source_bar.dart';

class TvPlayerPage extends ConsumerStatefulWidget {
  const TvPlayerPage({super.key, required this.channelId});

  final String channelId;

  @override
  ConsumerState<TvPlayerPage> createState() => _TvPlayerPageState();
}

class _TvPlayerPageState extends ConsumerState<TvPlayerPage> {
  final _scrollController = ScrollController();
  TvChannel? _selectedChannel;
  TvChannelListArgs? _relatedListArgs;
  String? _relatedListKey;
  int _activeSourceIndex = 0;
  final Set<String> _triedSourceIds = {};
  bool _userPickedSource = false;
  String? _syncedChannelId;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    applyPlayerPageOrientations();
    _recordView(widget.channelId);
  }

  @override
  void didUpdateWidget(covariant TvPlayerPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.channelId != widget.channelId) {
      _selectedChannel = null;
      _relatedListArgs = null;
      _relatedListKey = null;
      _activeSourceIndex = 0;
      _triedSourceIds.clear();
      _userPickedSource = false;
      _syncedChannelId = null;
      _recordView(widget.channelId);
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    resetPlayerOrientations();
    super.dispose();
  }

  void _onScroll() {
    final args = _relatedListArgs;
    if (args == null || !_scrollController.hasClients) return;
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - 200) {
      ref.read(tvChannelListProvider(args).notifier).loadMore();
    }
  }

  void _ensureRelatedListArgs(TvChannel channel) {
    final category = channel.category;
    if (category.isEmpty) {
      _relatedListArgs = null;
      _relatedListKey = null;
      return;
    }

    if (_relatedListKey == category) return;

    _relatedListKey = category;
    _relatedListArgs = TvChannelListArgs(category: category);
  }

  int _sourceIndexFor(TvChannel channel, String sourceId) {
    final index = channel.effectiveSources.indexWhere((s) => s.id == sourceId);
    return index >= 0 ? index : 0;
  }

  void _syncOpenedChannel(TvChannel opened, List<TvChannel> relatedChannels) {
    if (_selectedChannel != null &&
        !_channelMatchesSelection(opened, _selectedChannel!)) {
      return;
    }

    final matches = relatedChannels.where((c) => c.id == opened.id);
    final next = matches.isNotEmpty ? matches.first : opened;
    if (_syncedChannelId == next.id && _selectedChannel != null) {
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      setState(() {
        _selectedChannel = next;
        if (!_userPickedSource) {
          _activeSourceIndex = _sourceIndexFor(next, widget.channelId);
        }
        _syncedChannelId = next.id;
        _triedSourceIds.clear();
      });
    });
  }

  bool _channelMatchesSelection(TvChannel a, TvChannel b) {
    if (a.id == b.id) return true;
    return a.name.toLowerCase() == b.name.toLowerCase();
  }

  void _selectChannel(TvChannel channel) {
    if (_selectedChannel?.id == channel.id) return;
    _recordView(channel.id);
    setState(() {
      _selectedChannel = channel;
      _activeSourceIndex = 0;
      _triedSourceIds.clear();
      _userPickedSource = false;
      _syncedChannelId = channel.id;
    });
  }

  void _recordView(String channelId) {
    unawaited(
      ref.read(tvChannelRepositoryProvider).recordChannelView(channelId),
    );
  }

  void _selectSource(int index) {
    if (_activeSourceIndex == index) return;
    setState(() {
      _activeSourceIndex = index;
      _triedSourceIds.clear();
      _userPickedSource = true;
    });
  }

  Future<void> _reportFailure(String sourceId) async {
    try {
      await ref.read(tvChannelRepositoryProvider).reportChannelFailure(sourceId);
    } catch (_) {}
  }

  Future<bool> _onPlaybackFailed(String message) async {
    final channel = _selectedChannel;
    if (channel == null) return false;

    final sources = channel.effectiveSources;
    final current = channel.sourceAt(_activeSourceIndex);
    if (!_triedSourceIds.contains(current.id)) {
      _triedSourceIds.add(current.id);
      unawaited(_reportFailure(current.id));
    }

    for (var offset = 1; offset < sources.length; offset++) {
      final i = (_activeSourceIndex + offset) % sources.length;
      if (_triedSourceIds.contains(sources[i].id)) continue;
      if (!mounted) return true;
      setState(() {
        _activeSourceIndex = i;
        _userPickedSource = true;
      });
      return true;
    }

    if (mounted) {
      setState(() {});
    }
    return false;
  }

  String _channelSubtitle(TvChannel channel) {
    return [
      channel.category,
      if (channel.sourceCount > 1) '${channel.sourceCount} sources',
    ].where((part) => part.isNotEmpty).join(' · ');
  }

  List<ChannelGridItem> _toGridItems(List<TvChannel> channels) {
    return channels
        .map(
          (channel) => ChannelGridItem(
            id: channel.id,
            name: channel.name,
            logoUrl: channel.logoUrl,
            subtitle: _channelSubtitle(channel),
          ),
        )
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final channelAsync = ref.watch(tvChannelDetailProvider(widget.channelId));
    final pipMode = ref.watch(pipModeProvider);
    final appBarTitle =
        _selectedChannel?.name ??
        channelAsync.valueOrNull?.name ??
        'TV Channel';

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: pipMode
          ? null
          : AppBar(
              title: Text(appBarTitle),
              actions: const [StreamQualityAppBarButton()],
            ),
      body: channelAsync.when(
        loading: () => const Column(
          children: [
            AspectRatio(
              aspectRatio: 16 / 9,
              child: ColoredBox(
                color: Colors.black,
                child: Center(child: CircularProgressIndicator()),
              ),
            ),
            Expanded(child: Center(child: CircularProgressIndicator())),
            AdBanner(),
          ],
        ),
        error: (error, _) => Column(
          children: [
            const AspectRatio(
              aspectRatio: 16 / 9,
              child: ColoredBox(color: Colors.black),
            ),
            Expanded(
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(error.toString()),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: () =>
                          refreshTvChannelDetail(ref, widget.channelId),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            ),
            const AdBanner(),
          ],
        ),
        data: (channel) {
          _ensureRelatedListArgs(channel);
          final relatedState = _relatedListArgs != null
              ? ref.watch(tvChannelListProvider(_relatedListArgs!))
              : null;
          if (relatedState != null) {
            _syncOpenedChannel(channel, relatedState.items);
          } else if (_selectedChannel == null) {
            _selectedChannel = channel;
            _activeSourceIndex = _sourceIndexFor(channel, widget.channelId);
            _syncedChannelId = channel.id;
          }

          final selected = _selectedChannel ?? channel;
          final sources = selected.effectiveSources;
          final activeSource = selected.sourceAt(_activeSourceIndex);

          final player = StreamPlayerView(
            key: ValueKey('${selected.id}:${activeSource.id}'),
            streamUrl: activeSource.streamUrl,
            title: selected.name,
            onPlaybackFailed: _onPlaybackFailed,
          );

          return PlayerContentLayout(
            player: player,
            belowPlayer: Column(
              children: [
                StreamSourceBar(
                  sources: sources,
                  activeIndex: _activeSourceIndex,
                  onSelected: _selectSource,
                ),
                Expanded(
                  child: Container(
                    color: Theme.of(context).colorScheme.surface,
                    child: relatedState != null &&
                            relatedState.isLoading &&
                            relatedState.items.isEmpty
                        ? const Center(child: CircularProgressIndicator())
                        : ChannelGrid(
                            channels: _toGridItems(
                              relatedState?.items.isNotEmpty == true
                                  ? relatedState!.items
                                  : [channel],
                            ),
                            selectedId: selected.id,
                            scrollController: _scrollController,
                            isLoadingMore:
                                relatedState?.isLoadingMore ?? false,
                            onSelected: (item) {
                              final gridChannels =
                                  relatedState?.items.isNotEmpty == true
                                      ? relatedState!.items
                                      : [channel];
                              final picked = gridChannels
                                  .firstWhere((c) => c.id == item.id);
                              _selectChannel(picked);
                            },
                          ),
                  ),
                ),
                const AdBanner(),
              ],
            ),
          );
        },
      ),
    );
  }
}
