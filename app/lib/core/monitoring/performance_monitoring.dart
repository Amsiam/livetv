import 'package:dio/dio.dart';
import 'package:firebase_performance/firebase_performance.dart';
import 'package:flutter/foundation.dart';

const _httpMetricKey = 'firebase_http_metric';

/// Enables Firebase Performance (app start + network). Release builds only.
Future<void> configurePerformanceMonitoring() async {
  await FirebasePerformance.instance.setPerformanceCollectionEnabled(kReleaseMode);
}

/// Records API latency in Firebase Performance → Network requests.
Interceptor dioPerformanceInterceptor() {
  return InterceptorsWrapper(
    onRequest: (options, handler) async {
      if (!kReleaseMode) {
        handler.next(options);
        return;
      }

      final metric = FirebasePerformance.instance.newHttpMetric(
        options.uri.toString(),
        _httpMethod(options.method),
      );
      options.extra[_httpMetricKey] = metric;
      await metric.start();
      handler.next(options);
    },
    onResponse: (response, handler) async {
      await _finishHttpMetric(
        response.requestOptions,
        response.statusCode,
      );
      handler.next(response);
    },
    onError: (error, handler) async {
      await _finishHttpMetric(
        error.requestOptions,
        error.response?.statusCode,
      );
      handler.next(error);
    },
  );
}

HttpMethod _httpMethod(String method) {
  return switch (method.toUpperCase()) {
    'POST' => HttpMethod.Post,
    'PUT' => HttpMethod.Put,
    'DELETE' => HttpMethod.Delete,
    'PATCH' => HttpMethod.Patch,
    'HEAD' => HttpMethod.Head,
    'OPTIONS' => HttpMethod.Options,
    _ => HttpMethod.Get,
  };
}

Future<void> _finishHttpMetric(
  RequestOptions options,
  int? statusCode,
) async {
  if (!kReleaseMode) return;

  final metric = options.extra[_httpMetricKey];
  if (metric is! HttpMetric) return;

  if (statusCode != null) {
    metric.httpResponseCode = statusCode;
  }
  await metric.stop();
}
