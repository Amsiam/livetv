# Cloudflare Tunnel (cloudflared)

Two ways to use **cloudflared** with Live TV.

## Option A — Quick tunnel (local dev)

Best for testing the Flutter app on a **real phone** without LAN IP or opening router ports.

```bash
# Terminal 1 — Django API
cd backend && uv run python manage.py runserver 0.0.0.0:8000

# Terminal 2 — tunnel
./scripts/cloudflared-dev-api.sh
```

cloudflared prints a URL like `https://random-words.trycloudflare.com`.

1. **backend/.env** — allow the tunnel host:

   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
   ```

2. Restart Django, then test:

   ```bash
   curl -s https://YOUR-SUBDOMAIN.trycloudflare.com/v1/health/
   ```

3. **Flutter** (any device with internet):

   ```bash
   cd app
   flutter run --dart-define=API_BASE_URL=https://YOUR-SUBDOMAIN.trycloudflare.com/v1
   ```

Notes:

- URL changes each time you restart the quick tunnel (unless you use a named tunnel).
- HTTPS is handled by Cloudflare — no cert setup on your machine.
- Video streams still go **directly** to third-party HLS URLs; only metadata hits your API.

---

## Option B — Named tunnel (production on KVM4)

Alternative to exposing port **80** on the public internet. Traffic flows:

```
Flutter app → Cloudflare CDN/WAF → cloudflared (on VPS) → Nginx :8134 → Gunicorn :8123
```

### Setup

```bash
# On the VPS (once)
cloudflared tunnel login
cloudflared tunnel create livetv-api
cloudflared tunnel route dns livetv-api tv.test71.xyz

sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/<tunnel-id>.json /etc/cloudflared/
sudo cp deploy/cloudflared/config.yml.example /etc/cloudflared/config.yml
# Edit tunnel UUID, credentials path, and hostname

sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

### DNS

In Cloudflare DNS, the `cloudflared tunnel route dns` command creates a **CNAME** to `<tunnel-id>.cfargotunnel.com`. Keep the record **Proxied** (orange cloud) so CDN cache rules still apply.

### Hardening (optional)

If all traffic goes through the tunnel, you do **not** need to open **8134** on the public firewall — cloudflared connects to `127.0.0.1:8134` on the host (see `deploy/cloudflared/config.yml.example`).

### Django

```bash
# deploy/.env
DJANGO_ALLOWED_HOSTS=tv.test71.xyz
DJANGO_DEBUG=false
```

Cache rules in [deployment.md](../../docs/deployment.md) section 6 still apply — same hostname, same `/v1/` paths.

---

## Option C — Protect Django Admin (Zero Trust)

In [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → Access → Applications:

- Application URL: `https://tv.test71.xyz/admin`
- Policy: e.g. email OTP or Google login for your staff only

Public `/v1/*` stays open; admin gets an extra login layer.

---

## Compare

| Mode | Use case | Stable URL | CDN cache |
|------|----------|------------|-----------|
| Quick tunnel | Dev / demo | No | Limited |
| A record → KVM4 IP | Simple prod | Yes | Yes |
| Named tunnel | Prod without open ports | Yes | Yes |
