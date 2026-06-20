# Komikcast API

## Deployment

The Komikcast source currently blocks Vercel and Cloudflare Worker egress
IPs. `SOURCE_BASE_URL` must point to a reverse proxy hosted on a network that
can access `https://be.komikcast.cc`.

```text
SOURCE_BASE_URL=https://your-source-proxy.example.com
```

Do not use a `workers.dev` URL for this variable: the source currently returns
HTTP 429 with `Your IP has been permanently blocked.` for Cloudflare Worker
egress.

The Komikcast frontend referer/origin defaults to `https://v3.komikcast.fit`.
Override it only when the source frontend domain changes:

```text
SOURCE_WEB_URL=https://v3.komikcast.fit
```
