import 'package:flutter_test/flutter_test.dart';
import 'package:livetv_app/features/player/domain/player_brightness_mode.dart';

void main() {
  group('brightnessLevelTen', () {
    test('maps 0.0 to 0', () {
      expect(brightnessLevelTen(0), 0);
    });

    test('maps 1.0 to 10', () {
      expect(brightnessLevelTen(1), 10);
    });

    test('maps 0.5 to 5', () {
      expect(brightnessLevelTen(0.5), 5);
    });

    test('rounds to nearest level', () {
      expect(brightnessLevelTen(0.14), 1);
      expect(brightnessLevelTen(0.96), 10);
    });
  });

  group('brightnessFromLevelTen', () {
    test('maps levels back to normalized brightness', () {
      expect(brightnessFromLevelTen(0), 0);
      expect(brightnessFromLevelTen(10), 1);
      expect(brightnessFromLevelTen(5), 0.5);
    });
  });
}
