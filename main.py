from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from curl_cffi.requests import AsyncSession
from typing import Any
from urllib.parse import quote

import asyncio
import os
import time

app = FastAPI()

# ====================================
# ENABLE PUBLIC CORS
# ====================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================
# CONFIG
# ====================================

DEFAULT_SOURCE = "https://be.komikcast.cc"


def get_source_bases() -> list[str]:
    """Ordered source base URLs. Direct API is always kept as final fallback."""
    bases: list[str] = []
    seen: set[str] = set()

    def add(url: str | None) -> None:
        if not url:
            return
        normalized = url.strip().rstrip("/")
        if normalized and normalized not in seen:
            seen.add(normalized)
            bases.append(normalized)

    add(os.getenv("SOURCE_BASE_URL") or os.getenv("PROXY_BASE_URL"))

    for part in os.getenv("SOURCE_FALLBACK_URLS", DEFAULT_SOURCE).split(","):
        add(part)

    add(DEFAULT_SOURCE)

    worker_bases = [base for base in bases if "workers.dev" in base]
    regular_bases = [base for base in bases if "workers.dev" not in base]
    return regular_bases + worker_bases


SOURCE_BASES = get_source_bases()
BASE = SOURCE_BASES[0]
SOURCE_WEB_URL = os.getenv("SOURCE_WEB_URL", "https://v3.komikcast.fit").rstrip("/")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
SOURCE_RETRYABLE_STATUSES = {403, 429, 502, 503, 504}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,id;q=0.8",
    "origin": SOURCE_WEB_URL,
    "referer": f"{SOURCE_WEB_URL}/",
    "x-requested-with": "XMLHttpRequest",
}

SOURCE_PAGE_SIZE = 20
SOURCE_TIMEOUT_SECONDS = float(os.getenv("SOURCE_TIMEOUT_SECONDS", "30"))
SOURCE_MAX_CONCURRENCY = int(os.getenv("SOURCE_MAX_CONCURRENCY", "2"))
SOURCE_MIN_INTERVAL_SECONDS = float(os.getenv("SOURCE_MIN_INTERVAL_SECONDS", "0.5"))

HEALTH_CACHE_TTL = int(os.getenv("HEALTH_CACHE_TTL_SECONDS", "60"))
LIST_CACHE_TTL = int(os.getenv("LIST_CACHE_TTL_SECONDS", os.getenv("CACHE_TTL_SECONDS", "120")))
SERIES_DETAIL_CACHE_TTL = int(os.getenv("SERIES_DETAIL_CACHE_TTL_SECONDS", "300"))
CHAPTER_LIST_CACHE_TTL = int(os.getenv("CHAPTER_LIST_CACHE_TTL_SECONDS", "120"))
GENRES_CACHE_TTL = int(os.getenv("GENRES_CACHE_TTL_SECONDS", "86400"))
CHAPTER_CONTENT_CACHE_TTL = int(
    os.getenv("CHAPTER_CONTENT_CACHE_TTL_SECONDS", os.getenv("CHAPTER_CACHE_TTL_SECONDS", "604800"))
)
IMAGE_CACHE_SECONDS = int(os.getenv("IMAGE_CACHE_SECONDS", "604800"))

_source_session: AsyncSession | None = None
_source_semaphore = asyncio.Semaphore(SOURCE_MAX_CONCURRENCY)
_source_rate_lock = asyncio.Lock()
_source_last_request_at = 0.0
_json_cache: dict[str, tuple[float, Any]] = {}
_stale_cache: dict[str, Any] = {}
_json_inflight: dict[str, asyncio.Future] = {}
_json_cache_lock = asyncio.Lock()
_last_successful_base: str | None = None


# ====================================
# PROXY URL HELPER
# ====================================

def get_base_url(request: Request) -> str:
    """Get base URL dari request untuk generate proxy URL"""
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL.rstrip("/")

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")

    return str(request.base_url).rstrip("/")


