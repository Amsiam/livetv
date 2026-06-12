import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/features/matches/domain/channel.dart';

void main() {
  group('Channel.fromJson', () {
    test('parses sources array', () {
      final channel = Channel.fromJson({
        'id': 'a',
        'name': 'HD Stream',
        'language': 'en',
        'logo_url': '',
        'stream_url': 'https://example.com/a.m3u8',
        'priority': 2,
        'is_active': true,
        'sources': [
          {
            'id': 'a',
            'stream_url': 'https://example.com/a.m3u8',
            'label': 'Source 1',
            'host': 'example.com',
          },
          {
            'id': 'b',
            'stream_url': 'https://example.com/b.m3u8',
            'label': 'Source 2',
            'host': 'example.com',
          },
        ],
      });

      expect(channel.sourceCount, 2);
      expect(channel.sourceAt(1).label, 'Source 2');
    });

    test('falls back to single implicit source', () {
      final channel = Channel.fromJson({
        'id': 'a',
        'name': 'Backup',
        'language': 'bn',
        'logo_url': '',
        'stream_url': 'https://example.com/backup.m3u8',
        'priority': 0,
        'is_active': true,
      });

      expect(channel.sourceCount, 1);
      expect(channel.sourceAt(0).streamUrl, 'https://example.com/backup.m3u8');
    });
  });
}
