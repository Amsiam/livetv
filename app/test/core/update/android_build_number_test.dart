import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/core/update/android_build_number.dart';

void main() {
  group('androidPubspecBuildNumber', () {
    test('returns raw value for universal APK', () {
      expect(androidPubspecBuildNumber('3'), 3);
    });

    test('strips arm64 split-per-abi prefix', () {
      expect(androidPubspecBuildNumber('2003'), 3);
    });

    test('strips armeabi split-per-abi prefix', () {
      expect(androidPubspecBuildNumber('1002'), 2);
    });

    test('handles invalid input', () {
      expect(androidPubspecBuildNumber(''), 0);
    });
  });
}
