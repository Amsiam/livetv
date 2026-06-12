# Live TV — Flutter App

Cross-platform client for live match streams and TV channel catalog.

## Stack

- Flutter 3.x
- Riverpod (state)
- go_router (navigation)
- media_kit (HLS playback)
- Dio (HTTP)

## Run locally

1. Start the Django API (`backend/`) on port 8000.
2. From this directory:

```bash
flutter pub get
flutter run
```

### API base URL

Default per platform:

| Platform | API URL |
|----------|---------|
| Android emulator | `http://10.0.2.2:8000/v1` |
| iOS / Web / Desktop | `http://127.0.0.1:8000/v1` |

Override:

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.10:8000/v1
```

### Cloudflare Tunnel (any network, HTTPS)

With [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) and the Django API running locally:

```bash
# from repo root
./scripts/cloudflared-dev-api.sh
```

Use the printed `https://….trycloudflare.com` URL:

```bash
flutter run --dart-define=API_BASE_URL=https://YOUR-SUBDOMAIN.trycloudflare.com/v1
```

See [deploy/cloudflared/README.md](../deploy/cloudflared/README.md).

### Release APK (real phone)

`flutter build apk` **without** `--dart-define` bakes in `http://10.0.2.2:8000/v1` — that address only works on the **emulator**, not on a physical phone. You will see `ApiException` / connection errors.

Always pass your API URL when building for users:

```bash
# from repo root — Cloudflare tunnel or production HTTPS
./scripts/flutter-build-apk.sh https://YOUR-SUBDOMAIN.trycloudflare.com

# same Wi‑Fi as your PC (find IP: ip addr | grep 192.168)
./scripts/flutter-build-apk.sh http://192.168.1.10:8000
```

APK output (default): `app/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` (~32 MB). Add `--universal` to the script for a fat APK.

## Screens

- **Matches** — list, filters (Live / Upcoming / All), pull-to-refresh, pagination
- **Match player** — HLS playback, channel switcher, failure reporting
- **TV** — browse by region, search, standalone channel player

## Tests

```bash
flutter test
flutter analyze
```
