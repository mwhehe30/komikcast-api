from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Any

app = FastAPI()

# ====================================
# ENABLE CORS (PUBLIC ACCESS)
# ====================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all domains
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

client = httpx.AsyncClient(headers=HEADERS)


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
# ROUTES
# ====================================

@app.get("/")
async def root():

    return {
        "status": "ok",
        "message": "Komik API running"
    }


# SERIES LIST
@app.get("/series")
async def series(
    page: int = Query(1),
    take: int = Query(20)
):

    url = (
        f"{BASE}/series"
        f"?preset=rilisan_terbaru"
        f"&take={take}"
        f"&takeChapter=3"
        f"&page={page}"
    )

    raw = await fetch(url)

    return clean(raw)


# SERIES DETAIL
@app.get("/series/{slug}")
async def series_detail(slug: str):

    url = f"{BASE}/series/{slug}"

    raw = await fetch(url)

    return clean(raw)


# CHAPTER LIST
@app.get("/series/{slug}/chapters")
async def chapters(slug: str):

    url = f"{BASE}/series/{slug}/chapters"

    raw = await fetch(url)

    return clean(raw)


# CHAPTER DETAIL
@app.get("/series/{slug}/chapters/{chapter}")
async def chapter_detail(slug: str, chapter: int):

    url = f"{BASE}/series/{slug}/chapters/{chapter}"

    raw = await fetch(url)

    return clean(raw)
