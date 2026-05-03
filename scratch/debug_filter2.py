"""
Debug: test the actual API with a longer timeout and step by step.
Uses the same session repeatedly.
"""
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

async def test(session, label, url):
    try:
        print(f"\n[{label}]")
        print(f"  URL: {url[:200]}")
        r = await session.get(url, impersonate="chrome124", headers=HEADERS, timeout=30)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            print(f"  Count: {len(items)}")
            if items:
                print(f"  First: {items[0].get('title')}")
        else:
            print(f"  Response: {r.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")

async def main():
    async with AsyncSession() as s:
        # Warm up with genres
        print("=== Warming up with genres ===")
        await test(s, "genres", f"{BASE}/genres")
        
        # Baseline (no filter)
        await test(s, "baseline no filter", f"{BASE}/series?take=3&takeChapter=1&page=1&sort=latest&sortOrder=desc")
        
        # With preset
        await test(s, "with preset rilisan_terbaru", f"{BASE}/series?take=3&takeChapter=1&page=1&sort=latest&sortOrder=desc&preset=rilisan_terbaru")

        # Search: OR filter (comma)
        f1 = 'title=like="solo",nativeTitle=like="solo"'
        await test(s, "OR filter search solo", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f1)}")

        # Search: semicolon AND filter
        f2 = 'title=like="solo";nativeTitle=like="solo"'
        await test(s, "AND filter semicolon", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f2)}")

        # Search: just title
        f3 = 'title=like="solo"'
        await test(s, "title only", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f3)}")

        # Search: wildcard
        f4 = 'title=like="%solo%"'
        await test(s, "title wildcard %solo%", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f4)}")

        # Genre by ID=1
        f5 = 'genres.id=in=[1]'
        await test(s, "genre id=1", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f5)}")

        # Genre by name Action
        f6 = 'genres.name=in=["Action"]'
        await test(s, "genre name Action", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f6)}")

        # Status ongoing
        f7 = 'status=eq="Ongoing"'
        await test(s, "status Ongoing", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f7)}")

        # Type Manhwa
        f8 = 'type=eq="Manhwa"'
        await test(s, "type Manhwa", f"{BASE}/series?take=3&takeChapter=1&page=1&filter={quote(f8)}")

if __name__ == "__main__":
    asyncio.run(main())
