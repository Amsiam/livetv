import 'dart:async';

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/player_brightness_mode.dart';
import '../providers/player_brightness_mode_provider.dart';

/// Left-half vertical drag in fullscreen when brightness is in [PlayerBrightnessMode.auto].
class LiveTvBrightnessGesture extends ConsumerStatefulWidget {
  const LiveTvBrightnessGesture({super.key});

  @override
  ConsumerState<LiveTvBrightnessGesture> createState() =>
      _LiveTvBrightnessGestureState();
}

class _LiveTvBrightnessGestureState
    extends ConsumerState<LiveTvBrightnessGesture> {
  static const _sensitivity = 100.0;

  double _brightness = 0;
  bool _dragging = false;
  bool _showIndicator = false;
  Offset? _pointerStart;
  Timer? _indicatorTimer;
  StreamSubscription<double>? _subscription;

  @override
  void initState() {
    super.initState();
    unawaited(_syncBrightness());
    _listenToBrightness();
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _indicatorTimer?.cancel();
    super.dispose();
  }

  Future<void> _syncBrightness() async {
    final service = ref.read(screenBrightnessServiceProvider);
    final value = await service.currentBrightness(autoMode: true);
    if (mounted) {
      setState(() => _brightness = value);
    }
  }

  void _listenToBrightness() {
    final service = ref.read(screenBrightnessServiceProvider);
    _subscription?.cancel();
    _subscription = service
        .brightnessChanges(autoMode: true)
        .listen((value) {
      if (mounted && !_dragging) {
        setState(() => _brightness = value);
      }
    });
  }

  void _flashIndicator() {
    setState(() => _showIndicator = true);
    _indicatorTimer?.cancel();
    _indicatorTimer = Timer(const Duration(milliseconds: 900), () {
      if (mounted) {
        setState(() => _showIndicator = false);
      }
    });
  }

  Future<void> _setBrightness(double value) async {
    final clamped = value.clamp(0.0, 1.0);
    setState(() => _brightness = clamped);
    _flashIndicator();
    await ref.read(screenBrightnessServiceProvider).setBrightness(
          value: clamped,
          autoMode: true,
        );
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final level = brightnessLevelTen(_brightness);

    return Stack(
      fit: StackFit.expand,
      children: [
        Positioned(
          left: 0,
          top: 0,
          bottom: 0,
          width: width / 2,
          child: Listener(
            behavior: HitTestBehavior.translucent,
            onPointerDown: (event) => _pointerStart = event.position,
            onPointerMove: (event) {
              final start = _pointerStart;
              if (start == null) return;

              if (!_dragging) {
                final delta = event.position - start;
                if (delta.dy.abs() < kTouchSlop && delta.dx.abs() < kTouchSlop) {
                  return;
                }
                if (delta.dx.abs() > delta.dy.abs()) return;
                setState(() => _dragging = true);
              }

              final next = _brightness - event.delta.dy / _sensitivity;
              unawaited(_setBrightness(next));
            },
            onPointerUp: (_) {
              _pointerStart = null;
              setState(() => _dragging = false);
            },
            onPointerCancel: (_) {
              _pointerStart = null;
              setState(() => _dragging = false);
            },
            child: AbsorbPointer(
              absorbing: _dragging,
              child: const SizedBox.expand(),
            ),
          ),
        ),
        IgnorePointer(
          child: AnimatedOpacity(
            opacity: _showIndicator ? 1 : 0,
            duration: const Duration(milliseconds: 200),
            child: Align(
              alignment: Alignment.center,
              child: _BrightnessIndicator(level: level, auto: true),
            ),
          ),
        ),
      ],
    );
  }
}

class _BrightnessIndicator extends StatelessWidget {
  const _BrightnessIndicator({
    required this.level,
    required this.auto,
  });

  final int level;
  final bool auto;

  @override
  Widget build(BuildContext context) {
    final value = level / 10;
    final icon = value < 1.0 / 3.0
        ? Icons.brightness_low
        : value < 2.0 / 3.0
            ? Icons.brightness_medium
            : Icons.brightness_high;

    return Container(
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: const Color(0x88000000),
        borderRadius: BorderRadius.circular(64),
      ),
      height: 52,
      width: auto ? 118 : 108,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(width: 12),
          Icon(
            auto ? Icons.brightness_auto : icon,
            color: Colors.white,
            size: 24,
          ),
          const SizedBox(width: 8),
          Text(
            auto ? '$level / 10' : '${(value * 100).round()}%',
            style: const TextStyle(fontSize: 14, color: Colors.white),
          ),
          const SizedBox(width: 12),
        ],
      ),
    );
  }
}
