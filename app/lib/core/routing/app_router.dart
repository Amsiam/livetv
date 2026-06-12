import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:livetv_app/features/matches/presentation/match_list_page.dart';
import 'package:livetv_app/features/player/presentation/player_page.dart';
import 'package:livetv_app/features/tv_channels/presentation/tv_channel_list_page.dart';
import 'package:livetv_app/features/tv_channels/presentation/tv_player_page.dart';
import 'package:livetv_app/shell/main_shell.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorMatchesKey = GlobalKey<NavigatorState>(debugLabel: 'matches');
final _shellNavigatorTvKey = GlobalKey<NavigatorState>(debugLabel: 'tv');

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return MainShell(navigationShell: navigationShell);
        },
        branches: [
          StatefulShellBranch(
            navigatorKey: _shellNavigatorMatchesKey,
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) => const MatchListPage(),
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _shellNavigatorTvKey,
            routes: [
              GoRoute(
                path: '/tv',
                builder: (context, state) => const TvChannelListPage(),
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/match/:id',
        builder: (context, state) => PlayerPage(
          matchId: state.pathParameters['id']!,
        ),
      ),
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/tv/region/:region',
        builder: (context, state) => TvChannelListPage(
          region: Uri.decodeComponent(state.pathParameters['region']!),
        ),
      ),
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/tv/region/:region/search',
        builder: (context, state) => TvSearchPage(
          region: Uri.decodeComponent(state.pathParameters['region']!),
        ),
      ),
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/tv/region/:region/search/:query',
        builder: (context, state) => TvChannelListPage(
          region: Uri.decodeComponent(state.pathParameters['region']!),
          searchQuery: Uri.decodeComponent(state.pathParameters['query']!),
        ),
      ),
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/tv/search',
        builder: (context, state) => const TvSearchPage(),
      ),
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/tv/search/:query',
        builder: (context, state) => TvChannelListPage(
          searchQuery: Uri.decodeComponent(state.pathParameters['query']!),
        ),
      ),
      GoRoute(
        parentNavigatorKey: _rootNavigatorKey,
        path: '/tv/channel/:id',
        builder: (context, state) => TvPlayerPage(
          channelId: state.pathParameters['id']!,
        ),
      ),
    ],
  );
});
