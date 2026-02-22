from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
from typing import Any
from urllib.parse import urlparse, quote

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

BASE = "https://be.komikcast.cc"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "Referer": "https://v1.komikcast.fit/"
}

client = httpx.AsyncClient(
    headers=HEADERS,
    timeout=30.0
)

SOURCE_PAGE_SIZE = 20


# ====================================
# PROXY URL HELPER
# ====================================

def get_base_url(request: Request) -> str:
    """Get base URL dari request untuk generate proxy URL"""
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
# FETCH FUNCTION
# ====================================

async def fetch(url: str):

    try:

        r = await client.get(url)

        if r.status_code != 200:

            raise HTTPException(
                status_code=r.status_code,
                detail="Source error"
            )

        return r.json()

    except httpx.RequestError:

        raise HTTPException(
            status_code=500,
            detail="Network error"
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
    take: int = Query(20, ge=1, le=100)
):

    # hitung page awal
    start_page = (offset // SOURCE_PAGE_SIZE) + 1

    # index mulai di page tersebut
    start_index = offset % SOURCE_PAGE_SIZE

    results = []

    page = start_page

    while len(results) < take:

        url = (
            f"{BASE}/series"
            f"?preset=rilisan_terbaru"
            f"&take={SOURCE_PAGE_SIZE}"
            f"&takeChapter=3"
            f"&page={page}"
        )

        raw = await fetch(url)

        cleaned = clean(raw)

        items = cleaned.get("data", [])

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
    
    # Set referer default
    if not referer:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            referer = f"{parsed.scheme}://{parsed.netloc}/"
        except:
            referer = "https://v1.komikcast.fit/"
    
    # Fetch gambar dengan header yang sesuai
    try:
        from fastapi.responses import StreamingResponse
        
        async with httpx.AsyncClient(timeout=30.0) as proxy_client:
            response = await proxy_client.get(
                url,
                headers={
                    "Referer": referer,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                },
                follow_redirects=True
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch image"
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
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


# ====================================
# SHUTDOWN CLEANUP
# ====================================


