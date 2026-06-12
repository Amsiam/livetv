import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/hls_playlist_client.dart';
import '../../domain/hls_playlist_parser.dart';
import '../../domain/stream_format.dart';

final hlsPlaylistClientProvider = Provider<HlsPlaylistClient>(
  (ref) => HlsPlaylistClient(),
);

final hlsPlaylistInfoProvider =
    FutureProvider.family<HlsPlaylistInfo, String>((ref, streamUrl) async {
  if (detectStreamFormat(streamUrl) != StreamFormat.hls) {
    return const HlsPlaylistInfo(variantHeights: [], isMediaPlaylist: false);
  }
  return ref.read(hlsPlaylistClientProvider).fetchInfo(streamUrl);
});