def proxify_url(image_url: str, base_url: str) -> str:
    """Convert image URL ke proxy URL"""
    if not image_url or not isinstance(image_url, str):
        return image_url
    
    # Cek apakah URL gambar (common image domains/extensions)
    if any(domain in image_url.lower() for domain in ["imgkc", "komikcast", "cdn", "minio"]) or \
       any(image_url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        return f"{base_url}/proxy?url={quote(image_url)}"
    
    return image_url


def proxify_images(obj: Any, base_url: str):
    """Recursively convert semua image URL ke proxy URL"""
    
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            # Keys yang contain image URLs (termasuk coverImage, backgroundImage, dataImages)
            if k in ["image", "images", "thumbnail", "cover", "poster", "avatar", "photo", "picture", "img", "src",
                     "coverImage", "backgroundImage", "dataImages"]:
                if isinstance(v, str):
                    result[k] = proxify_url(v, base_url)
                elif isinstance(v, list):
                    result[k] = [proxify_url(item, base_url) if isinstance(item, str) else proxify_images(item, base_url) for item in v]
                elif isinstance(v, dict):
                    # Handle dataImages yang berupa object dengan key numerik
                    result[k] = {key: proxify_url(val, base_url) if isinstance(val, str) else proxify_images(val, base_url) 
                                for key, val in v.items()}
                else:
                    result[k] = proxify_images(v, base_url)
            else:
                result[k] = proxify_images(v, base_url)
        return result
    
    elif isinstance(obj, list):
        return [proxify_images(item, base_url) for item in obj]
    
    return obj


# ====================================
# CLEAN FUNCTION
# ====================================

def clean(obj: Any):

    if isinstance(obj, dict):

        result = {}

        for k, v in obj.items():

            if v is None:
                continue

            if v == "":
                continue

            result[k] = clean(v)

        return result

    elif isinstance(obj, list):

        return [clean(x) for x in obj]

    return obj


# ====================================
# FLATTEN ITEM HELPER
# ====================================

def flatten_item(item: dict) -> dict:
    """
    The source API wraps all fields inside a nested 'data' key:
      { "id": 1, "data": { "title": "...", "slug": "..." }, "chapters": [...] }
    This merges 'data' into the top level so consumers get a flat object.
    Top-level keys (id, createdAt, updatedAt, chapters, etc.) take precedence.
    """
    if not isinstance(item, dict):
        return item
    nested = item.get("data")
    if not isinstance(nested, dict):
        return item
    merged = {**nested}
    for k, v in item.items():
        merged[k] = v
    return merged


def flatten_items(items: list) -> list:
    return [flatten_item(i) for i in items]


# ====================================
# FETCH FUNCTION
# ====================================

async def get_source_session() -> AsyncSession:
    global _source_session

    if _source_session is None:
        _source_session = AsyncSession()
    return _source_session


@app.on_event("shutdown")
async def close_source_session():
    global _source_session

    if _source_session is not None:
        await _source_session.close()
        _source_session = None


async def wait_for_source_slot():
    global _source_last_request_at

    async with _source_rate_lock:
        elapsed = time.monotonic() - _source_last_request_at
        if elapsed < SOURCE_MIN_INTERVAL_SECONDS:
            await asyncio.sleep(SOURCE_MIN_INTERVAL_SECONDS - elapsed)
        _source_last_request_at = time.monotonic()


def get_cached_json(url: str) -> Any | None:
    cached = _json_cache.get(url)
    if not cached:
        return None

    expires_at, data = cached
    if expires_at <= time.monotonic():
        _json_cache.pop(url, None)
        return None

    return data


def source_error_detail(status_code: int, base_url: str) -> str:
    if status_code == 403:
        return (
            f"Source blocked requests from {base_url} (403). "
            "Trying fallback sources if configured."
        )
    if status_code == 429:
        return (
            f"Source rate-limited requests from {base_url} (429). "
            "Trying fallback sources if configured."
        )
    return f"Source returned HTTP {status_code} from {base_url}"


async def fetch_url_once(url: str):
    """Fetch JSON from one source URL with shared session and conservative pacing."""
    session = await get_source_session()
    r = None

    async with _source_semaphore:
        for attempt in range(3):
            await wait_for_source_slot()
            r = await session.get(
                url,
                impersonate="chrome124",
                headers=HEADERS,
                timeout=SOURCE_TIMEOUT_SECONDS,
            )
            if r.status_code != 429 or attempt == 2:
                break

            retry_after = r.headers.get("retry-after", "2")
            try:
                delay = min(float(retry_after), 5)
            except ValueError:
                delay = 2
            await asyncio.sleep(delay)

    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=source_error_detail(r.status_code, url),
        )

    return r.json()


