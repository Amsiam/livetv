import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

class ChannelGridItem {
  const ChannelGridItem({
    required this.id,
    required this.name,
    required this.logoUrl,
    this.subtitle,
  });

  final String id;
  final String name;
  final String logoUrl;
  final String? subtitle;
}

class ChannelGrid extends StatelessWidget {
  const ChannelGrid({
    super.key,
    required this.channels,
    required this.selectedId,
    required this.onSelected,
    this.scrollController,
    this.isLoadingMore = false,
  });

  final List<ChannelGridItem> channels;
  final String? selectedId;
  final ValueChanged<ChannelGridItem> onSelected;
  final ScrollController? scrollController;
  final bool isLoadingMore;

  @override
  Widget build(BuildContext context) {
    if (channels.isEmpty) {
      return const Center(child: Text('No channels available'));
    }

    final itemCount = channels.length + (isLoadingMore ? 1 : 0);

    return GridView.builder(
      controller: scrollController,
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 1.05,
      ),
      itemCount: itemCount,
      itemBuilder: (context, index) {
        if (index >= channels.length) {
          return const Center(child: CircularProgressIndicator());
        }

        final channel = channels[index];
        final isSelected = selectedId == channel.id;

        return _ChannelCard(
          channel: channel,
          isSelected: isSelected,
          onTap: () => onSelected(channel),
        );
      },
    );
  }
}

class _ChannelCard extends StatelessWidget {
  const _ChannelCard({
    required this.channel,
    required this.isSelected,
    required this.onTap,
  });

  final ChannelGridItem channel;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Material(
      color: colorScheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: isSelected ? colorScheme.primary : colorScheme.outlineVariant,
          width: isSelected ? 2 : 1,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
          child: Column(
            children: [
              if (channel.logoUrl.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: CachedNetworkImage(
                    imageUrl: channel.logoUrl,
                    width: 44,
                    height: 44,
                    fit: BoxFit.cover,
                    errorWidget: (_, _, _) => Icon(
                      Icons.tv,
                      size: 36,
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                )
              else
                Icon(
                  Icons.tv,
                  size: 36,
                  color: colorScheme.onSurfaceVariant,
                ),
              const SizedBox(height: 6),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      channel.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight:
                                isSelected ? FontWeight.w600 : FontWeight.w500,
                            height: 1.2,
                          ),
                    ),
                    if (channel.subtitle != null &&
                        channel.subtitle!.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        channel.subtitle!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                              height: 1.2,
                            ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
