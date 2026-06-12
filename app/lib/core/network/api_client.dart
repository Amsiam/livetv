import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:livetv_app/config/api_config.dart';
import 'package:livetv_app/core/monitoring/crash_reporting.dart';
import 'package:livetv_app/core/monitoring/performance_monitoring.dart';
import 'package:livetv_app/core/network/api_exception.dart';

String _apiErrorMessage(DioException error) {
  final base = ApiConfig.baseUrl;
  final detail = error.message ?? 'Network error';
  if (error.type == DioExceptionType.connectionError ||
      error.type == DioExceptionType.connectionTimeout) {
    return '$detail (API: $base)';
  }
  return detail;
}

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Accept': 'application/json'},
    ),
  );
  dio.interceptors.add(dioPerformanceInterceptor());
  dio.interceptors.add(
    InterceptorsWrapper(
      onError: (error, handler) {
        recordDioError(error);
        handler.next(error);
      },
    ),
  );
  return dio;
});

extension DioX on Dio {
  Future<Map<String, dynamic>> getJson(String path, {Map<String, dynamic>? query}) async {
    try {
      final response = await get<Map<String, dynamic>>(path, queryParameters: query);
      return response.data ?? {};
    } on DioException catch (error) {
      throw ApiException(
        _apiErrorMessage(error),
        statusCode: error.response?.statusCode,
      );
    }
  }

  Future<List<dynamic>> getJsonList(String path, {Map<String, dynamic>? query}) async {
    try {
      final response = await get<List<dynamic>>(path, queryParameters: query);
      return response.data ?? [];
    } on DioException catch (error) {
      throw ApiException(
        _apiErrorMessage(error),
        statusCode: error.response?.statusCode,
      );
    }
  }
}