async def fetch_uncached(path: str):
    """Fetch JSON from source, failing over across configured base URLs."""
    global _last_successful_base

    if not path.startswith("/"):
        path = f"/{path}"

    last_error: HTTPException | None = None

    for base in get_source_bases():
        url = f"{base}{path}"
        try:
            data = await fetch_url_once(url)
            _last_successful_base = base
            return data
        except HTTPException as e:
            if e.status_code in SOURCE_RETRYABLE_STATUSES:
                last_error = e
                continue
            raise
        except Exception as e:
            last_error = HTTPException(status_code=500, detail=f"Fetch error: {str(e)}")
            continue

    if last_error is not None:
        raise last_error

    raise HTTPException(status_code=503, detail="All Komikcast sources failed")


async def fetch(path: str, ttl: int = LIST_CACHE_TTL, cache_key: str | None = None):
    """Fetch JSON from source, cache it, and coalesce duplicate in-flight calls."""
    if not path.startswith("/"):
        path = f"/{path}"

    cache_key = cache_key or path

    if ttl > 0:
        cached = get_cached_json(cache_key)
        if cached is not None:
            return cached

    async with _json_cache_lock:
        if ttl > 0:
            cached = get_cached_json(cache_key)
            if cached is not None:
                return cached

        future = _json_inflight.get(cache_key)
        if future is None:
            future = asyncio.get_running_loop().create_future()
            future.add_done_callback(
                lambda f: f.exception() if not f.cancelled() else None
            )
            _json_inflight[cache_key] = future
            owner = True
        else:
            owner = False

    if not owner:
        return await future

    try:
        data = await fetch_uncached(path)
        if ttl > 0:
            _json_cache[cache_key] = (time.monotonic() + ttl, data)
        _stale_cache[cache_key] = data
        future.set_result(data)
        return data
    except Exception as e:
        stale = _stale_cache.get(cache_key)
        if stale is not None:
            future.set_result(stale)
            return stale
        future.set_exception(e)
        raise
    finally:
        async with _json_cache_lock:
            _json_inflight.pop(cache_key, None)


# ====================================
# ROOT
# ====================================

@app.get("/")
async def root(response: Response):
    health_path = "/genres"
    routes = [
        "/",
        "/series",
        "/genres",
        "/series/{slug}",
        "/series/{slug}/chapters",
        "/series/{slug}/chapters/{chapter}",
        "/proxy",
    ]

    try:
        await fetch(
            health_path,
            ttl=HEALTH_CACHE_TTL,
            cache_key=f"health:{health_path}",
        )
        active_base = _last_successful_base or BASE
        source = {
            "status": "ok",
            "baseUrl": active_base,
            "configuredBases": get_source_bases(),
        }
        status = "ok"
        status_code = 200
        message = "Komikcast API is running"
    except HTTPException as e:
        status = "error"
        status_code = 503
        response.status_code = status_code
        source = {
            "status": "error",
            "baseUrl": BASE,
            "configuredBases": get_source_bases(),
            "httpStatus": e.status_code,
            "detail": e.detail,
        }
        message = "Komikcast source is not reachable"
    except Exception as e:
        status = "error"
        status_code = 503
        response.status_code = status_code
        source = {
            "status": "error",
            "baseUrl": BASE,
            "configuredBases": get_source_bases(),
            "detail": str(e),
        }
        message = "Komikcast API health check failed"

    return {
        "status": status,
        "statusCode": status_code,
        "message": message,
        "source": source,
        "routes": routes,
    }


# ====================================
# SERIES LIST (OFFSET PAGINATION)
# ====================================

