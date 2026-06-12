# Feature List — Live TV App

Features grouped by phase. v1 = Phase 1 (MVP).

---

## Phase 1 — MVP

### Flutter client

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F1.1 | Match list homepage | Scrollable list of matches with team names, time, poster, live badge | Must |
| F1.2 | Status filters | Tabs/filters: Live \| Upcoming \| All | Must |
| F1.3 | Pull-to-refresh | Manual refresh of match list | Must |
| F1.4 | Background refresh | Auto-refresh every 30–60s while app is foregrounded | Should |
| F1.5 | Pagination | 20 matches per page, infinite scroll or load-more | Must |
| F1.6 | Match detail / player | Tap match → full-screen HLS player | Must |
| F1.7 | Default channel | Auto-play highest-priority active channel | Must |
| F1.8 | Channel switcher | Switch between multiple channels per match without leaving player | Must |
| F1.9 | Player states | Loading, playing, error, retry on stream failure | Must |
| F1.10 | Scroll position | Preserve list scroll position when returning from player | Should |
| F1.11 | Client-side cache | In-memory + short disk cache (~60s) for match/channel data | Should |

### Backend (Django + DRF)

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| B1.1 | Match model | title, sport, teams, starts_at, status, poster_url, sort_order | Must |
| B1.2 | Channel model | name, language, logo_url, stream_url, priority, is_active | Must |
| B1.3 | Public REST API | `GET /v1/matches`, `/v1/matches/{id}`, `/v1/matches/{id}/channels` | Must |
| B1.4 | Pagination | Page-based match list | Must |
| B1.5 | Status filter | Filter matches by scheduled/live/ended | Must |
| B1.6 | Redis caching | Cache list + detail responses; invalidate on admin save | Must |
| B1.7 | Health endpoint | `GET /v1/health` | Must |
| B1.8 | Django Admin — matches | CRUD with list filters, search, status actions | Must |
| B1.9 | Django Admin — channels | TabularInline on match edit; priority, is_active | Must |
| B1.10 | Bulk admin actions | Mark as live/ended, deactivate channels | Should |
| B1.11 | CSV import | Bulk match + channel import via django-import-export | Should |

### Infrastructure

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| I1.1 | KVM4 deployment | Docker Compose: Nginx, Django, PostgreSQL, Redis | Must |
| I1.2 | Cloudflare CDN | Proxy + cache rules on public GET routes | Must |
| I1.3 | WAF rate limiting | 60 req/min per IP on `/v1/` | Must |
| I1.4 | SSL | Full (Strict) between Cloudflare and origin | Must |
| I1.5 | Monitoring | Uptime Kuma + Sentry | Should |

### Platforms (Phase 1)

| Platform | Support |
|----------|---------|
| Android | Yes |
| iOS | Yes |
| Web | Yes |
| Android TV | Phase 2 |
| tvOS | Phase 3 |

---

## Phase 2 — TV + reliability

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F2.1 | Android TV flavor | Leanback launcher, TV-optimized layout | Must |
| F2.2 | D-pad navigation | FocusTraversalGroup, remote-friendly channel switcher | Must |
| F2.3 | Stream health checks | Cron job probes stream_url every 1–2 min during live events | Must |
| F2.4 | Auto-deactivate dead streams | Set is_active=False after N consecutive failures | Must |
| F2.5 | Admin alerts | Email/Slack when streams fail | Should |
| F2.6 | Cache tuning | Adjust Cloudflare + Redis TTL based on match-day traffic | Should |
| F2.7 | Upgrade alerts | CPU/RAM thresholds trigger KVM8 upgrade consideration | Could |

---

## Phase 3 — polish

| ID | Feature | Description | Priority |
|----|---------|-------------|----------|
| F3.1 | tvOS | Evaluate Flutter tvOS vs thin native AVPlayer wrapper | Should |
| F3.2 | Picture-in-Picture | PiP on Android/iOS | Could |
| F3.3 | Favorites | Local storage favorites (no account) | Could |
| F3.4 | Match start notifications | Push via device token (no login) | Could |
| F3.5 | Background audio | Continue audio when app backgrounded | Could |

---

## Out of scope (v1–v3)

- User accounts / login
- Payment / subscription
- Video hosting or transcoding on your VPS
- Live chat or comments
- In-app match statistics / scores API
- Social sharing (can add later)

---

## Success criteria (v1)

- [ ] User sees live matches within 2s on good network
- [ ] Playback starts on default channel within 3–5s of tapping a match
- [ ] Channel switch works without app restart
- [ ] Admin can add a match + 3 channels without code deploy
- [ ] API survives 10k simulated concurrent users with p95 < 300ms on cached routes

---

## Implementation checklist

- [x] Flutter app: go_router, Riverpod, media_kit under `app/`
- [ ] Django + DRF backend with Match/Channel models
- [x] MatchListPage with filters, pagination, pull-to-refresh
- [x] PlayerPage with HLS playback + channel switcher
- [ ] Django Admin with inlines, filters, bulk actions
- [ ] Deploy KVM4 + Cloudflare
- [ ] Android TV flavor
- [ ] k6 load test

## Related docs

- [Architecture](./architecture.md)
- [Best practices](./best-practices.md)
