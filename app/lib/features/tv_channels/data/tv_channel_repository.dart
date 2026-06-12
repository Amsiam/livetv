import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/cache/session_cache.dart';
import 'package:livetv_app/core/network/api_client.dart';
import 'package:livetv_app/features/matches/data/match_repository.dart';
import 'package:livetv_app/features/tv_channels/domain/tv_channel.dart';

final tvChannelRepositoryProvider = Provider<TvChannelRepository>((ref) {
  return TvChannelRepository(
    ref.watch(dioProvider),
    ref.watch(sessionCacheProvider),
  );
});

class TvChannelRepository {
  TvChannelRepository(this._dio, this._cache);

  final Dio _dio;
  final SessionCache _cache;

  String _channelsKey({
    required int page,
    String? region,
    String? category,
    String? search,
    bool grouped = false,
  }) =>
      'tv-ch|$region|$category|$search|g$grouped|p$page';

  String _channelsPrefix({
    String? region,
    String? category,
    String? search,
    bool grouped = false,
  }) =>
      'tv-ch|$region|$category|$search|g$grouped|';

  Future<List<TvRegion>> fetchRegions({bool forceRefresh = false}) async {
    const key = 'tv-regions';
    if (!forceRefresh) {
      final cached = _cache.get<List<TvRegion>>(key);
      if (cached != null) return cached;
    }

    final list = await _dio.getJsonList('/tv-channels/regions/');
    final result = list
        .map((item) => TvRegion.fromJson(item as Map<String, dynamic>))
        .toList();
    _cache.set(key, result);
    return result;
  }

  Future<PaginatedTvChannels> fetchChannels({
    int page = 1,
    String? region,
    String? category,
    String? search,
    bool grouped = false,
    bool forceRefresh = false,
  }) async {
    final key = _channelsKey(
      page: page,
      region: region,
      category: category,
      search: search,
      grouped: grouped,
    );
    if (!forceRefresh) {
      final cached = _cache.get<PaginatedTvChannels>(key);
      if (cached != null) return cached;
    }

    final query = <String, dynamic>{'page': page};
    if (region != null && region.isNotEmpty) query['region'] = region;
    if (category != null && category.isNotEmpty) query['category'] = category;
    if (search != null && search.isNotEmpty) query['search'] = search;
    if (grouped) query['grouped'] = 'true';

    final json = await _dio.getJson('/tv-channels/', query: query);
    final result = PaginatedTvChannels.fromJson(json);

    if (forceRefresh && page == 1) {
      final prefix = _channelsPrefix(
        region: region,
        category: category,
        search: search,
        grouped: grouped,
      );
      _cache.removeWhere((k) => k.startsWith(prefix) && k != key);
    }

    _cache.set(key, result);
    return result;
  }

  Future<TvChannel> fetchChannel(
    String id, {
    bool forceRefresh = false,
  }) async {
    final key = 'tv-channel|$id';
    if (!forceRefresh) {
      final cached = _cache.get<TvChannel>(key);
      if (cached != null) return cached;
    }

    final json = await _dio.getJson('/tv-channels/$id/');
    final result = TvChannel.fromJson(json);
    _cache.set(key, result);
    return result;
  }

  Future<void> reportChannelFailure(String channelId) async {
    await _dio.post('/tv-channels/$channelId/report-failure/');
  }

  Future<void> recordChannelView(String channelId) async {
    try {
      await _dio.post('/tv-channels/$channelId/record-view/');
    } catch (_) {}
  }
}
