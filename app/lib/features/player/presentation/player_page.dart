import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/widgets/ad_banner.dart';
import 'package:livetv_app/core/widgets/channel_grid.dart';
import 'package:livetv_app/core/widgets/stream_source_bar.dart';
import 'package:livetv_app/core/domain/stream_source.dart';
import 'package:livetv_app/features/matches/data/match_repository.dart';
import 'package:livetv_app/features/tv_channels/data/tv_channel_repository.dart';
import 'package:livetv_app/features/matches/domain/channel.dart';
import 'package:livetv_app/features/matches/presentation/providers/match_providers.dart';
import 'package:livetv_app/features/player/presentation/providers/pip_mode_provider.dart';
import 'package:livetv_app/features/player/presentation/providers/player_providers.dart';
import 'package:livetv_app/features/player/presentation/utils/player_orientation.dart';
import 'package:livetv_app/features/player/presentation/widgets/player_content_layout.dart';
import 'package:livetv_app/features/player/presentation/widgets/stream_player_view.dart';
import 'package:livetv_app/features/player/presentation/widgets/stream_quality_app_bar_button.dart';

class PlayerPage extends ConsumerStatefulWidget {
  const PlayerPage({super.key, required this.matchId});

  final String matchId;

  @override
  ConsumerState<PlayerPage> createState() => _PlayerPageState();
}

class _PlayerPageState extends ConsumerState<PlayerPage> {
  Channel? _currentChannel;
  int _activeSourceIndex = 0;
  final Set<String> _triedSourceIds = {};

  @override
  void initState() {
    super.initState();
    applyPlayerPageOrientations();
  }

  @override
  void dispose() {
    resetPlayerOrientations();
    super.dispose();
  }

  bool _channelMatchesSelection(Channel a, Channel b) {
    if (a.id == b.id) return true;
    return a.name.toLowerCase() == b.name.toLowerCase();
  }

  void _ensureDefaultChannel(List<Channel> channels) {
    if (channels.isEmpty) {
      if (_currentChannel != null) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          setState(() {
            _currentChannel = null;
            _activeSourceIndex = 0;
            _triedSourceIds.clear();
          });
        });
      }
      return;
    }

    if (_currentChannel != null) {
      Channel? updated;
      for (final channel in channels) {
        if (_channelMatchesSelection(channel, _currentChannel!)) {
          updated = channel;
          break;
        }
      }
      if (updated != null) {
        final current = _currentChannel!;
        final needsSync = updated.id != current.id ||
            updated.sourceCount != current.sourceCount ||
            updated.streamUrl != current.streamUrl;
        if (needsSync) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            setState(() => _currentChannel = updated);
          });
        }
        return;
      }
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final channel = channels.first;
      setState(() {
        _currentChannel = channel;
        _activeSourceIndex = 0;
        _triedSourceIds.clear();
      });
      ref.read(activeChannelProvider.notifier).select(channel);
    });
  }

  Future<void> _reportFailure(StreamSource source) async {
    try {
      if (source.kind == StreamSourceKind.catalog) {
        await ref.read(tvChannelRepositoryProvider).reportChannelFailure(source.id);
        return;
      }
      await ref.read(matchRepositoryProvider).reportChannelFailure(source.id);
    } catch (_) {}
  }

  Future<bool> _onPlaybackFailed(String message) async {
    final channel = _currentChannel;
    if (channel == null) return false;

    final sources = channel.effectiveSources;
    final current = channel.sourceAt(_activeSourceIndex);
    if (!_triedSourceIds.contains(current.id)) {
      _triedSourceIds.add(current.id);
      unawaited(_reportFailure(current));
    }

    for (var offset = 1; offset < sources.length; offset++) {
      final i = (_activeSourceIndex + offset) % sources.length;
      if (_triedSourceIds.contains(sources[i].id)) continue;
      if (!mounted) return true;
      setState(() => _activeSourceIndex = i);
      return true;
    }

    if (mounted) {
      setState(() {});
    }
    return false;
  }

  void _switchChannel(Channel channel) {
    if (_currentChannel != null &&
        _channelMatchesSelection(_currentChannel!, channel)) {
      return;
    }
    setState(() {
      _currentChannel = channel;
      _activeSourceIndex = 0;
      _triedSourceIds.clear();
    });
    ref.read(activeChannelProvider.notifier).select(channel);
  }

  void _selectSource(int index) {
    if (_activeSourceIndex == index) return;
    setState(() {
      _activeSourceIndex = index;
      _triedSourceIds.clear();
    });
  }

  String _channelSubtitle(Channel channel) {
    return [
      channel.language,
      if (channel.sourceCount > 1) '${channel.sourceCount} sources',
    ].where((part) => part.isNotEmpty).join(' · ');
  }

  List<ChannelGridItem> _toGridItems(List<Channel> channels) {
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
    final matchAsync = ref.watch(matchDetailProvider(widget.matchId));
    final pipMode = ref.watch(pipModeProvider);

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: pipMode
          ? null
          : AppBar(
              title: matchAsync.maybeWhen(
                data: (match) => Text(match.displayTitle),
                orElse: () => const Text('Loading…'),
              ),
              actions: const [StreamQualityAppBarButton()],
            ),
      body: matchAsync.when(
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
                          refreshMatchDetail(ref, widget.matchId),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            ),
            const AdBanner(),
          ],
        ),
        data: (match) {
          _ensureDefaultChannel(match.channels);
          final channel = _currentChannel;

          if (channel == null) {
            return const Column(
              children: [
                AspectRatio(
                  aspectRatio: 16 / 9,
                  child: ColoredBox(color: Colors.black),
                ),
                Expanded(
                  child: Center(child: Text('No active channels for this match')),
                ),
                AdBanner(),
              ],
            );
          }

          final sources = channel.effectiveSources;
          final activeSource = channel.sourceAt(_activeSourceIndex);

          final player = StreamPlayerView(
            key: ValueKey('${channel.id}:${activeSource.id}'),
            streamUrl: activeSource.streamUrl,
            title: channel.name,
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
                    child: ChannelGrid(
                      channels: _toGridItems(match.channels),
                      selectedId: channel.id,
                      onSelected: (item) {
                        final selected = match.channels
                            .firstWhere((c) => c.id == item.id);
                        _switchChannel(selected);
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
