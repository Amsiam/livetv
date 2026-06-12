import 'package:dio/dio.dart';

import '../domain/hls_playlist_parser.dart';

class HlsPlaylistClient {
  HlsPlaylistClient({Dio? dio}) : _dio = dio ?? Dio();

  final Dio _dio;

  Future<HlsPlaylistInfo> fetchInfo(String url) async {
    final response = await _dio.get<String>(
      url,
      options: Options(
        responseType: ResponseType.plain,
        headers: const {
          'User-Agent':
              'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        },
      ),
    );
    final body = response.data ?? '';
    final info = parseHlsPlaylist(body);

    if (info.variantHeights.isNotEmpty || info.isMediaPlaylist) {
      return info;
    }

    // Master with relative variant URLs but no RESOLUTION tag — follow first variant.
    final variantUrl = _firstVariantUrl(body, url);
    if (variantUrl == null) return info;

    final variantResponse = await _dio.get<String>(
      variantUrl,
      options: Options(
        responseType: ResponseType.plain,
        headers: const {
          'User-Agent':
              'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
        },
      ),
    );
    return parseHlsPlaylist(variantResponse.data ?? '');
  }

  String? _firstVariantUrl(String body, String masterUrl) {
    final lines = body.split('\n').map((l) => l.trim()).toList();
    for (var i = 0; i < lines.length; i++) {
      if (!lines[i].startsWith('#EXT-X-STREAM-INF:')) continue;
      for (var j = i + 1; j < lines.length; j++) {
        final line = lines[j];
        if (line.isEmpty || line.startsWith('#')) continue;
        return Uri.parse(masterUrl).resolve(line).toString();
      }
    }
    return null;
  }
}
