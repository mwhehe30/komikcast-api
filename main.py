from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Any, List, Dict, Optional, Set

app = FastAPI()

# ====================================
# CORS
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
    "referer": "https://v1.komikcast.fit/",
}

SOURCE_PAGE_SIZE = 20


# ====================================
# CLEAN
# ====================================

def clean(obj: Any):

    if isinstance(obj, dict):

        result = {}

        for k, v in obj.items():

            if v is None or v == "":
                continue

            result[k] = clean(v)

        return result

    elif isinstance(obj, list):

        return [clean(x) for x in obj]

    return obj


# ====================================
# FETCH (VERCEL SAFE)
# ====================================

async def fetch(url: str):

    try:

        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=30.0
        ) as client:

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
        "status": "ok",
        "message": "Komik API Cursor Pagination Ready"
    }


# ====================================
# CURSOR PAGINATION
# ====================================

@app.get("/series")
async def series(
    cursor: Optional[str] = None,
    take: int = Query(20, ge=1, le=100)
):

    results: List[Dict] = []
    seen: Set[str] = set()

    found_cursor = cursor is None

    page = 1
    next_cursor = None

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

        for item in items:

            slug = item.get("slug")

            if not slug:
                continue

            # tunggu sampai cursor ditemukan
            if not found_cursor:

                if slug == cursor:
                    found_cursor = True

                continue

            # anti duplicate
            if slug in seen:
                continue

            seen.add(slug)

            results.append(item)

            next_cursor = slug

            if len(results) >= take:
                break

        page += 1

        if page > 1000:
            break

    return {
        "status": 200,
        "count": len(results),
        "cursor": cursor,
        "nextCursor": next_cursor,
        "hasMore": len(results) == take,
        "data": results
    }


# ====================================
# SERIES DETAIL
# ====================================

@app.get("/series/{slug}")
async def series_detail(slug: str):

    raw = await fetch(f"{BASE}/series/{slug}")

    return clean(raw)


# ====================================
# CHAPTER LIST
# ====================================

@app.get("/series/{slug}/chapters")
async def chapters(slug: str):

    raw = await fetch(f"{BASE}/series/{slug}/chapters")

    return clean(raw)


# ====================================
# CHAPTER DETAIL
# ====================================

@app.get("/series/{slug}/chapters/{chapter}")
async def chapter_detail(slug: str, chapter: int):

    raw = await fetch(f"{BASE}/series/{slug}/chapters/{chapter}")

    return clean(raw)
