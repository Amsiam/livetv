import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit_video/media_kit_video.dart';

import '../../domain/player_brightness_mode.dart';
import '../providers/player_brightness_mode_provider.dart';
import '../utils/live_tv_fullscreen.dart';
import 'live_tv_brightness_gesture.dart';

/// Material controls plus swipe-up to enter fullscreen in embedded mode.
Widget liveTvVideoControls(VideoState state) {
  return Builder(
    builder: (context) {
      return Consumer(
        builder: (context, ref, _) {
          final brightnessMode = ref.watch(playerBrightnessModeProvider);
          final fullscreen = isFullscreen(context);
          final autoBrightness = brightnessMode == PlayerBrightnessMode.auto;

          return Stack(
            fit: StackFit.expand,
            clipBehavior: Clip.none,
            children: [
              MaterialVideoControls(state),
              if (!fullscreen) const _SwipeUpForFullscreen(),
              if (fullscreen && autoBrightness) const LiveTvBrightnessGesture(),
            ],
          );
        },
      );
    },
  );
}

class _SwipeUpForFullscreen extends StatefulWidget {
  const _SwipeUpForFullscreen();

  @override
  State<_SwipeUpForFullscreen> createState() => _SwipeUpForFullscreenState();
}

class _SwipeUpForFullscreenState extends State<_SwipeUpForFullscreen>
    with SingleTickerProviderStateMixin {
  static const _swipeDistanceThreshold = 48.0;
  static const _swipeVelocityThreshold = 300.0;
  static const _maxDragForProgress = 100.0;

  late final AnimationController _pulseController;
  double _dragDelta = 0;
  bool _triggered = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  double get _progress {
    if (_dragDelta >= 0) return 0;
    return (-_dragDelta / _maxDragForProgress).clamp(0.0, 1.0);
  }

  bool get _willTrigger =>
      _dragDelta < -_swipeDistanceThreshold || _progress >= 0.85;

  void _onDragStart(DragStartDetails _) {
    _triggered = false;
    _pulseController.reset();
    setState(() => _dragDelta = 0);
  }

  void _onDragUpdate(DragUpdateDetails details) {
    setState(() {
      _dragDelta += details.delta.dy;
      if (_dragDelta > 0) _dragDelta = 0;
    });
  }

  Future<void> _onDragEnd(DragEndDetails details) async {
    final velocity = details.primaryVelocity ?? 0;
    final swipedUp = _dragDelta < -_swipeDistanceThreshold ||
        velocity < -_swipeVelocityThreshold;

    if (swipedUp && !_triggered) {
      _triggered = true;
      HapticFeedback.lightImpact();
      await _pulseController.forward();
      if (mounted) {
        await enterLiveTvFullscreen(context);
      }
    }

    if (mounted) {
      setState(() => _dragDelta = 0);
      _pulseController.reset();
    }
  }

  @override
  Widget build(BuildContext context) {
    final progress = _progress;
    final showHint = progress > 0.02 || _pulseController.isAnimating;

    return Positioned.fill(
      child: Stack(
        fit: StackFit.expand,
        clipBehavior: Clip.hardEdge,
        children: [
          GestureDetector(
            behavior: HitTestBehavior.translucent,
            onVerticalDragStart: _onDragStart,
            onVerticalDragUpdate: _onDragUpdate,
            onVerticalDragEnd: _onDragEnd,
            child: const SizedBox.expand(),
          ),
          if (showHint)
            IgnorePointer(
              child: AnimatedOpacity(
                opacity: progress.clamp(0.0, 1.0),
                duration: const Duration(milliseconds: 80),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.bottomCenter,
                      end: Alignment.topCenter,
                      stops: const [0.0, 0.55, 1.0],
                      colors: [
                        Colors.black.withValues(alpha: 0.55 * progress),
                        Colors.black.withValues(alpha: 0.2 * progress),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),
            ),
          if (showHint)
            IgnorePointer(
              child: Align(
                alignment: Alignment.bottomCenter,
                child: Padding(
                  padding: EdgeInsets.only(
                    bottom: 16 + progress * 28,
                  ),
                  child: AnimatedBuilder(
                    animation: _pulseController,
                    builder: (context, child) {
                      final pulse = Curves.easeOut.transform(
                        _pulseController.value,
                      );
                      final scale = 1.0 + pulse * 0.12;
                      return Transform.scale(
                        scale: scale,
                        child: child,
                      );
                    },
                    child: _SwipeUpHint(
                      progress: progress,
                      ready: _willTrigger,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _SwipeUpHint extends StatelessWidget {
  const _SwipeUpHint({
    required this.progress,
    required this.ready,
  });

  final double progress;
  final bool ready;

  @override
  Widget build(BuildContext context) {
    final lift = progress * 10;
    final iconSize = 28.0 + progress * 10;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Transform.translate(
          offset: Offset(0, -lift),
          child: Icon(
            Icons.keyboard_arrow_up_rounded,
            size: iconSize,
            color: ready ? Colors.white : Colors.white70,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          ready ? 'Release for fullscreen' : 'Swipe up',
          style: TextStyle(
            color: ready ? Colors.white : Colors.white70,
            fontSize: 12,
            fontWeight: ready ? FontWeight.w600 : FontWeight.w500,
            letterSpacing: 0.2,
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          width: 56,
          height: 3,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: progress,
              backgroundColor: Colors.white24,
              valueColor: AlwaysStoppedAnimation<Color>(
                ready ? Colors.white : Colors.white70,
              ),
            ),
          ),
        ),
        if (progress > 0.15) ...[
          const SizedBox(height: 6),
          ...List.generate(2, (index) {
            final phase = (progress * math.pi * 2) - index * 0.8;
            final wave = (math.sin(phase) * 0.5 + 0.5) * progress;
            return Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Opacity(
                opacity: 0.25 + wave * 0.45,
                child: Icon(
                  Icons.keyboard_arrow_up_rounded,
                  size: 16 + wave * 6,
                  color: Colors.white54,
                ),
              ),
            );
          }),
        ],
      ],
    );
  }
}
