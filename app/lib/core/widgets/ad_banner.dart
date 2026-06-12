import 'package:flutter/material.dart';

/// Banner ad slot. Hidden until an ad unit is configured (e.g. AdMob).
///
/// Enable with: `--dart-define=AD_BANNER_UNIT_ID=ca-app-pub-...`
class AdBanner extends StatelessWidget {
  const AdBanner({super.key});

  static const _adUnitId = String.fromEnvironment('AD_BANNER_UNIT_ID');

  static bool get isEnabled => _adUnitId.isNotEmpty;

  @override
  Widget build(BuildContext context) {
    if (!isEnabled) {
      return const SizedBox.shrink();
    }

    // TODO: load BannerAd when AdMob (or similar) is integrated.
    return const SizedBox.shrink();
  }
}
