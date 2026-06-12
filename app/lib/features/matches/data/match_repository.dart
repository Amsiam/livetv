import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/cache/session_cache.dart';
import 'package:livetv_app/core/network/api_client.dart';
import 'package:livetv_app/features/matches/domain/match.dart';

final sessionCacheProvider = Provider<SessionCache>((ref) => SessionCache());

final matchRepositoryProvider = Provider<MatchRepository>((ref) {
  return MatchRepository(
    ref.watch(dioProvider),
    ref.watch(sessionCacheProvider),
  );
});

class MatchRepository {
  MatchRepository(this._dio, this._cache);

  final Dio _dio;
  final SessionCache _cache;

  String _matchesKey({required int page, String? status}) =>
      'matches|${status ?? 'all'}|p$page';

  String _matchesPrefix(String? status) => 'matches|${status ?? 'all'}|';

  Future<PaginatedMatches> fetchMatches({
    int page = 1,
    String? status,
    bool forceRefresh = false,
  }) async {
    final key = _matchesKey(page: page, status: status);
    if (!forceRefresh) {
      final cached = _cache.get<PaginatedMatches>(key);
      if (cached != null) return cached;
    }

    final query = <String, dynamic>{'page': page};
    if (status != null && status.isNotEmpty) {
      query['status'] = status;
    }
    final json = await _dio.getJson('/matches/', query: query);
    final result = PaginatedMatches.fromJson(json);

    if (forceRefresh && page == 1) {
      final prefix = _matchesPrefix(status);
      _cache.removeWhere((k) => k.startsWith(prefix) && k != key);
    }

    _cache.set(key, result);
    return result;
  }

  Future<MatchDetail> fetchMatchDetail(
    String id, {
    bool forceRefresh = false,
  }) async {
    final key = 'match|$id';
    if (!forceRefresh) {
      final cached = _cache.get<MatchDetail>(key);
      if (cached != null) return cached;
    }

    final json = await _dio.getJson('/matches/$id/');
    final result = MatchDetail.fromJson(json);
    _cache.set(key, result);
    return result;
  }

  Future<void> reportChannelFailure(String channelId) async {
    await _dio.post('/channels/$channelId/report-failure/');
  }
}
