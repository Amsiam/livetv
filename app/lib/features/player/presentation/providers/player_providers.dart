import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/features/matches/domain/channel.dart';

class ActiveChannelNotifier extends Notifier<Channel?> {
  @override
  Channel? build() => null;

  void select(Channel? channel) => state = channel;
}

final activeChannelProvider =
    NotifierProvider<ActiveChannelNotifier, Channel?>(ActiveChannelNotifier.new);
