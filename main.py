from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
from curl_cffi.requests import AsyncSession
from typing import Any
from urllib.parse import urlparse, quote

import os

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

# Gunakan PROXY_BASE_URL jika IP diblock (contoh: Cloudflare Worker)
BASE = os.getenv("PROXY_BASE_URL", "https://be.komikcast.cc").rstrip("/")

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,id;q=0.8",
    "origin": "https://v2.komikcast.fit",
    "referer": "https://v2.komikcast.fit/",
    "x-requested-with": "XMLHttpRequest",
}

SOURCE_PAGE_SIZE = 20


# ====================================
# PROXY URL HELPER
# ====================================

def get_base_url(request: Request) -> str:
    """Get base URL dari request untuk generate proxy URL"""
    # Hardcode base URL dengan http (uncomment untuk pakai)
    return "http://unofficial-komikcast-api.vercel.app"
    
    # base = str(request.base_url).rstrip("/")
    # 
    # # Option 1: Force HTTP via environment variable
    # force_http = os.getenv("FORCE_HTTP_PROXY", "false").lower() == "true"
    # if force_http:
    #     base = base.replace("https://", "http://")
    # 
    # # Option 2: Use custom base URL from environment
    # custom_base = os.getenv("PROXY_BASE_URL")
    # if custom_base:
    #     return custom_base.rstrip("/")
    # 
    # return base


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
        if k != "data":
            merged[k] = v
    return merged


def flatten_items(items: list) -> list:
    return [flatten_item(i) for i in items]


# ====================================
# FETCH FUNCTION
# ====================================

async def fetch(url: str):
    """Fetch JSON from source using curl_cffi to bypass Cloudflare"""
    async with AsyncSession() as s:
        try:
            # Impersonate browser TLS fingerprint
            r = await s.get(url, impersonate="chrome124", headers=HEADERS, timeout=30)

            if r.status_code != 200:
                detail = "Source error"
                if r.status_code == 403:
                    detail = f"Source blocked (403). Cloudflare detected data-center IP. Please set PROXY_BASE_URL."
                
                raise HTTPException(
                    status_code=r.status_code,
                    detail=detail
                )

            return r.json()

        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=500,
                detail=f"Fetch error: {str(e)}"
            )


# ====================================
# ROOT
# ====================================

@app.get("/")
async def root():

    return {
        "status": 200,
        "message": "Komikcast API with offset pagination"
    }


# ====================================
# SERIES LIST (OFFSET PAGINATION)
# ====================================

@app.get("/series")
async def series(
    request: Request,
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

        url = (
            f"{BASE}/series"
            f"?take={SOURCE_PAGE_SIZE}"
            f"&takeChapter=3"
            f"&includeMeta=true"
            f"&page={page}"
            f"&sort={sort}"
            f"&sortOrder={sortOrder}"
        )

        if filter_query:
            url += f"&filter={quote(filter_query)}"

        raw = await fetch(url)

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
async def genres(request: Request):

    url = f"{BASE}/genres"

    raw = await fetch(url)

    # Source returns: {"data": [{"id": 1, "data": {"name": "..."}}, ...]}
    # Use flatten_item to merge nested 'data' into top level.
    items = flatten_items(raw.get("data", []))
    result = clean(items)

    # Proxify images (just in case there are icons)
    base_url = get_base_url(request)
    result = proxify_images(result, base_url)

    return {
        "status": 200,
        "data": result
    }


# ====================================
# SERIES DETAIL
# ====================================

@app.get("/series/{slug}")
async def series_detail(request: Request, slug: str):

    url = f"{BASE}/series/{slug}"

    raw = await fetch(url)
    
    cleaned = clean(raw)
    
    # Proxify semua image URLs
    base_url = get_base_url(request)
    cleaned = proxify_images(cleaned, base_url)

    return cleaned


# ====================================
# CHAPTER LIST
# ====================================

@app.get("/series/{slug}/chapters")
async def chapters(request: Request, slug: str):

    url = f"{BASE}/series/{slug}/chapters"

    raw = await fetch(url)
    
    cleaned = clean(raw)
    
    # Proxify semua image URLs
    base_url = get_base_url(request)
    cleaned = proxify_images(cleaned, base_url)

    return cleaned


# ====================================
# CHAPTER DETAIL
# ====================================

@app.get("/series/{slug}/chapters/{chapter}")
async def chapter_detail(request: Request, slug: str, chapter: str):

    url = f"{BASE}/series/{slug}/chapters/{chapter}"

    raw = await fetch(url)
    
    cleaned = clean(raw)
    
    # Proxify semua image URLs
    base_url = get_base_url(request)
    cleaned = proxify_images(cleaned, base_url)

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
        referer = "https://v2.komikcast.fit"
    
    # Fetch gambar dengan header yang sesuai
    try:
        async with AsyncSession() as s:
            response = await s.get(
                url,
                impersonate="chrome124",
                headers={
                    "Referer": referer,
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive",
                },
                timeout=30
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
                    "Cache-Control": "public, max-age=86400",
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


