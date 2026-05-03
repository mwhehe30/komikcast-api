import asyncio
from curl_cffi.requests import AsyncSession
from urllib.parse import quote
import json

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,id;q=0.8",
    "origin": "https://v2.komikcast.fit",
    "referer": "https://v2.komikcast.fit/",
    "x-requested-with": "XMLHttpRequest",
}

BASE = "https://be.komikcast.cc"

async def test(label, url):
    async with AsyncSession() as s:
        r = await s.get(url, impersonate="chrome124", headers=HEADERS, timeout=15)
        print(f"\n[{label}]")
        print(f"  URL: {url[:200]}")
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            print(f"  Count: {len(items)}")
            if items:
                print(f"  First: {items[0].get('title')}")
        else:
            print(f"  Response: {r.text[:300]}")

async def main():
    # 1. No filter (baseline)
    await test("baseline (no filter)", f"{BASE}/series?take=3&takeChapter=1&page=1&sort=latest&sortOrder=desc&preset=rilisan_terbaru&type=project")

    # 2. Search - OR style (comma = OR in RSQL)
    filter_or = 'title=like="solo",nativeTitle=like="solo"'
    await test("search OR style", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_or)}")

    # 3. Search - semicolon = AND in RSQL
    filter_and = 'title=like="solo";nativeTitle=like="solo"'
    await test("search AND style (semicolon)", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_and)}")

    # 4. Search title only
    filter_title = 'title=like="solo"'
    await test("title only search", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_title)}")

    # 5. Search with contains % wildcard
    filter_wild = 'title=like="%solo%"'
    await test("wildcard search", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_wild)}")

    # 6. Genre filter by name (string)
    filter_genre = 'genres.name=in=["Action"]'
    await test("genre by name string", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_genre)}")

    # 7. Genre filter by id numeric
    filter_genre_id = 'genres.id=in=[1]'
    await test("genre by id", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_genre_id)}")

    # 8. Status filter
    filter_status = 'status=eq="ongoing"'
    await test("status filter", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_status)}")

    # 9. Type filter
    filter_type = 'type=eq="Manhwa"'
    await test("type filter", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_type)}")

    # 10. Search title only no quotes
    filter_nq = 'title=like=solo'
    await test("title no quotes", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(filter_nq)}")

    # 11. Using 'search' query param instead of filter
    await test("search query param", f"{BASE}/series?take=3&takeChapter=1&page=1&search=solo")

    # 12. Using 'q' query param
    await test("q query param", f"{BASE}/series?take=3&takeChapter=1&page=1&q=solo")

    # 13. Using 'title' query param
    await test("title query param", f"{BASE}/series?take=3&takeChapter=1&page=1&title=solo")

if __name__ == "__main__":
    asyncio.run(main())
