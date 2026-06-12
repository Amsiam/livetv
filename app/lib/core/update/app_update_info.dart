class AppUpdateInfo {
  const AppUpdateInfo({
    required this.updateAvailable,
    required this.forceUpdate,
    required this.versionName,
    required this.buildNumber,
    required this.minBuildNumber,
    required this.downloadUrl,
    required this.releaseNotes,
  });

  factory AppUpdateInfo.fromJson(Map<String, dynamic> json) {
    return AppUpdateInfo(
      updateAvailable: json['update_available'] == true,
      forceUpdate: json['force_update'] == true,
      versionName: json['version_name']?.toString() ?? '',
      buildNumber: _asInt(json['build_number']),
      minBuildNumber: _asInt(json['min_build_number']),
      downloadUrl: json['download_url']?.toString() ?? '',
      releaseNotes: json['release_notes']?.toString() ?? '',
    );
  }

  final bool updateAvailable;
  final bool forceUpdate;
  final String versionName;
  final int buildNumber;
  final int minBuildNumber;
  final String downloadUrl;
  final String releaseNotes;

  bool get canInstall => updateAvailable && downloadUrl.isNotEmpty;

  static int _asInt(Object? value) {
    if (value is int) return value;
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
