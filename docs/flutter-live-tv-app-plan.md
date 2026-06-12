# Live TV App — Documentation Index

Master plan split into focused documents. Start with **Architecture**, then **Feature list**, then **Best practices** during implementation.

| Document | Contents |
|----------|----------|
| [architecture.md](./architecture.md) | System design, stack, data model, API, infra (KVM4 + Cloudflare), security, risks |
| [feature-list.md](./feature-list.md) | Phased features (MVP → TV → polish), priorities, success criteria, checklist |
| [best-practices.md](./best-practices.md) | Django, DRF, and Flutter guidelines (sourced from official docs via Context7) |
| [deployment.md](./deployment.md) | KVM4 + Docker + Cloudflare + cron + Telegram production setup |

## Quick reference

- **Client:** Flutter + Riverpod + go_router + media_kit
- **Backend:** Django 5 + DRF + Django Admin
- **Infra:** Hostinger KVM4 + Cloudflare CDN + PostgreSQL + Redis
- **Scale:** ~100k users; video from third-party HLS; metadata API only

## Flutter app

Source: [`app/`](../app/) — run with `cd app && flutter run`.

## Confirmed decisions

- Third-party HLS/m3u8 stream URLs
- Free app, no login
- Platforms: Android, iOS, Web (Phase 1); Android TV (Phase 2); tvOS (Phase 3)
- Django + DRF over alternatives (performance adequate with caching; best admin DX)
