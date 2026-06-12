import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/features/player/domain/hls_playlist_parser.dart';

const _master720 = '''
#EXTM3U
#EXT-X-STREAM-INF:AVERAGE-BANDWIDTH=1460000,BANDWIDTH=1820000,RESOLUTION=1280x720,FRAME-RATE=25.000,CODECS="avc1.4d401f,mp4a.40.2",CLOSED-CAPTIONS=NONE
tracks-v1a1/mono.ts.m3u8
''';

const _masterMulti = '''
#EXTM3U
#EXT-X-STREAM-INF:RESOLUTION=1920x1080,BANDWIDTH=5000000
1080/playlist.m3u8
#EXT-X-STREAM-INF:RESOLUTION=1280x720,BANDWIDTH=1820000
720/playlist.m3u8
''';

const _mediaPlaylist = '''
#EXTM3U
#EXT-X-TARGETDURATION:9
#EXTINF:9.000,
segment.ts
''';

void main() {
  test('parses single 720p master variant', () {
    final info = parseHlsPlaylist(_master720);
    expect(info.variantHeights, [720]);
    expect(info.isMediaPlaylist, isFalse);
  });

  test('parses multiple master variants', () {
    final info = parseHlsPlaylist(_masterMulti);
    expect(info.variantHeights, [1080, 720]);
  });

  test('detects media playlist without variants', () {
    final info = parseHlsPlaylist(_mediaPlaylist);
    expect(info.variantHeights, isEmpty);
    expect(info.isMediaPlaylist, isTrue);
  });
}
