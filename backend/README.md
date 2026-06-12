# Live TV Backend

Django + DRF API with Django Admin for match and channel metadata.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.12+
- PostgreSQL and Redis (optional for local dev — SQLite + LocMem cache work out of the box)

## Setup

```bash
cd backend
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

- Admin: http://127.0.0.1:8000/admin/
- API: http://127.0.0.1:8000/v1/matches/
- Health: http://127.0.0.1:8000/v1/health/

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/matches/` | Paginated match list (`status`, `sport`, `page`, `limit`) |
| GET | `/v1/matches/{id}/` | Match detail with active channels |
| GET | `/v1/matches/{id}/channels/` | Active channels for a match |
| GET | `/v1/tv-channels/` | Paginated TV channel catalog (`region`, `category`, `search`, `page`, `limit`) |
| GET | `/v1/tv-channels/{id}/` | Single TV channel (for standalone playback) |
| GET | `/v1/tv-channels/regions/` | Regions with active channel counts |
| GET | `/v1/health/` | Health check |
| GET | `/v1/app-update/?platform=android&build=1` | APK update check (sideload) |
| POST | `/v1/channels/{id}/report-failure/` | Report playback failure from client |

## Channel failure handling

Channels track consecutive failures (`failure_count`). User reports use `CHANNEL_FAILURE_THRESHOLD` (default **100**). Celery health probes use `CHANNEL_HEALTH_FAILURE_THRESHOLD` (default **3**) so server checks can deactivate sooner than client tolerance. Reactivation probes skip inactive channels once `failure_count` reaches **100** (not 3).

- **Celery:** automatic probe + reactivation (see below)
- **Manual:** `uv run python manage.py check_streams` / `reactivate_streams`
- **Client:** `POST /v1/channels/{id}/report-failure/` when playback fails (30s cooldown per IP)
- **Admin:** use “Reset failure count and reactivate” action after fixing a stream URL
- **Telegram:** optional alert to admin chat when a channel is deactivated (see below)

```bash
uv run python manage.py check_streams
uv run python manage.py reactivate_streams
```

## Celery (automatic sync & stream health)

Requires Redis (`docker compose up -d redis` or `REDIS_URL`).

| Task | Schedule (default) | What it does |
|------|-------------------|--------------|
| `health.sync_tv_catalog` | Every 6 hours | Runs `sync_livetv_collector` for configured regions |
| `health.probe_active_streams` | Every 15 min | Parallel chunked URL probes; deactivates dead links |
| `health.reactivate_recovered_streams` | Every 30 min | Re-enables inactive channels when URL responds again |

```bash
# Terminal 1 — worker
./scripts/celery-worker.sh

# Terminal 2 — scheduler
./scripts/celery-beat.sh

# Run once manually
cd backend && uv run celery -A config call health.run_all_maintenance
```

Auto-reactivation applies to channels deactivated by health check, user reports, or dead-link admin action — not manual admin deactivations or sync-missing.

Tune via `.env`: `CELERY_SYNC_CRON_HOUR`, `CELERY_PROBE_CRON_MINUTE`, `STREAM_PROBE_WORKERS` (parallel probes per chunk, default **20**), `CHANNEL_HEALTH_FAILURE_THRESHOLD`.

## App updates (sideload APK)

The Android app checks `GET /v1/app-update/?platform=android&build=N` on launch (`N` = Flutter build number from `pubspec.yaml`, e.g. `1.0.0+1` → `1`).

Responses are cached in Redis and at Cloudflare (`APP_UPDATE_CACHE_TTL`, default **300s**). The cache clears when you save or delete an **App release** in admin.

**Automated publish** (build + store on server + admin row):

```bash
./scripts/publish-apk.sh https://api.yourdomain.com
# remote VPS: add --remote user@host
```

Requires `PUBLIC_API_URL=https://api.yourdomain.com` in `deploy/.env`. APKs are stored under `media/releases/` and served at `/media/releases/...`.

Manage releases in Django admin → **App releases** (or use `python manage.py publish_app_release`):

| Field | Purpose |
|-------|---------|
| **APK file** | Upload here; `download_url` is set automatically |
| **Build number** | Must match `pubspec.yaml` `+N` |
| **Min build number** | Users below this are **forced** to update |
| **Force update** | Everyone below latest build must update |
| **Download URL** | Auto-filled from APK file, or paste an external CDN URL |

## TV channel catalog sync

Sync channels from [LiveTVCollector](https://github.com/bugsfreeweb/LiveTVCollector/tree/main/LiveTV):

```bash
# Default regions from LIVETV_COLLECTOR_REGIONS (or Bangladesh)
uv run python manage.py sync_livetv_collector

# Specific regions
uv run python manage.py sync_livetv_collector --regions Bangladesh,India

# All regions (large download)
uv run python manage.py sync_livetv_collector --all

# Skip reachability checks (faster, saves dead URLs too)
uv run python manage.py sync_livetv_collector --skip-probe
```

Sync saves all upstream URLs quickly. Dead streams are deactivated when users report playback failures in the app (`POST /v1/tv-channels/{id}/report-failure/`). Optional slow probe: `--probe` or `CATALOG_SYNC_PROBE_STREAMS=true`.

Browse synced channels in Django admin under **Catalog channels**. Link a catalog entry to a match channel via **Catalog channel** on the channel inline — stream URLs auto-update on the next sync.

## Telegram notifications

When a channel hits the failure threshold and is deactivated, a message is sent to your Telegram chat.

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token
2. Add the bot to your admin group/channel or start a chat with it
3. Get your chat ID (e.g. message [@userinfobot](https://t.me/userinfobot) or use `getUpdates` on the bot API)
4. Add to `.env`:

```
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

If unset, notifications are skipped silently.

## Docker services (PostgreSQL + Redis)

From project root:

```bash
docker compose up -d
```

Then set in `.env`:

```
POSTGRES_DB=livetv
POSTGRES_USER=livetv
POSTGRES_PASSWORD=livetv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6379/1
```

## Production

See **[docs/deployment.md](../docs/deployment.md)** for the full KVM4 + Docker + Cloudflare setup guide.

Quick start on server:

```bash
cd deploy
cp env.production.example .env   # edit values
./scripts/deploy.sh
```

Public GET responses (`/v1/matches/`, detail, channels) send:

```
Cache-Control: public, max-age=60, s-maxage=60
CDN-Cache-Control: max-age=60
ETag: "..."
```

Configure Cloudflare **Cache Rules** to respect these headers (or cache `GET /v1/matches*` for 60s). Bypass cache for `/admin/*` and all `POST` routes.
