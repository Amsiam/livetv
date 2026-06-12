/// Parsed HLS playlist metadata used for quality UI.
class HlsPlaylistInfo {
  const HlsPlaylistInfo({
    required this.variantHeights,
    required this.isMediaPlaylist,
  });

  /// Video heights (e.g. 720) from `#EXT-X-STREAM-INF:RESOLUTION=…`.
  final List<int> variantHeights;

  /// True when the URL points at a segment playlist (`#EXTINF`), not a master.
  final bool isMediaPlaylist;

  bool get hasMultipleVariants => variantHeights.length > 1;

  bool get hasSingleVariant => variantHeights.length == 1;
}

final _streamInfResolution = RegExp(
  r'RESOLUTION=(\d+)x(\d+)',
  caseSensitive: false,
);

/// Parse raw M3U8 text. Does not fetch over the network.
HlsPlaylistInfo parseHlsPlaylist(String body) {
  final heights = <int>[];
  var sawStreamInf = false;
  var sawExtInf = false;

  for (final line in body.split('\n')) {
    final trimmed = line.trim();
    if (trimmed.startsWith('#EXT-X-STREAM-INF:')) {
      sawStreamInf = true;
      final match = _streamInfResolution.firstMatch(trimmed);
      if (match != null) {
        final height = int.tryParse(match.group(2)!);
        if (height != null && height > 0) {
          heights.add(height);
        }
      }
    } else if (trimmed.startsWith('#EXTINF:')) {
      sawExtInf = true;
    }
  }

  final uniqueHeights = heights.toSet().toList()..sort((a, b) => b.compareTo(a));

  return HlsPlaylistInfo(
    variantHeights: uniqueHeights,
    isMediaPlaylist: sawExtInf && !sawStreamInf,
  );
}
