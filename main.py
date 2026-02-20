from fastapi import FastAPI, HTTPException, Query
import httpx
from typing import Any

app = FastAPI(
    title="Komik API",
    version="1.0.0"
)

BASE = "https://be.komikcast.cc"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "Referer": "https://v1.komikcast.fit/"
}

client = httpx.AsyncClient(
    headers=HEADERS,
    timeout=30
)

# =====================================================
# CLEAN FUNCTION (remove null, "", empty object)
# =====================================================

def clean(obj: Any):

    if isinstance(obj, dict):

        result = {}

        for k, v in obj.items():

            if v is None:
                continue

            if v == "":
                continue

            if v == {}:
                continue

            if v == []:
                continue

            result[k] = clean(v)

        return result

    elif isinstance(obj, list):

        return [
            clean(x)
            for x in obj
            if x is not None and x != "" and x != {}
        ]

    return obj


# =====================================================
# FETCH FUNCTION
# =====================================================

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


# =====================================================
# TRANSFORM SERIES LIST (infinite scroll)
# =====================================================

def transform_series_list(raw):

    result = []

    for item in raw["data"]:

        d = item["data"]

        result.append(clean({

            "id": item["id"],

            "title": d.get("title"),

            "slug": d.get("slug"),

            "cover": d.get("coverImage"),

            "rating": d.get("rating"),

            "status": d.get("status"),

            "type": d.get("type"),

            "views": item["dataMetadata"]["totalViewsComputed"]

        }))

    return result


# =====================================================
# TRANSFORM SERIES DETAIL
# =====================================================

def transform_series_detail(raw):

    d = raw["data"]
    meta = d["data"]

    return clean({

        "id": d["id"],

        "title": meta.get("title"),

        "slug": meta.get("slug"),

        "cover": meta.get("coverImage"),

        "background": meta.get("backgroundImage"),

        "rating": meta.get("rating"),

        "status": meta.get("status"),

        "author": meta.get("author"),

        "format": meta.get("format"),

        "synopsis": meta.get("synopsis"),

        "genres": [
            g["data"]["name"]
            for g in meta.get("genres", [])
        ],

        "views": d["dataMetadata"]["totalViewsComputed"]

    })


# =====================================================
# TRANSFORM CHAPTER LIST
# =====================================================

def transform_chapters(raw):

    result = []

    for ch in raw["data"]:

        meta = ch["data"]

        result.append(clean({

            "id": ch["id"],

            "chapter": meta.get("index"),

            "views": ch["views"]["total"],

            "createdAt": ch["createdAt"]

        }))

    return result


# =====================================================
# TRANSFORM CHAPTER DETAIL (IMAGES)
# =====================================================

def transform_chapter_detail(raw):

    d = raw["data"]
    meta = d["data"]

    return clean({

        "id": d["id"],

        "chapter": meta.get("index"),

        "images": meta.get("images"),

        "views": d["views"]["total"],

        "createdAt": d["createdAt"]

    })


# =====================================================
# ROUTES
# =====================================================


# Health
@app.get("/")
async def root():

    return {
        "status": "ok"
    }


# Infinite scroll series
@app.get("/series")
async def series(
    page: int = Query(1),
    take: int = Query(20)
):

    url = (
        f"{BASE}/series"
        f"?preset=rilisan_terbaru"
        f"&type=project"
        f"&take={take}"
        f"&takeChapter=3"
        f"&page={page}"
    )

    raw = await fetch(url)

    return {

        "status": 200,

        "page": raw["meta"]["page"],

        "total": raw["meta"]["total"],

        "data": transform_series_list(raw)

    }


# Series detail
@app.get("/series/{slug}")
async def series_detail(slug: str):

    url = f"{BASE}/series/{slug}"

    raw = await fetch(url)

    return {

        "status": 200,

        "data": transform_series_detail(raw)

    }


# Chapter list
@app.get("/series/{slug}/chapters")
async def chapters(slug: str):

    url = f"{BASE}/series/{slug}/chapters"

    raw = await fetch(url)

    return {

        "status": 200,

        "data": transform_chapters(raw)

    }


# Chapter detail (images)
@app.get("/series/{slug}/chapters/{chapter}")
async def chapter_detail(slug: str, chapter: int):

    url = f"{BASE}/series/{slug}/chapters/{chapter}"

    raw = await fetch(url)

    return {

        "status": 200,

        "data": transform_chapter_detail(raw)

    }
