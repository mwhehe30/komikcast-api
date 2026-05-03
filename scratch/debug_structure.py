"""
Debug: check actual structure of items returned.
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

async def main():
    async with AsyncSession() as s:
        # Check structure of a series item
        r = await s.get(f"{BASE}/series?take=1&takeChapter=1&page=1&sort=latest&sortOrder=desc", 
                        impersonate="chrome124", headers=HEADERS, timeout=30)
        print(f"Status: {r.status_code}")
        data = r.json()
        print(f"Top-level keys: {list(data.keys())}")
        items = data.get("data", [])
        if items:
            item = items[0]
            print(f"\nItem keys: {list(item.keys())}")
            print(f"\nFull item: {json.dumps(item, indent=2, default=str)[:2000]}")

        # Check genre item structure too
        r2 = await s.get(f"{BASE}/genres", impersonate="chrome124", headers=HEADERS, timeout=30)
        gdata = r2.json()
        gitems = gdata.get("data", [])
        if gitems:
            print(f"\nGenre item keys: {list(gitems[0].keys())}")
            print(f"Genre item: {json.dumps(gitems[0], indent=2, default=str)}")

        # Check search results
        f1 = 'title=like="solo",nativeTitle=like="solo"'
        r3 = await s.get(f"{BASE}/series?take=2&takeChapter=1&page=1&filter={quote(f1)}",
                         impersonate="chrome124", headers=HEADERS, timeout=30)
        sdata = r3.json()
        sitems = sdata.get("data", [])
        if sitems:
            print(f"\nSearch result item keys: {list(sitems[0].keys())}")
            print(f"Search item: {json.dumps(sitems[0], indent=2, default=str)[:2000]}")

if __name__ == "__main__":
    asyncio.run(main())
