import 'package:livetv_app/features/matches/domain/channel.dart';

enum MatchStatus { scheduled, live, ended }

MatchStatus matchStatusFromString(String value) {
  return MatchStatus.values.firstWhere(
    (status) => status.name == value,
    orElse: () => MatchStatus.scheduled,
  );
}

class MatchSummary {
  const MatchSummary({
    required this.id,
    required this.displayTitle,
    required this.sport,
    required this.homeTeam,
    required this.awayTeam,
    required this.startsAt,
    required this.endsAt,
    required this.status,
    required this.posterUrl,
    required this.sortOrder,
  });

  final String id;
  final String displayTitle;
  final String sport;
  final String homeTeam;
  final String awayTeam;
  final DateTime startsAt;
  final DateTime endsAt;
  final MatchStatus status;
  final String posterUrl;
  final int sortOrder;

  factory MatchSummary.fromJson(Map<String, dynamic> json) {
    return MatchSummary(
      id: json['id'] as String,
      displayTitle: json['display_title'] as String,
      sport: json['sport'] as String? ?? '',
      homeTeam: json['home_team'] as String? ?? '',
      awayTeam: json['away_team'] as String? ?? '',
      startsAt: DateTime.parse(json['starts_at'] as String),
      endsAt: DateTime.parse(json['ends_at'] as String),
      status: matchStatusFromString(json['status'] as String? ?? 'scheduled'),
      posterUrl: json['poster_url'] as String? ?? '',
      sortOrder: json['sort_order'] as int? ?? 0,
    );
  }
}

class MatchDetail extends MatchSummary {
  const MatchDetail({
    required super.id,
    required super.displayTitle,
    required super.sport,
    required super.homeTeam,
    required super.awayTeam,
    required super.startsAt,
    required super.endsAt,
    required super.status,
    required super.posterUrl,
    required super.sortOrder,
    required this.channels,
  });

  final List<Channel> channels;

  factory MatchDetail.fromJson(Map<String, dynamic> json) {
    final channels = (json['channels'] as List<dynamic>? ?? [])
        .map((item) => Channel.fromJson(item as Map<String, dynamic>))
        .toList()
      ..sort((a, b) => b.priority.compareTo(a.priority));

    return MatchDetail(
      id: json['id'] as String,
      displayTitle: json['display_title'] as String,
      sport: json['sport'] as String? ?? '',
      homeTeam: json['home_team'] as String? ?? '',
      awayTeam: json['away_team'] as String? ?? '',
      startsAt: DateTime.parse(json['starts_at'] as String),
      endsAt: DateTime.parse(json['ends_at'] as String),
      status: matchStatusFromString(json['status'] as String? ?? 'scheduled'),
      posterUrl: json['poster_url'] as String? ?? '',
      sortOrder: json['sort_order'] as int? ?? 0,
      channels: channels,
    );
  }
}

class PaginatedMatches {
  const PaginatedMatches({
    required this.results,
    required this.count,
    required this.nextPage,
  });

  final List<MatchSummary> results;
  final int count;
  final int? nextPage;

  factory PaginatedMatches.fromJson(Map<String, dynamic> json) {
    final results = (json['results'] as List<dynamic>? ?? [])
        .map((item) => MatchSummary.fromJson(item as Map<String, dynamic>))
        .toList();

    int? nextPage;
    final next = json['next'];
    if (next is String && next.isNotEmpty) {
      final uri = Uri.parse(next);
      nextPage = int.tryParse(uri.queryParameters['page'] ?? '');
    }

    return PaginatedMatches(
      results: results,
      count: json['count'] as int? ?? results.length,
      nextPage: nextPage,
    );
  }
}
