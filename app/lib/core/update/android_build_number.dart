/// Converts Android [PackageInfo.buildNumber] to the pubspec `+N` build value.
///
/// `flutter build apk --split-per-abi` sets `versionCode` to `abi * 1000 + N`
/// (arm64 → `2000 + N`). In-app updates compare against Django `build_number`
/// from pubspec, so we strip the ABI prefix when present.
int androidPubspecBuildNumber(String buildNumber) {
  final code = int.tryParse(buildNumber) ?? 0;
  if (code >= 1000) return code % 1000;
  return code;
}
