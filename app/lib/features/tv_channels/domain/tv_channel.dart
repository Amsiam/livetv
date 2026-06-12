import 'package:livetv_app/core/domain/stream_source.dart';

class TvChannel {
  const TvChannel({
    required this.id,
    required this.name,
    required this.region,
    required this.category,
    required this.logoUrl,
    required this.streamUrl,
    required this.updatedAt,
    this.sources = const [],
  });

  final String id;
  final String name;
  final String region;
  final String category;
  final String logoUrl;
  final String streamUrl;
  final DateTime? updatedAt;
  final List<StreamSource> sources;

  int get sourceCount => effectiveSources.length;

  List<StreamSource> get effectiveSources {
    if (sources.isNotEmpty) return sources;
    return [
      StreamSource(
        id: id,
        streamUrl: streamUrl,
        label: 'Source 1',
      ),
    ];
  }

  StreamSource sourceAt(int index) {
    final list = effectiveSources;
    return list[index.clamp(0, list.length - 1)];
  }

  factory TvChannel.fromJson(Map<String, dynamic> json) {
    final updated = json['updated_at'];
    final parsedSources = (json['sources'] as List<dynamic>? ?? [])
        .map((item) => StreamSource.fromJson(item as Map<String, dynamic>))
        .toList();

    return TvChannel(
      id: json['id'] as String,
      name: json['name'] as String? ?? '',
      region: json['region'] as String? ?? '',
      category: json['category'] as String? ?? '',
      logoUrl: json['logo_url'] as String? ?? '',
      streamUrl: json['stream_url'] as String? ?? '',
      updatedAt: updated == null ? null : DateTime.tryParse(updated as String),
      sources: parsedSources,
    );
  }
}

class TvRegion {
  const TvRegion({required this.region, required this.channelCount});

  final String region;
  final int channelCount;

  factory TvRegion.fromJson(Map<String, dynamic> json) {
    return TvRegion(
      region: json['region'] as String? ?? '',
      channelCount: json['channel_count'] as int? ?? 0,
    );
  }
}

class PaginatedTvChannels {
  const PaginatedTvChannels({
    required this.results,
    required this.count,
    required this.nextPage,
  });

  final List<TvChannel> results;
  final int count;
  final int? nextPage;

  factory PaginatedTvChannels.fromJson(Map<String, dynamic> json) {
    final results = (json['results'] as List<dynamic>? ?? [])
        .map((item) => TvChannel.fromJson(item as Map<String, dynamic>))
        .toList();

    int? nextPage;
    final next = json['next'];
    if (next is String && next.isNotEmpty) {
      final uri = Uri.parse(next);
      nextPage = int.tryParse(uri.queryParameters['page'] ?? '');
    }

    return PaginatedTvChannels(
      results: results,
      count: json['count'] as int? ?? results.length,
      nextPage: nextPage,
    );
  }
}
