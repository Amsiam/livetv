import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/features/matches/data/match_repository.dart';
import 'package:livetv_app/features/tv_channels/data/tv_channel_repository.dart';

/// Prefetches main catalog data once per app session (in-memory cache).
final sessionBootstrapProvider = FutureProvider<void>((ref) async {
  final matches = ref.read(matchRepositoryProvider);
  final tv = ref.read(tvChannelRepositoryProvider);

  await Future.wait([
    matches.fetchMatches(),
    matches.fetchMatches(status: 'live'),
    matches.fetchMatches(status: 'scheduled'),
    tv.fetchChannels(grouped: true),
  ]);
});
