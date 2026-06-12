enum StreamSourceKind { match, catalog }

StreamSourceKind streamSourceKindFromJson(String? value) {
  return value == 'catalog'
      ? StreamSourceKind.catalog
      : StreamSourceKind.match;
}

class StreamSource {
  const StreamSource({
    required this.id,
    required this.streamUrl,
    required this.label,
    this.host = '',
    this.kind = StreamSourceKind.match,
  });

  final String id;
  final String streamUrl;
  final String label;
  final String host;
  final StreamSourceKind kind;

  factory StreamSource.fromJson(Map<String, dynamic> json) {
    return StreamSource(
      id: json['id'] as String,
      streamUrl: json['stream_url'] as String? ?? '',
      label: json['label'] as String? ?? 'Source',
      host: json['host'] as String? ?? '',
      kind: streamSourceKindFromJson(json['kind'] as String?),
    );
  }
}
