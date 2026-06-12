import 'package:livetv_app/core/domain/stream_source.dart';

class Channel {
  const Channel({
    required this.id,
    required this.name,
    required this.language,
    required this.logoUrl,
    required this.streamUrl,
    required this.priority,
    required this.isActive,
    this.sources = const [],
  });

  final String id;
  final String name;
  final String language;
  final String logoUrl;
  final String streamUrl;
  final int priority;
  final bool isActive;
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

  factory Channel.fromJson(Map<String, dynamic> json) {
    final parsedSources = (json['sources'] as List<dynamic>? ?? [])
        .map((item) => StreamSource.fromJson(item as Map<String, dynamic>))
        .toList();

    return Channel(
      id: json['id'] as String,
      name: json['name'] as String? ?? '',
      language: json['language'] as String? ?? '',
      logoUrl: json['logo_url'] as String? ?? '',
      streamUrl: json['stream_url'] as String? ?? '',
      priority: json['priority'] as int? ?? 0,
      isActive: json['is_active'] as bool? ?? true,
      sources: parsedSources,
    );
  }
}
