# Komikcast API

## Deployment

The Komikcast source currently blocks Vercel and Cloudflare Worker egress
IPs. If your primary proxy is blocked, the API automatically falls back to
`https://be.komikcast.cc`.

```text
SOURCE_BASE_URL=https://your-source-proxy.example.com
SOURCE_FALLBACK_URLS=https://be.komikcast.cc
```

Do not use a `workers.dev` URL as the only source: the source currently returns
HTTP 429 with `Your IP has been permanently blocked.` for Cloudflare Worker
egress. If you already set one on Vercel, remove it or keep it only as the
first entry in `SOURCE_BASE_URL`; the API will retry the direct backend
automatically.

The Komikcast frontend referer/origin defaults to `https://v3.komikcast.fit`.
Override it only when the source frontend domain changes:

```text
SOURCE_WEB_URL=https://v3.komikcast.fit
```

## Source request control

The API keeps a short in-memory cache and coalesces duplicate in-flight
requests so repeated client calls do not always hit the Komikcast source.
Tune these values when deploying:

```text
HEALTH_CACHE_TTL_SECONDS=60
LIST_CACHE_TTL_SECONDS=120
SERIES_DETAIL_CACHE_TTL_SECONDS=300
CHAPTER_LIST_CACHE_TTL_SECONDS=120
GENRES_CACHE_TTL_SECONDS=86400
CHAPTER_CONTENT_CACHE_TTL_SECONDS=604800
IMAGE_CACHE_SECONDS=604800
SOURCE_MAX_CONCURRENCY=2
SOURCE_MIN_INTERVAL_SECONDS=0.5
SOURCE_TIMEOUT_SECONDS=30
```

`CACHE_TTL_SECONDS` and `CHAPTER_CACHE_TTL_SECONDS` are still accepted as
fallbacks for older deployments.
