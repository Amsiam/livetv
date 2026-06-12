import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/features/tv_channels/data/tv_channel_repository.dart';
import 'package:livetv_app/features/tv_channels/domain/tv_channel.dart';

class TvChannelListArgs {
  const TvChannelListArgs({
    this.region,
    this.category,
    this.search,
    this.grouped = true,
  });

  final String? region;
  final String? category;
  final String? search;
  final bool grouped;

  @override
  bool operator ==(Object other) {
    return other is TvChannelListArgs &&
        other.region == region &&
        other.category == category &&
        other.search == search &&
        other.grouped == grouped;
  }

  @override
  int get hashCode => Object.hash(region, category, search, grouped);
}

class TvChannelListState {
  const TvChannelListState({
    this.items = const [],
    this.isLoading = false,
    this.isLoadingMore = false,
    this.hasMore = true,
    this.page = 1,
    this.error,
  });

  final List<TvChannel> items;
  final bool isLoading;
  final bool isLoadingMore;
  final bool hasMore;
  final int page;
  final String? error;

  TvChannelListState copyWith({
    List<TvChannel>? items,
    bool? isLoading,
    bool? isLoadingMore,
    bool? hasMore,
    int? page,
    String? error,
    bool clearError = false,
  }) {
    return TvChannelListState(
      items: items ?? this.items,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMore: hasMore ?? this.hasMore,
      page: page ?? this.page,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class TvChannelListNotifier extends FamilyNotifier<TvChannelListState, TvChannelListArgs> {
  @override
  TvChannelListState build(TvChannelListArgs arg) {
    Future.microtask(() => refresh(force: false));
    return const TvChannelListState(isLoading: true);
  }

  Future<void> refresh({bool force = true}) async {
    if (force || state.items.isEmpty) {
      state = state.copyWith(isLoading: true, clearError: true);
    }
    try {
      final repo = ref.read(tvChannelRepositoryProvider);
      final page = await repo.fetchChannels(
        region: arg.region,
        category: arg.category,
        search: arg.search,
        grouped: arg.grouped,
        forceRefresh: force,
      );
      state = TvChannelListState(
        items: page.results,
        hasMore: page.nextPage != null,
        page: 1,
      );
    } catch (error) {
      state = state.copyWith(isLoading: false, error: error.toString());
    }
  }

  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;
    state = state.copyWith(isLoadingMore: true, clearError: true);
    try {
      final repo = ref.read(tvChannelRepositoryProvider);
      final nextPage = state.page + 1;
      final page = await repo.fetchChannels(
        page: nextPage,
        region: arg.region,
        category: arg.category,
        search: arg.search,
        grouped: arg.grouped,
      );
      state = state.copyWith(
        items: [...state.items, ...page.results],
        page: nextPage,
        hasMore: page.nextPage != null,
        isLoadingMore: false,
      );
    } catch (error) {
      state = state.copyWith(isLoadingMore: false, error: error.toString());
    }
  }
}

final tvChannelListProvider = NotifierProvider.family<TvChannelListNotifier,
    TvChannelListState, TvChannelListArgs>(TvChannelListNotifier.new);

final tvChannelDetailProvider =
    FutureProvider.family<TvChannel, String>((ref, channelId) async {
  return ref.read(tvChannelRepositoryProvider).fetchChannel(channelId);
});

Future<void> refreshTvChannelDetail(WidgetRef ref, String channelId) async {
  await ref
      .read(tvChannelRepositoryProvider)
      .fetchChannel(channelId, forceRefresh: true);
  ref.invalidate(tvChannelDetailProvider(channelId));
}
