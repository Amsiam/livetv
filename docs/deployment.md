# Deployment Guide — Live TV

Deploy the **Django API** on **Hostinger KVM4** with **Docker Compose**, **Cloudflare CDN**, **PostgreSQL**, **Redis**, and **Telegram** alerts. Distribute the **Flutter Android app** as a sideload APK with the production API URL baked in at build time.

## Architecture (production)

```
Flutter app
    ↓
Cloudflare CDN + WAF  (tv.test71.xyz)
    ↓
Nginx :8134 on KVM4 (origin; Cloudflare Tunnel or DNS)
    ↓
Gunicorn (Django + DRF + Admin)
    ↓
PostgreSQL + Redis
    ↑
Celery worker + Celery beat (sync, stream probe, reactivation)
```

Video streams go **directly** from third-party HLS URLs to the app — not through your server.

---

## Prerequisites checklist

| Item | Notes |
|------|-------|
| Hostinger KVM4 | Ubuntu 24.04 recommended |
| Domain | e.g. `tv.test71.xyz` |
| Cloudflare account | Free plan is fine |
| Telegram bot | Optional, for channel failure alerts |
| Git repo access | On the server |

---

## 1. Server initial setup (KVM4)

SSH into the VPS as root, then:

```bash
apt update && apt upgrade -y
apt install -y git curl ufw

# Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# Firewall
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
# Optional: only if exposing Nginx directly (not using Cloudflare Tunnel)
# ufw allow 8134/tcp
ufw enable
```

Log out and back in so Docker group applies.

---

## 2. Clone the project

```bash
mkdir -p /opt/live-tv
cd /opt/live-tv
git clone <your-repo-url> .
```

Project layout on server:

```
/opt/live-tv/
  app/              # Flutter Android app
  backend/          # Django app
  deploy/           # Docker, nginx, production scripts
  scripts/          # flutter-build-apk.sh, cloudflared-dev-api.sh, etc.
  docs/
  docker-compose.yml   # local dev only
```

---

## 3. Configure environment

```bash
cd /opt/live-tv/deploy
cp env.production.example .env
nano .env
```

### Required values

| Variable | Example | Notes |
|----------|---------|-------|
| `DJANGO_SECRET_KEY` | random 50+ chars | `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `false` | Never `true` in production |
| `DJANGO_ALLOWED_HOSTS` | `tv.test71.xyz` | Must match `server_name` in nginx |
| `PUBLIC_API_URL` | `https://tv.test71.xyz` | Public origin for APK `download_url` (no `/v1`) |
| `POSTGRES_PASSWORD` | strong password | Change from default |
| `CORS_ALLOWED_ORIGINS` | `https://yourdomain.com` | Flutter web origin if used |

### Optional

| Variable | Default | Purpose |
|----------|---------|---------|
| `MATCH_LIST_CACHE_TTL` | `60` | Redis + Cloudflare cache TTL for matches/TV (seconds) |
| `APP_UPDATE_CACHE_TTL` | `300` | Redis + Cloudflare cache TTL for `/v1/app-update/` (seconds) |
| `CHANNEL_FAILURE_THRESHOLD` | `100` | User/app playback reports before deactivation (see §8) |
| `CHANNEL_HEALTH_FAILURE_THRESHOLD` | `3` | Celery probe failures before deactivation |
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | — | Your chat or group ID |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Set automatically in compose |
| `STREAM_PROBE_TIMEOUT` | `5` | HTTP timeout for stream health probes |
| `STREAM_PROBE_WORKERS` | `20` | Parallel probes per Celery chunk |
| `STREAM_PROBE_CHUNK_SIZE` | `100` | Channels per probe task |
| `CATALOG_SYNC_CHUNK_SIZE` | `500` | Channels per catalog sync chunk |
| `CELERY_SYNC_CRON_HOUR` | `*/6` | Catalog sync schedule (UTC) |
| `CELERY_PROBE_CRON_MINUTE` | `*/15` | Dead-link probe schedule |
| `CELERY_REACTIVATE_CRON_MINUTE` | `*/30` | Reactivate recovered streams |
| `LIVETV_COLLECTOR_REGIONS` | `Bangladesh,India,Pakistan` | Regions for catalog sync |

**Do not commit `.env`** — it is gitignored.

---

## 4. Configure Nginx

Edit `deploy/nginx/livetv.conf` before first deploy:

