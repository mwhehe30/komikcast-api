from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

BASE = "https://be.komikcast.cc"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "Referer": "https://v1.komikcast.fit/",
}


async def fetch_json(url: str):

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=30
    ) as client:

        res = await client.get(url)

        if res.status_code != 200:
            raise HTTPException(
                status_code=res.status_code,
                detail="Failed to fetch"
            )

        return res.json()


#
# latest series
#
@app.get("/series")
async def series(page: int = 1):

    url = f"{BASE}/series?preset=rilisan_terbaru&take=20&takeChapter=3&page={page}"

    data = await fetch_json(url)

    return data


#
# series detail
#
@app.get("/series/{slug}")
async def detail(slug: str):

    url = f"{BASE}/series/{slug}"

    return await fetch_json(url)


#
# chapters list
#
@app.get("/series/{slug}/chapters")
async def chapters(slug: str):

    url = f"{BASE}/series/{slug}/chapters"

    return await fetch_json(url)


#
# chapter detail (images)
#
@app.get("/series/{slug}/chapters/{chapter}")
async def chapter(slug: str, chapter: int):

    url = f"{BASE}/series/{slug}/chapters/{chapter}"

    return await fetch_json(url)
