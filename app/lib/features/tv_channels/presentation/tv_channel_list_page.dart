import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:livetv_app/features/tv_channels/presentation/providers/tv_channel_providers.dart';

class TvChannelListPage extends ConsumerStatefulWidget {
  const TvChannelListPage({
    super.key,
    this.region,
    this.searchQuery,
  });

  final String? region;
  final String? searchQuery;

  @override
  ConsumerState<TvChannelListPage> createState() => _TvChannelListPageState();
}

class _TvChannelListPageState extends ConsumerState<TvChannelListPage> {
  late final TvChannelListArgs _args;
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _args = TvChannelListArgs(
      region: widget.region,
      search: widget.searchQuery,
    );
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - 200) {
      ref.read(tvChannelListProvider(_args).notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(tvChannelListProvider(_args));
    final title = widget.searchQuery?.isNotEmpty == true
        ? widget.region != null
            ? '${widget.region}: ${widget.searchQuery}'
            : 'Search: ${widget.searchQuery}'
        : widget.region ?? 'TV Channels';

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: [
          if (widget.searchQuery == null)
            IconButton(
              icon: const Icon(Icons.search),
              tooltip: widget.region != null
                  ? 'Search in ${widget.region}'
                  : 'Search channels',
              onPressed: () {
                if (widget.region != null) {
                  context.push(
                    '/tv/region/${Uri.encodeComponent(widget.region!)}/search',
                  );
                  return;
                }
                context.push('/tv/search');
              },
            ),
        ],
      ),
      body: _buildBody(state),
    );
  }

  Widget _buildBody(TvChannelListState state) {
    if (state.isLoading && state.items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(state.error!),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () =>
                  ref.read(tvChannelListProvider(_args).notifier).refresh(force: true),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (state.items.isEmpty) {
      return const Center(child: Text('No channels found'));
    }

    return RefreshIndicator(
      onRefresh: () =>
          ref.read(tvChannelListProvider(_args).notifier).refresh(force: true),
      child: ListView.separated(
        controller: _scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        itemCount: state.items.length + (state.isLoadingMore ? 1 : 0),
        separatorBuilder: (_, _) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          if (index >= state.items.length) {
            return const Center(child: CircularProgressIndicator());
          }
          final channel = state.items[index];
          return Card(
            child: ListTile(
              leading: channel.logoUrl.isNotEmpty
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: CachedNetworkImage(
                        imageUrl: channel.logoUrl,
                        width: 40,
                        height: 40,
                        fit: BoxFit.cover,
                        errorWidget: (_, _, _) => const Icon(Icons.tv),
                      ),
                    )
                  : const Icon(Icons.tv),
              title: Text(channel.name),
              subtitle: Text(
                [
                  channel.category,
                  channel.region,
                  if (channel.sourceCount > 1)
                    '${channel.sourceCount} sources',
                ].where((part) => part.isNotEmpty).join(' · '),
              ),
              trailing: const Icon(Icons.play_circle_outline),
              onTap: () => context.push('/tv/channel/${channel.id}'),
            ),
          );
        },
      ),
    );
  }
}

class TvSearchPage extends StatefulWidget {
  const TvSearchPage({super.key, this.region});

  final String? region;

  @override
  State<TvSearchPage> createState() => _TvSearchPageState();
}

class _TvSearchPageState extends State<TvSearchPage> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final query = _controller.text.trim();
    if (query.isEmpty) return;
    final encodedQuery = Uri.encodeComponent(query);
    if (widget.region != null) {
      context.push(
        '/tv/region/${Uri.encodeComponent(widget.region!)}/search/$encodedQuery',
      );
      return;
    }
    context.push('/tv/search/$encodedQuery');
  }

  @override
  Widget build(BuildContext context) {
    final region = widget.region;
    final title = region != null ? 'Search in $region' : 'Search channels';
    final hint = region != null ? 'Channel name in $region' : 'Channel name';

    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _controller,
              autofocus: true,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _submit(),
              decoration: InputDecoration(
                hintText: hint,
                suffixIcon: IconButton(
                  icon: const Icon(Icons.search),
                  onPressed: _submit,
                ),
                border: const OutlineInputBorder(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
