import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/core/network/api_client.dart';
import 'package:livetv_app/core/update/android_build_number.dart';
import 'package:livetv_app/core/update/app_update_info.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';

const _installChannel = MethodChannel('com.livetv.livetv_app/install');

class AppUpdateService {
  AppUpdateService(this._dio);

  final Dio _dio;

  Future<PackageInfo> packageInfo() => PackageInfo.fromPlatform();

  Future<int> currentBuildNumber() async {
    final info = await packageInfo();
    final raw = info.buildNumber;
    if (Platform.isAndroid) {
      return androidPubspecBuildNumber(raw);
    }
    return int.tryParse(raw) ?? 0;
  }

  Future<AppUpdateInfo?> checkForUpdate() async {
    if (kIsWeb || !Platform.isAndroid) return null;

    final build = await currentBuildNumber();
    final payload = await _dio.getJson(
      '/app-update/',
      query: {
        'platform': 'android',
        'build': build,
      },
    );
    final info = AppUpdateInfo.fromJson(payload);
    assert(() {
      debugPrint(
        'AppUpdate: build=$build available=${info.updateAvailable} '
        'force=${info.forceUpdate} url=${info.downloadUrl}',
      );
      return true;
    }());
    return info;
  }

  Future<String> downloadApk(
    String url, {
    void Function(double progress)? onProgress,
  }) async {
    final directory = await getExternalCacheDirectories();
    final targetDir = directory?.isNotEmpty == true
        ? directory!.first
        : await getTemporaryDirectory();
    final filePath = '${targetDir.path}/livetv_update.apk';

    final file = File(filePath);
    if (await file.exists()) {
      await file.delete();
    }

    final downloader = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(minutes: 10),
      ),
    );

    await downloader.download(
      url,
      filePath,
      onReceiveProgress: (received, total) {
        if (total <= 0) return;
        onProgress?.call(received / total);
      },
    );

    return filePath;
  }

  Future<void> installApk(String filePath) async {
    if (!Platform.isAndroid) {
      throw UnsupportedError('APK install is only supported on Android.');
    }
    await _installChannel.invokeMethod<void>('installApk', {'path': filePath});
  }
}

final appUpdateServiceProvider = Provider<AppUpdateService>((ref) {
  return AppUpdateService(ref.watch(dioProvider));
});
