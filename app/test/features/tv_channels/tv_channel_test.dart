import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/features/tv_channels/domain/tv_channel.dart';

void main() {
  group('TvChannel.fromJson', () {
    test('parses sources array', () {
      final channel = TvChannel.fromJson({
        'id': 'a',
        'name': 'Sports HD',
        'region': 'Bangladesh',
        'category': 'Sports',
        'logo_url': '',
        'stream_url': 'https://cdn.example/a.m3u8',
        'sources': [
          {
            'id': 'a',
            'stream_url': 'https://cdn.example/a.m3u8',
            'label': 'Source 1',
            'host': 'cdn.example',
          },
          {
            'id': 'b',
            'stream_url': 'https://cdn.example/b.m3u8',
            'label': 'Source 2',
            'host': 'cdn.example',
          },
        ],
      });

      expect(channel.sourceCount, 2);
      expect(channel.sourceAt(1).label, 'Source 2');
    });

    test('falls back to single implicit source', () {
      final channel = TvChannel.fromJson({
        'id': 'a',
        'name': 'News',
        'region': 'India',
        'category': 'News',
        'logo_url': '',
        'stream_url': 'https://cdn.example/news.m3u8',
      });

      expect(channel.sourceCount, 1);
      expect(channel.sourceAt(0).streamUrl, 'https://cdn.example/news.m3u8');
    });
  });
}