@app.get("/series")
async def series(
    request: Request,
    response: Response,
    offset: int = Query(0, ge=0),
    take: int = Query(20, ge=1, le=100),
    keyword: str = Query(None),
    genres: list[str] = Query(None),
    status: str = Query(None),
    type: str = Query(None),
    sort: str = Query("latest"),
    sortOrder: str = Query("desc")
):

    # hitung page awal
    start_page = (offset // SOURCE_PAGE_SIZE) + 1

    # index mulai di page tersebut
    start_index = offset % SOURCE_PAGE_SIZE

    results = []

    page = start_page
    
    # -------------------------------------------------------
    # Build RSQL filter string
    # The source API uses RSQL syntax:
    #   comma (,)     = OR
    #   semicolon (;) = AND  (avoid — causes DB pool timeout)
    # -------------------------------------------------------
    or_filters = []   # joined with comma  → OR
    and_filters = []  # joined with semicolon → AND (use sparingly)

    if keyword:
        # OR: match title OR nativeTitle
        kw = keyword.replace('"', '')  # sanitise
        or_filters.append(f'title=like="{kw}"')
        or_filters.append(f'nativeTitle=like="{kw}"')

    if genres:
        # API works with name-based filter; genre-ID filter returns 0 results.
        # All genre names must be quoted strings in the in-list.
        # Multiple genres → OR semantics (in= already handles that).
        quoted = [f'"{g.strip()}"' for g in genres if g.strip()]
        if quoted:
            and_filters.append(f'genres.name=in=[{",".join(quoted)}]')

    if status:
        and_filters.append(f'status=eq="{status}"')

    if type:
        and_filters.append(f'type=eq="{type}"')

    # Combine: (title OR nativeTitle) AND genre AND status AND type
    # Build: or-block first, then wrap everything with and-block
    filter_parts = []
    if or_filters:
        filter_parts.append(",".join(or_filters))  # OR group
    filter_parts.extend(and_filters)               # AND conditions

    # Join all parts with semicolon (AND), but only use semicolons for
    # the outer AND joins — inner OR group is already comma-joined.
    filter_query = ";".join(filter_parts) if filter_parts else None

    while len(results) < take:

        path = (
            f"/series"
            f"?take={SOURCE_PAGE_SIZE}"
            f"&takeChapter=3"
            f"&includeMeta=true"
            f"&page={page}"
            f"&sort={sort}"
            f"&sortOrder={sortOrder}"
        )

        if filter_query:
            path += f"&filter={quote(filter_query)}"

        raw = await fetch(path, ttl=LIST_CACHE_TTL)

        cleaned = clean(raw)

        items = flatten_items(cleaned.get("data", []))

        if not items:
            break

        # slice sesuai offset lokal
        if page == start_page:
            items = items[start_index:]

        results.extend(items)

        page += 1

        if page > 1000:
            break

    # potong sesuai take
    results = results[:take]

    # Proxify semua image URLs
    base_url = get_base_url(request)
    results = proxify_images(results, base_url)
    response.headers["Cache-Control"] = (
        f"public, s-maxage={LIST_CACHE_TTL}, stale-while-revalidate={LIST_CACHE_TTL * 2}"
    )

    return {
        "status": 200,
        "offset": offset,
        "take": take,
        "count": len(results),
        "hasMore": len(results) == take,
        "data": results
    }


# ====================================
# GENRES
# ====================================

@app.get("/genres")
async def genres(request: Request, response: Response):

    raw = await fetch("/genres", ttl=GENRES_CACHE_TTL)

    # Source returns: {"data": [{"id": 1, "data": {"name": "..."}}, ...]}
    # Use flatten_item to merge nested 'data' into top level.
    items = flatten_items(raw.get("data", []))
    result = clean(items)

    # Proxify images (just in case there are icons)
    base_url = get_base_url(request)
    result = proxify_images(result, base_url)
    response.headers["Cache-Control"] = (
        f"public, s-maxage={GENRES_CACHE_TTL}, stale-while-revalidate={GENRES_CACHE_TTL}"
    )

    return {
        "status": 200,
        "data": result
    }


# ====================================
# SERIES DETAIL
# ====================================

@app.get("/series/{slug}")
async def series_detail(request: Request, response: Response, slug: str):

    raw = await fetch(f"/series/{slug}", ttl=SERIES_DETAIL_CACHE_TTL)
    
    cleaned = clean(raw)
    
    # Proxify semua image URLs
    base_url = get_base_url(request)
    cleaned = proxify_images(cleaned, base_url)
    response.headers["Cache-Control"] = (
        f"public, s-maxage={SERIES_DETAIL_CACHE_TTL}, stale-while-revalidate={SERIES_DETAIL_CACHE_TTL * 2}"
    )

    return cleaned


# ====================================
# CHAPTER LIST
# ====================================

@app.get("/series/{slug}/chapters")
async def chapters(request: Request, response: Response, slug: str):

    raw = await fetch(f"/series/{slug}/chapters", ttl=CHAPTER_LIST_CACHE_TTL)
    
    cleaned = clean(raw)
    
    # Proxify semua image URLs
    base_url = get_base_url(request)
    cleaned = proxify_images(cleaned, base_url)
    response.headers["Cache-Control"] = (
        f"public, s-maxage={CHAPTER_LIST_CACHE_TTL}, stale-while-revalidate={CHAPTER_LIST_CACHE_TTL * 2}"
    )

    return cleaned


# ====================================
# CHAPTER DETAIL
# ====================================

@app.get("/series/{slug}/chapters/{chapter}")
async def chapter_detail(
    request: Request,
    response: Response,
    slug: str,
    chapter: str,
):

    raw = await fetch(
        f"/series/{slug}/chapters/{chapter}",
        ttl=CHAPTER_CONTENT_CACHE_TTL,
    )
    
    cleaned = clean(raw)
    
    # Proxify semua image URLs
    base_url = get_base_url(request)
    cleaned = proxify_images(cleaned, base_url)
    response.headers["Cache-Control"] = (
        f"public, s-maxage={CHAPTER_CONTENT_CACHE_TTL}, stale-while-revalidate={CHAPTER_CONTENT_CACHE_TTL}"
    )

    return cleaned


# ====================================
# IMAGE PROXY
# ====================================

@app.get("/proxy")
async def proxy_image(
    url: str = Query(..., description="Image URL to proxy"),
    referer: str = Query(None, description="Custom referer header")
):
    """
    Proxy endpoint untuk bypass 403 error pada gambar.
    Menambahkan header Referer dan User-Agent yang sesuai.
    """
    
    # Validasi URL
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter required")
    
    # Validasi URL aman (block localhost/private IP)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else ""
        
        # Block private addresses
        private_patterns = [
            "127.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
            "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
            "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
            "192.168.", "169.254.", "localhost", "0."
        ]
        
        if any(hostname.startswith(p) for p in private_patterns):
            raise HTTPException(
                status_code=400,
                detail="Access to internal networks is prohibited"
            )
        
        if parsed.scheme not in ["http", "https"]:
            raise HTTPException(status_code=400, detail="Invalid URL scheme")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")
    
    # Set referer default - gunakan referer yang sama dengan Weebs_Scraper
    if not referer:
        # Default referer yang work untuk komikcast images
        referer = SOURCE_WEB_URL
    
    # Fetch gambar dengan header yang sesuai
    try:
        session = await get_source_session()
        async with _source_semaphore:
            await wait_for_source_slot()
            response = await session.get(
                url,
                impersonate="chrome124",
                headers={
                    "Referer": referer,
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive",
                },
                timeout=SOURCE_TIMEOUT_SECONDS
            )
            
            if response.status_code != 200:
                # Log error untuk debugging
                error_detail = f"Status {response.status_code}"
                if response.status_code == 403:
                    error_detail = f"403 Forbidden - URL: {url[:100]}, Referer: {referer}"
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
            # Stream response
            return StreamingResponse(
                iter([response.content]),
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={
                    "Cache-Control": f"public, max-age={IMAGE_CACHE_SECONDS}",
                    "Access-Control-Allow-Origin": "*"
                }
            )
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


# ====================================
# RUN
# ====================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


