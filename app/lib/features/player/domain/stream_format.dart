enum StreamFormat {
  hls,
  dash,
  other,
}

StreamFormat detectStreamFormat(String url) {
  final path = Uri.tryParse(url)?.path.toLowerCase() ?? url.toLowerCase();
  if (path.contains('.mpd')) return StreamFormat.dash;
  if (path.contains('.m3u8') || path.contains('m3u8')) return StreamFormat.hls;
  return StreamFormat.other;
}

bool isAdaptiveStreamUrl(String url) {
  final format = detectStreamFormat(url);
  return format == StreamFormat.hls || format == StreamFormat.dash;
}

String streamFormatLabel(StreamFormat format) {
  switch (format) {
    case StreamFormat.hls:
      return 'HLS';
    case StreamFormat.dash:
      return 'DASH';
    case StreamFormat.other:
      return 'Stream';
  }
}