| Setting | Default in repo | Must match |
|---------|-----------------|------------|
| `server_name` | `tv.test71.xyz` | `DJANGO_ALLOWED_HOSTS` in `deploy/.env` |
| `listen` | `8134` | `NGINX_PUBLISH_PORT` in `deploy/.env` (compose maps host → container) |
| `upstream django` | `web:8123` | `GUNICORN_BIND=0.0.0.0:8123` on the **web** service (set in compose) |

Cloudflare real-IP blocks are already included. Update from [Cloudflare IP ranges](https://www.cloudflare.com/ips/) if needed.

**Ports:** Gunicorn listens on **8123** inside Docker; Nginx proxies to it and publishes **8134** on the host. Local dev (`runserver`) still uses **8000** — production ports only.

**Cloudflare:** Orange-cloud proxied DNS only forwards **80/443** to the origin. With origin on **8134**, use **Cloudflare Tunnel** (§6 Option B) pointing at `http://127.0.0.1:8134`, or grey-cloud DNS and open `8134` on the firewall.

---

## 5. First deploy

```bash
cd /opt/live-tv/deploy
chmod +x scripts/*.sh
./scripts/deploy.sh
```

Create admin user:

```bash
docker compose -f docker-compose.prod.yml exec web \
  uv run python manage.py createsuperuser
```

Verify:

```bash
./scripts/health-check.sh
curl -s http://localhost:8134/v1/matches/ | head
```

---

## 6. Cloudflare setup

### Option A — DNS to KVM4 (classic)

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A or CNAME | `tv` (or tunnel CNAME) | KVM4 IP or tunnel | Proxied (orange cloud) |

### Option B — Cloudflare Tunnel (`cloudflared`)

If you have **cloudflared** installed, you can skip opening the origin port publicly. Run a named tunnel on the VPS that connects to local Nginx on **8134**. Full steps: **[deploy/cloudflared/README.md](../deploy/cloudflared/README.md)**.

For **local dev** (Flutter on a physical phone):

```bash
./scripts/cloudflared-dev-api.sh
# Use the printed https://….trycloudflare.com URL as API_BASE_URL
```

Add `.trycloudflare.com` to `DJANGO_ALLOWED_HOSTS` while using quick tunnels.

### SSL/TLS

- **Encryption mode:** Full (strict)
- Generate **Origin Certificate** in Cloudflare → SSL/TLS → Origin Server
- Install on Nginx if terminating TLS on origin (optional; Cloudflare Tunnel → HTTP `:8134` is OK with Full mode)

### Cache Rules

Create rules in order (top = highest priority):

**Rule 1 — Bypass admin and health**

- When: URI Path starts with `/admin` **or** `/v1/health`
- Then: Cache eligibility = Bypass

**Rule 2 — Bypass all non-GET**

- When: Request Method does not equal `GET`
- Then: Cache eligibility = Bypass

This includes `POST /v1/channels/{id}/report-failure/` and `POST /v1/tv-channels/{id}/report-failure/` — failure reports always hit your origin (never cached).

**Rule 3 — Cache public match API**

- When: URI Path starts with `/v1/matches`
- And: Request Method equals `GET`
- Then: Cache eligibility = Eligible, Edge TTL = **Respect origin** (or 60 seconds)

Covers match list, match detail (`/v1/matches/{id}/`), and nested channel list (`/v1/matches/{id}/channels/`).

**Rule 4 — Cache public TV channel API**

- When: URI Path starts with `/v1/tv-channels`
- And: Request Method equals `GET`
- Then: Cache eligibility = Eligible, Edge TTL = **Respect origin** (or 60 seconds)

List responses use `?grouped=true` (deduped channels with `sources[]`). Detail responses include all alternate sources for failover.

**Rule 5 — Cache app update checks**

- When: URI Path starts with `/v1/app-update`
- And: Request Method equals `GET`
- Then: Cache eligibility = Eligible, Edge TTL = **Respect origin** (or 300 seconds)

Most users share the same `build` query param, so the edge serves one cached response per build. Origin Redis caches the latest release row and clears automatically when you edit **App releases** in admin.

**Rule 6 — Cache APK downloads (free CDN)**

- When: URI Path starts with `/media/releases`
- And: Request Method equals `GET`
- Then: Cache eligibility = Eligible, Edge TTL = 1 month (or Respect origin `Cache-Control`)

Each APK filename includes the version (`livetv-android-v1.0.4-b5.apk`), so edge cache is safe for a long TTL. After the first request per Cloudflare PoP, thousands of in-app downloads are served from Cloudflare — not your VPS. Requires the orange-cloud proxied production domain; **trycloudflare quick tunnels are not a CDN**.

### WAF rate limiting

- Path: `/v1/*`
- Rate: 60 requests per minute per IP

### Verify Cloudflare caching

**Match API:**

```bash
curl -I https://tv.test71.xyz/v1/matches/
```

Look for:

```
cf-cache-status: HIT   # after second request
cache-control: public, max-age=60, s-maxage=60
```

**APK downloads** (replace with your published filename):

```bash
curl -I https://tv.test71.xyz/media/releases/livetv-android-v1.0.4-b5.apk
curl -I https://tv.test71.xyz/media/releases/livetv-android-v1.0.4-b5.apk
```

First request: `cf-cache-status: MISS` (origin serves once). Second request: `cf-cache-status: HIT`. Response should include:

```
cache-control: public, max-age=31536000, immutable
```

Optional: after `./scripts/publish-apk.sh`, run one `curl` to the new APK URL to warm the nearest edge cache before users update.

**TV channel API:**

```bash
curl -I "https://tv.test71.xyz/v1/tv-channels/?grouped=true"
```

---

## 7. Caching strategy (three layers)

Reads are cached at three levels. Writes (admin, failure reports) bypass Cloudflare and invalidate Redis where noted.

### Layer 1 — Cloudflare edge (GET only)

| Path | Edge TTL | Notes |
|------|----------|--------|
| `GET /v1/matches*` | 60s (origin `Cache-Control`) | List, detail, per-match channels |
| `GET /v1/tv-channels*` | 60s | Grouped list + detail with `sources[]` |
| `GET /v1/app-update/` | 300s | One cached JSON per `build` param per PoP |
| `GET /media/releases/*` | Long (immutable) | APK bytes — largest bandwidth saver |
| `GET /v1/health/` | Bypass | Always fresh |
| `POST /v1/*/report-failure/` | Bypass | Never cached |
| `/admin/*` | Bypass | Staff UI |

Origin sends `Cache-Control: public, max-age=60, s-maxage=60` on public JSON (`MATCH_LIST_CACHE_TTL`). Tune in `deploy/.env`.

### Layer 2 — Redis (Django origin)

| Cache key pattern | TTL | Populated by |
|-------------------|-----|--------------|
| `matches:list:*` | `MATCH_LIST_CACHE_TTL` | `GET /v1/matches/` |
| `matches:detail:{id}` | `MATCH_LIST_CACHE_TTL` | `GET /v1/matches/{id}/` |
| `matches:channels:{id}` | `MATCH_LIST_CACHE_TTL` | `GET /v1/matches/{id}/channels/` |
| `tv-channels:list:*` | `MATCH_LIST_CACHE_TTL` | `GET /v1/tv-channels/` |
| `tv-channels:detail:{id}` | `MATCH_LIST_CACHE_TTL` | `GET /v1/tv-channels/{id}/` |
| `releases:latest:{platform}` | `APP_UPDATE_CACHE_TTL` | `GET /v1/app-update/` |
| `*_failure_report:*` | 30s | Cooldown keys only (not response cache) |

**Automatic invalidation:**

| Event | What clears |
|-------|-------------|
| Save/delete **Match** or **Match channel** | Match list + that match’s detail/channels |
| Save/delete **Catalog channel** | TV list + that channel’s detail |
| Catalog sync (Celery) | Full TV list cache |
| Save/delete **App release** | Latest-release key for platform |
| Channel **deactivation** | Related match or catalog caches |

After admin edits, clients may still see old data for up to **60s** at Cloudflare edge even when Redis was cleared. Purge Cloudflare cache for urgent changes.

**Manual flush (troubleshooting):**

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB
```

### Layer 3 — Flutter app (in-memory session)

| Data | Behavior |
|------|----------|
| Match list / detail | `SessionCache` until pull-to-refresh |
| TV channel list / detail | Same |
| App bootstrap | Prefetch live matches + grouped TV page 1 |

Pull-to-refresh on **Live Matches** and **TV Channels** re-fetches from the API (may still be a Cloudflare HIT for under 60s).

### Why this matters at scale

During live events, **metadata** traffic can spike heavily. Cloudflare + Redis keep almost all reads off PostgreSQL. **Video never hits your server** — clients pull HLS from third-party URLs.

---

## 8. Client failure reports (server load)

**Short answer: No**, failure POSTs will not bottleneck a properly configured KVM4 setup.

Endpoints:

- `POST /v1/channels/{id}/report-failure/` — match sources
- `POST /v1/tv-channels/{id}/report-failure/` — TV / catalog sources

### Per request (lightweight)

1. Redis cooldown check (**30s** per **IP + channel id**)
2. If allowed: one SELECT + one UPDATE (`failure_count += 1`)
3. If threshold reached: deactivate, invalidate Redis, optional Telegram
4. Small JSON response

No video proxying. No heavy CPU on the request path.

### Throttling already in place

| Limit | Value | Effect |
|-------|-------|--------|
| Cooldown | 30s / IP / channel id | Prevents repeat spam on same source |
| Cloudflare WAF | 60 req/min/IP on `/v1/*` | Caps abusive clients |
| Failure threshold | 100 (default) | Deactivates after sustained reports |
| Source failover | Next source in app | One report per failed source per attempt |

Example: 4 sources all fail → up to **4 POSTs** (different ids), not a continuous stream.

### Rough capacity

| Scenario | Origin load |
|----------|-------------|
| 10k viewers, 5% report one failure | ~500 POSTs over minutes — trivial |
| 10k viewers open match list | Cloudflare HIT + Redis — not 10k DB reads |
| Catalog sync / probes | Celery workers — off the user API path |

Uncached `GET /v1/matches/` at scale is a bigger risk than failure POSTs. Caching (§7) addresses that.

### Tuning (`deploy/.env`)

```
CHANNEL_FAILURE_THRESHOLD=100
CHANNEL_HEALTH_FAILURE_THRESHOLD=3
MATCH_LIST_CACHE_TTL=60
```

Avoid `CHANNEL_FAILURE_THRESHOLD=1` in production (constant deactivations + cache churn).

---

## 9. Background jobs (Celery)

Production compose runs **celery-worker** and **celery-beat** alongside the web container. No host crontab needed for sync or stream health.

| Task | Default schedule | Action |
|------|------------------|--------|
| `health.sync_tv_catalog` | Every 6 hours | Dispatches per-region sync; each region upserts in chunks |
| `health.probe_active_streams` | Every 15 min | Probes **active** channels only; increments `failure_count` (demerit points) |
| `health.reactivate_recovered_streams` | Every 30 min | Probes **inactive** channels only if `failure_count` &lt; `CHANNEL_FAILURE_THRESHOLD` (100) |

Large regions (~28k channels) are split into Celery chunks so work spreads across workers instead of one long task. Tune in `deploy/.env`:

```
CATALOG_SYNC_CHUNK_SIZE=500
STREAM_PROBE_CHUNK_SIZE=100
STREAM_PROBE_WORKERS=20
CATALOG_SYNC_PROBE_STREAMS=false
```

Keep `CATALOG_SYNC_PROBE_STREAMS=false` for fast catalog upserts; rely on chunked `probe_active_streams` for dead-link checks.

**Failure count (demerit points) and Celery probes:**

| Channel state | Celery behavior |
|---------------|-----------------|
| **Active** | Probed every 15 min; health failures deactivate at `CHANNEL_HEALTH_FAILURE_THRESHOLD` (3); client reports deactivate at `CHANNEL_FAILURE_THRESHOLD` (100) |
| **Inactive, `failure_count` ≥ 100** | **Skipped** — confirmed dead for reactivation; no more recovery probes |
| **Inactive, `failure_count` &lt; 100** | Recovery task may re-probe (e.g. health-deactivated at 3 can still auto-recover) |
| **Inactive, reason `dead_link` or `admin`** | **Skipped** — manual admin decision; reactivate from inactive review only |

This avoids re-checking tens of thousands of known-dead URLs every 30 minutes. To retry a confirmed-dead channel, use **Inactive TV channels (review)** or **Inactive match channels (review)** → **Verify and reactivate** (resets `failure_count`).

The Android app also reports dead streams when playback fails or times out (~25s). See **§8** for load characteristics; Celery probes are the heavy background work, not client POSTs.

Configure regions in `deploy/.env`:

```
LIVETV_COLLECTOR_REGIONS=Bangladesh,India,Pakistan
```

Source: [LiveTVCollector](https://github.com/bugsfreeweb/LiveTVCollector/tree/main/LiveTV)

### Match channels in admin

When creating a live match:

1. **Matches** → add match → inline **Match channels**
2. **Catalog pick (recommended):** search grouped TV channel by name (e.g. `Geo Super · Sports (4 sources)`). One row auto-fills name/logo/stream; the app exposes **all catalog sources** for that channel name.
3. **Manual:** leave catalog empty, enter name + stream URL yourself.

You do not need one admin row per source when using catalog pick.

Verify after deploy:

```bash
docker compose -f docker-compose.prod.yml ps celery-worker celery-beat
docker compose -f docker-compose.prod.yml exec celery-worker \
  uv run celery -A config inspect ping --timeout 10
```

Manual one-shot (optional):

```bash
docker compose -f docker-compose.prod.yml exec celery-worker \
  uv run celery -A config call health.run_all_maintenance
```

Equivalent management commands (debugging):

```bash
docker compose -f docker-compose.prod.yml exec web uv run python manage.py sync_livetv_collector
docker compose -f docker-compose.prod.yml exec web uv run python manage.py check_streams
docker compose -f docker-compose.prod.yml exec web uv run python manage.py reactivate_streams
```

---

## 10. Telegram notifications

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Message the bot, then get chat ID from `getUpdates`
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `deploy/.env`
4. Restart backend containers:

```bash
docker compose -f docker-compose.prod.yml up -d web celery-worker celery-beat
```

5. Test:

```bash
docker compose -f docker-compose.prod.yml exec web uv run python manage.py test_telegram
```

Alerts fire when a channel is **deactivated** after hitting the failure threshold.

---

## 11. Updates (redeploy)

```bash
cd /opt/live-tv/deploy
./scripts/deploy.sh
```

Or manually:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T web uv run python manage.py migrate --noinput
```

---

## 12. Flutter Android app

The app does **not** read the API URL from a config file at runtime on release builds. You must pass it at compile time.

### Production APK (automated)

Set `PUBLIC_API_URL=https://tv.test71.xyz` in `deploy/.env` (no `/v1` suffix).

**One command** — build, store APK on the server, register **App release**:

```bash
# On the VPS:
./scripts/publish-apk.sh https://tv.test71.xyz

# From laptop → remote VPS:
./scripts/publish-apk.sh https://tv.test71.xyz --remote deploy@your-vps
```

APKs land in `media/releases/` and are served at `https://tv.test71.xyz/media/releases/...`. The **App release** row and `download_url` are created automatically.

### APK distribution (free CDN)

No extra service or code changes — `download_url` stays on your API domain. Cloudflare Free caches APK files at the edge (see **Rule 6** in §6). Nginx sends long-lived `Cache-Control` headers for `/media/releases/` ([deploy/nginx/livetv.conf](../deploy/nginx/livetv.conf)).

| Traffic | Who serves it |
|---------|----------------|
| `GET /v1/app-update/` | Cloudflare edge (small JSON, ~300s TTL) |
| `GET /media/releases/*.apk` | Cloudflare edge after first hit per PoP (~32 MB) |
| Admin, POST, first cache miss | Your VPS |

At 30k users × ~32 MB, origin bandwidth stays small (one fetch per edge PoP per APK version) instead of ~960 GB through the VPS.

Manual alternative:

```bash
./scripts/flutter-build-apk.sh https://tv.test71.xyz
cd backend && PUBLIC_API_URL=https://tv.test71.xyz \
  uv run python manage.py publish_app_release \
  --apk ../app/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk \
  --pubspec ../app/pubspec.yaml
```

Or upload **APK file** in Django admin → **App releases**.

Plain `flutter build apk` without `--dart-define=API_BASE_URL=...` defaults to `http://10.0.2.2:8000/v1` (emulator only) — real devices will fail to connect.

### In-app updates (sideload)

On launch the app calls `GET /v1/app-update/?platform=android&build=N` (`N` = pubspec `+N`, e.g. `1.0.0+1` → `1`). Split APKs encode Android `versionCode` as `abi×1000+N`; the app normalizes that before calling the API. Responses are cached at Redis + Cloudflare (`APP_UPDATE_CACHE_TTL`, default **5 minutes**); cache clears when you save an **App release**.

**APK size:** `./scripts/flutter-build-apk.sh` builds an **arm64-only** split APK (~32 MB), similar to what Play serves per device. Pass `--universal` for a single fat APK (~97 MB, all ABIs). For Google Play, build an App Bundle: `cd app && flutter build appbundle --dart-define=API_BASE_URL=https://tv.test71.xyz/v1`.

Workflow: bump `version: x.y.z+N` in `app/pubspec.yaml` → `./scripts/publish-apk.sh https://tv.test71.xyz` → users get prompted on next launch.

### Local dev on a physical phone

```bash
# Terminal 1 — API
cd backend && uv run python manage.py runserver 0.0.0.0:8000

# Terminal 2 — quick tunnel (add hostname to DJANGO_ALLOWED_HOSTS)
./scripts/cloudflared-dev-api.sh

# Terminal 3 — run app against tunnel URL
./scripts/flutter-run-tunnel.sh https://xxxx.trycloudflare.com
```

Same Wi‑Fi alternative: `./scripts/flutter-build-apk.sh http://192.168.x.x:8000` (no tunnel).

### Optional client config

| Build flag | Purpose |
|------------|---------|
| `API_BASE_URL` | Required for release APKs (see above) |
| `AD_BANNER_UNIT_ID` | AdMob banner unit; omit to hide ad slot |
| Firebase | Configure with `flutterfire configure` in `app/` for Crashlytics (release-only reporting) |

---

## 13. Backups

### PostgreSQL

Daily backup cron:

```bash
crontab -e
```

```cron
0 3 * * * docker compose -f /opt/live-tv/deploy/docker-compose.prod.yml exec -T postgres pg_dump -U livetv livetv | gzip > /opt/backups/livetv-$(date +\%Y\%m\%d).sql.gz
```

```bash
mkdir -p /opt/backups
```

### Restore

```bash
gunzip -c /opt/backups/livetv-20260101.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U livetv livetv
```

Hostinger also provides weekly VPS snapshots — enable in the control panel.

---

## 14. Production verification checklist

Run after every deploy:

- [ ] `curl https://tv.test71.xyz/v1/health/` → `{"status":"ok"}`
- [ ] `curl https://tv.test71.xyz/v1/matches/` → JSON list
- [ ] Admin login at `https://tv.test71.xyz/admin/`
- [ ] Second `GET /v1/matches/` and `GET /v1/tv-channels/?grouped=true` show `cf-cache-status: HIT`
- [ ] `docker compose -f docker-compose.prod.yml ps` — web, nginx, postgres, redis, celery-worker, celery-beat all `Up`
- [ ] `./scripts/health-check.sh` — API on `:8134` + Celery ping OK
- [ ] `docker compose -f docker-compose.prod.yml exec web uv run python manage.py test_telegram` (if configured)
- [ ] Create test match + channel in admin → appears in API within 60s (or after cache TTL)
- [ ] `curl "https://tv.test71.xyz/v1/app-update/?platform=android&build=1"` → JSON update payload
- [ ] Release APK built with `./scripts/flutter-build-apk.sh https://tv.test71.xyz` loads matches on a real device

---

## 15. Troubleshooting

| Problem | Fix |
|---------|-----|
| 502 Bad Gateway | `docker compose logs web` — check migrations, env vars |
| 400 DisallowedHost | Add domain to `DJANGO_ALLOWED_HOSTS`, restart web |
| API empty after admin edit | Wait 60s for cache TTL, or flush Redis: `docker compose exec redis redis-cli FLUSHDB` |
| Cloudflare not caching | Check Cache Rules; ensure `Cache-Control` headers present (`curl -I`) |
| Telegram not sending | Verify token/chat ID; run `test_telegram`; check `docker compose logs web` |
| Static/admin CSS broken | `docker compose exec web uv run python manage.py collectstatic --noinput` |
| Flutter app “network error” on phone | Rebuild with `./scripts/flutter-build-apk.sh https://tv.test71.xyz` — emulator default URL does not work on devices |
| `failure_count` not rising in admin | App must hit playback timeout (~25s) or error; reports are cooldown-limited (30s/IP); check API reachability from the phone |
| In-app update not offered | Add **App release** in admin; wait up to `APP_UPDATE_CACHE_TTL` (default 5 min) or purge Cloudflare cache for `/v1/app-update`; ensure `download_url` is HTTPS |

### Useful logs

```bash
cd /opt/live-tv/deploy
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f nginx
```

---

## 16. Local dev vs production

| | Local | Production |
|---|-------|------------|
| Compose file | `docker-compose.yml` (root) | `deploy/docker-compose.prod.yml` |
| Env file | `backend/.env` | `deploy/.env` |
| Server | `runserver` | Gunicorn + Nginx |
| Flutter API URL | Tunnel / LAN / emulator `10.0.2.2` | `--dart-define=API_BASE_URL=https://tv.test71.xyz/v1` |
| Cloudflare | Optional (quick tunnel for phones) | Required for scale |
| DEBUG | `true` | `false` |

---

## Related docs

- [architecture.md](./architecture.md) — system design
- [best-practices.md](./best-practices.md) — Django/DRF guidelines
- [backend/README.md](../backend/README.md) — API reference
