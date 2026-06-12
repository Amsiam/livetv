import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/features/matches/domain/match.dart';

void main() {
  test('MatchSummary parses API JSON', () {
    final match = MatchSummary.fromJson({
      'id': '11111111-1111-1111-1111-111111111111',
      'display_title': 'Team A vs Team B',
      'sport': 'football',
      'home_team': 'Team A',
      'away_team': 'Team B',
      'starts_at': '2026-06-09T12:00:00Z',
      'ends_at': '2026-06-09T14:00:00Z',
      'status': 'live',
      'poster_url': 'https://example.com/poster.jpg',
      'sort_order': 1,
    });

    expect(match.displayTitle, 'Team A vs Team B');
    expect(match.status, MatchStatus.live);
  });
}
