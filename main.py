from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Any, List, Dict, Set
from contextlib import asynccontextmanager


# ====================================
# LIFESPAN
# ====================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # startup
    app.state.client = httpx.AsyncClient(
        headers={
            "accept": "application/json, text/plain, */*",
            "referer": "https://v1.komikcast.fit/",
        },
        timeout=30.0
    )

    print("HTTP Client started")

    yield

    # shutdown
    await app.state.client.aclose()

    print("HTTP Client closed")


app = FastAPI(lifespan=lifespan)


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


BASE = "https://be.komikcast.cc"
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
# FETCH
# ====================================

async def fetch(app: FastAPI, url: str):

    try:

        client: httpx.AsyncClient = app.state.client

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
# SERIES OFFSET PAGINATION
# ====================================

@app.get("/series")
async def series(
    offset: int = Query(0, ge=0),
    take: int = Query(20, ge=1, le=100)
):

    start_page = (offset // SOURCE_PAGE_SIZE) + 1
    start_index = offset % SOURCE_PAGE_SIZE

    results: List[Dict] = []
    seen: Set[str] = set()

    page = start_page

    while len(results) < take:

        url = (
            f"{BASE}/series"
            f"?preset=rilisan_terbaru"
            f"&take={SOURCE_PAGE_SIZE}"
            f"&takeChapter=3"
            f"&page={page}"
        )

        raw = await fetch(app, url)

        cleaned = clean(raw)

        items = cleaned.get("data", [])

        if not items:
            break

        if page == start_page:
            items = items[start_index:]

        for item in items:

            slug = item.get("slug")

            if not slug or slug in seen:
                continue

            seen.add(slug)

            results.append(item)

            if len(results) >= take:
                break

        page += 1

    return {
        "status": 200,
        "offset": offset,
        "take": take,
        "count": len(results),
        "hasMore": len(results) == take,
        "data": results
    }
