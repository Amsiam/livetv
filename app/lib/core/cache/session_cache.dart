/// In-memory cache for the current app session. Cleared when the app process ends.
class SessionCache {
  final Map<String, Object> _store = {};

  T? get<T>(String key) {
    final value = _store[key];
    return value is T ? value : null;
  }

  void set(String key, Object value) => _store[key] = value;

  void removeWhere(bool Function(String key) test) {
    _store.removeWhere((key, _) => test(key));
  }
}
