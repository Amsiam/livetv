import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:livetv_app/features/matches/domain/match.dart';

class MatchCard extends StatelessWidget {
  const MatchCard({super.key, required this.match, required this.onTap});

  final MatchSummary match;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final time = DateFormat.MMMd().add_jm().format(match.startsAt.toLocal());
    final statusColor = switch (match.status) {
      MatchStatus.live => Colors.redAccent,
      MatchStatus.scheduled => Theme.of(context).colorScheme.primary,
      MatchStatus.ended => Colors.grey,
    };

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 72,
                  height: 72,
                  child: match.posterUrl.isNotEmpty
                      ? CachedNetworkImage(
                          imageUrl: match.posterUrl,
                          fit: BoxFit.cover,
                          errorWidget: (_, _, _) => _posterFallback(context),
                        )
                      : _posterFallback(context),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _StatusBadge(
                          label: match.status.name.toUpperCase(),
                          color: statusColor,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          match.sport,
                          style: Theme.of(context).textTheme.labelSmall
                              ?.copyWith(color: Colors.white54),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      match.displayTitle,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      time,
                      style: Theme.of(
                        context,
                      ).textTheme.bodySmall?.copyWith(color: Colors.white60),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.play_circle_fill, size: 36),
            ],
          ),
        ),
      ),
    );
  }

  Widget _posterFallback(BuildContext context) {
    return ColoredBox(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: const Icon(Icons.sports_soccer, size: 32),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.6)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
        ),
      ),
    );
  }
}
