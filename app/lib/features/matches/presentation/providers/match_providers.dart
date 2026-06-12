import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/features/matches/data/match_repository.dart';
import 'package:livetv_app/features/matches/domain/match.dart';

enum MatchFilter { all, live, scheduled }

extension MatchFilterX on MatchFilter {
  String? get apiValue => switch (this) {
        MatchFilter.all => null,
        MatchFilter.live => 'live',
        MatchFilter.scheduled => 'scheduled',
      };

  String get label => switch (this) {
        MatchFilter.all => 'All',
        MatchFilter.live => 'Live',
        MatchFilter.scheduled => 'Upcoming',
      };
}

class MatchListState {
  const MatchListState({
    this.items = const [],
    this.isLoading = false,
    this.isLoadingMore = false,
    this.hasMore = true,
    this.page = 1,
    this.error,
    this.filter = MatchFilter.live,
  });

  final List<MatchSummary> items;
  final bool isLoading;
  final bool isLoadingMore;
  final bool hasMore;
  final int page;
  final String? error;
  final MatchFilter filter;

  MatchListState copyWith({
    List<MatchSummary>? items,
    bool? isLoading,
    bool? isLoadingMore,
    bool? hasMore,
    int? page,
    String? error,
    MatchFilter? filter,
    bool clearError = false,
  }) {
    return MatchListState(
      items: items ?? this.items,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMore: hasMore ?? this.hasMore,
      page: page ?? this.page,
      error: clearError ? null : (error ?? this.error),
      filter: filter ?? this.filter,
    );
  }
}

class MatchListNotifier extends Notifier<MatchListState> {
  @override
  MatchListState build() {
    Future.microtask(() => refresh(force: false));
    return const MatchListState(isLoading: true);
  }

  Future<void> setFilter(MatchFilter filter) async {
    if (state.filter == filter) return;
    state = state.copyWith(filter: filter, clearError: true);
    await refresh(force: false);
  }

  Future<void> refresh({bool force = false}) async {
    if (force || state.items.isEmpty) {
      state = state.copyWith(isLoading: true, clearError: true);
    }
    try {
      final repo = ref.read(matchRepositoryProvider);
      final page = await repo.fetchMatches(
        status: state.filter.apiValue,
        forceRefresh: force,
      );
      state = MatchListState(
        items: page.results,
        hasMore: page.nextPage != null,
        page: 1,
        filter: state.filter,
      );
    } catch (error) {
      state = state.copyWith(
        isLoading: false,
        error: error.toString(),
      );
    }
  }

  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;
    state = state.copyWith(isLoadingMore: true, clearError: true);
    try {
      final repo = ref.read(matchRepositoryProvider);
      final nextPage = state.page + 1;
      final page = await repo.fetchMatches(
        page: nextPage,
        status: state.filter.apiValue,
      );
      state = state.copyWith(
        items: [...state.items, ...page.results],
        page: nextPage,
        hasMore: page.nextPage != null,
        isLoadingMore: false,
      );
    } catch (error) {
      state = state.copyWith(
        isLoadingMore: false,
        error: error.toString(),
      );
    }
  }
}

final matchListProvider =
    NotifierProvider<MatchListNotifier, MatchListState>(MatchListNotifier.new);

final matchDetailProvider =
    FutureProvider.family<MatchDetail, String>((ref, matchId) async {
  return ref.read(matchRepositoryProvider).fetchMatchDetail(matchId);
});

Future<void> refreshMatchDetail(WidgetRef ref, String matchId) async {
  await ref
      .read(matchRepositoryProvider)
      .fetchMatchDetail(matchId, forceRefresh: true);
  ref.invalidate(matchDetailProvider(matchId));
}
