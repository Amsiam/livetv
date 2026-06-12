# Live TV Web

React + Vite + Video.js browser client for `tv.test71.xyz`.

## Development

```bash
cd web
npm install
npm run dev
```

Opens at http://localhost:37233. API calls proxy to `https://tv.test71.xyz/v1` by default.

Override API origin:

```bash
VITE_DEV_API_ORIGIN=http://127.0.0.1:8000 npm run dev
```

## Production build

```bash
npm run build
```

Output: `web/dist/`. The nginx Docker image builds this automatically with `VITE_API_BASE_URL=/v1` (same-origin).

## Deploy

From the server after `git pull`:

```bash
cd /opt/live-tv/deploy
./scripts/roll-app-tier.sh   # rebuilds nginx with embedded web dist
```

Cloudflare should cache hashed `/assets/*` aggressively; `index.html` uses a short TTL from nginx.
