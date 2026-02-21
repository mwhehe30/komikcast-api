from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Any

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
async def series_detail(slug: str):

    url = f"{BASE}/series/{slug}"

    raw = await fetch(url)

    return clean(raw)


# ====================================
# CHAPTER LIST
# ====================================

@app.get("/series/{slug}/chapters")
async def chapters(slug: str):

    url = f"{BASE}/series/{slug}/chapters"

    raw = await fetch(url)

    return clean(raw)


# ====================================
# CHAPTER DETAIL
# ====================================

@app.get("/series/{slug}/chapters/{chapter}")
async def chapter_detail(slug: str, chapter: int):

    url = f"{BASE}/series/{slug}/chapters/{chapter}"

    raw = await fetch(url)

    return clean(raw)


# ====================================
# SHUTDOWN CLEANUP
# ====================================


