import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:media_kit/media_kit.dart';

import '../../domain/stream_format.dart';
import '../../domain/stream_playback_settings.dart';
import '../providers/hls_playlist_info_provider.dart';
import '../providers/player_settings_handle_provider.dart';
import '../providers/stream_playback_settings_provider.dart';
import '../utils/stream_quality_utils.dart';

class StreamQualityPanel extends ConsumerWidget {
  const StreamQualityPanel({
    super.key,
    required this.streamUrl,
    required this.tracks,
    required this.selectedTrack,
    required this.onApply,
    this.compact = false,
  });

  final String streamUrl;
  final List<VideoTrack> tracks;
  final VideoTrack selectedTrack;
  final Future<void> Function() onApply;
  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(streamPlaybackSettingsProvider);
    final format = detectStreamFormat(streamUrl);
    final hlsAsync = ref.watch(hlsPlaylistInfoProvider(streamUrl));
    final hlsInfo = hlsAsync.valueOrNull;
    final hlsHeights = hlsInfo?.variantHeights ?? const <int>[];
    final hlsParseComplete =
        format != StreamFormat.hls || hlsAsync is AsyncData;
    final playbackHeight = ref.watch(playerSettingsHandleProvider).playbackHeight;

    final presets = qualityPresetsForStream(
      streamUrl,
      tracks,
      minBitrateKbps: settings.minBitrateKbps,
      hlsVariantHeights: hlsHeights,
      hlsParseComplete: hlsParseComplete,
      playbackHeight: playbackHeight,
    );
    final hlsCapMode = usesHlsBitrateCap(
      streamUrl,
      tracks,
      hlsVariantHeights: hlsHeights,
    );
    final showQualityPresets = presets.length > 1;
    final showAbrTuning =
        format == StreamFormat.hls || format == StreamFormat.dash;

    String? streamHint;
    if (hlsHeights.length == 1) {
      streamHint = 'Single ${hlsHeights.first}p variant from playlist';
    } else if (hlsHeights.length > 1) {
      streamHint =
          'Variants: ${hlsHeights.map((h) => '${h}p').join(', ')}';
    } else if (hlsInfo?.isMediaPlaylist == true && playbackHeight != null) {
      streamHint = 'Single ${playbackHeight}p stream';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!compact && streamHint != null) ...[
          Text(streamHint, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 8),
        ],
        if (hlsAsync is AsyncLoading && format == StreamFormat.hls)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: LinearProgressIndicator(minHeight: 2),
          ),
        if (!showQualityPresets)
          Text(
            hlsAsync is AsyncLoading
                ? 'Reading stream qualities…'
                : 'Single fixed quality for this stream.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        if (showQualityPresets)
          ...presets.map((preset) {
            final selected = settings.quality == preset;
            return ListTile(
              dense: true,
              visualDensity: VisualDensity.compact,
              contentPadding: compact
                  ? const EdgeInsets.symmetric(horizontal: 0)
                  : const EdgeInsets.symmetric(horizontal: 4),
              leading: Icon(
                selected ? Icons.radio_button_checked : Icons.radio_button_off,
                size: 22,
              ),
              title: Text(qualityPresetLabel(preset)),
              subtitle: preset == QualityPreset.auto
                  ? const Text('Best available for your network')
                  : hlsCapMode
                      ? Text(
                          'Caps near ${(StreamPlaybackSettings(quality: preset).hlsBitrateCapBps! / 1_000_000).toStringAsFixed(1)} Mbps',
                        )
                      : null,
              onTap: () async {
                ref
                    .read(streamPlaybackSettingsProvider.notifier)
                    .setQuality(preset);
                await onApply();
              },
            );
          }),
        if (showAbrTuning && showQualityPresets) ...[
          const SizedBox(height: 4),
          Text('Advanced', style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 4),
          if (format == StreamFormat.hls)
            _BitrateField(
              label: 'Extra max bitrate (kbps)',
              hint: 'No extra cap',
              value: settings.maxBitrateKbps,
              onChanged: (value) {
                ref
                    .read(streamPlaybackSettingsProvider.notifier)
                    .setMaxBitrateKbps(value);
              },
              onSubmitted: onApply,
            ),
          if (format == StreamFormat.hls) const SizedBox(height: 8),
          DropdownMenu<BufferStrategy>(
            label: const Text('Buffer'),
            width: double.infinity,
            initialSelection: settings.bufferStrategy,
            dropdownMenuEntries: BufferStrategy.values
                .map(
                  (strategy) => DropdownMenuEntry(
                    value: strategy,
                    label: bufferStrategyLabel(strategy),
                  ),
                )
                .toList(),
            onSelected: (value) async {
              if (value == null) return;
              ref
                  .read(streamPlaybackSettingsProvider.notifier)
                  .setBufferStrategy(value);
              await onApply();
            },
          ),
        ],
      ],
    );
  }
}

class _BitrateField extends StatefulWidget {
  const _BitrateField({
    required this.label,
    required this.hint,
    required this.value,
    required this.onChanged,
    required this.onSubmitted,
  });

  final String label;
  final String hint;
  final int? value;
  final ValueChanged<int?> onChanged;
  final Future<void> Function() onSubmitted;

  @override
  State<_BitrateField> createState() => _BitrateFieldState();
}

class _BitrateFieldState extends State<_BitrateField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.value?.toString() ?? '');
  }

  @override
  void didUpdateWidget(covariant _BitrateField oldWidget) {
    super.didUpdateWidget(oldWidget);
    final text = widget.value?.toString() ?? '';
    if (_controller.text != text) _controller.text = text;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _commit() async {
    final raw = _controller.text.trim();
    if (raw.isEmpty) {
      widget.onChanged(null);
    } else {
      final parsed = int.tryParse(raw);
      if (parsed != null && parsed > 0) widget.onChanged(parsed);
    }
    await widget.onSubmitted();
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: _controller,
      keyboardType: TextInputType.number,
      style: Theme.of(context).textTheme.bodyMedium,
      decoration: InputDecoration(
        labelText: widget.label,
        hintText: widget.hint,
        isDense: true,
        border: const OutlineInputBorder(),
        suffixIcon: IconButton(
          icon: const Icon(Icons.check, size: 20),
          onPressed: _commit,
        ),
      ),
      onSubmitted: (_) => _commit(),
    );
  }
}
