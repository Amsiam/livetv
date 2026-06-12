import 'package:flutter/foundation.dart';

class ApiConfig {
  const ApiConfig._();

  static const String _envBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  /// Backend `/v1` root. Override with `--dart-define=API_BASE_URL=http://10.0.2.2:8000/v1`.
  static String get baseUrl {
    if (_envBaseUrl.isNotEmpty) {
      return _envBaseUrl.endsWith('/v1') ? _envBaseUrl : '$_envBaseUrl/v1';
    }
    if (kIsWeb) {
      return 'http://127.0.0.1:8000/v1';
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000/v1';
      default:
        return 'http://127.0.0.1:8000/v1';
    }
  }
}
