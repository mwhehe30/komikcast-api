import asyncio
from curl_cffi.requests import AsyncSession
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
        print("Fetching genres...")
        r = await s.get(f"{BASE}/genres", impersonate="chrome124", headers=HEADERS)
        print(f"Genres Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                print(f"Data is dict. Keys: {list(data.keys())}")
                if "data" in data:
                    items = data["data"]
                    print(f"Inner data count: {len(items)}")
                    if items:
                        print(f"Sample genre: {json.dumps(items[0], indent=2)}")
            else:
                print(f"Data is {type(data)}. Count: {len(data)}")
                if data:
                    print(f"Sample genre: {json.dumps(data[0], indent=2)}")
        
        print("\nFetching search 'solo'...")
        # filter=title=like="solo",nativeTitle=like="solo"
        filter_str = 'title=like="solo",nativeTitle=like="solo"'
        url = f"{BASE}/series?take=5&filter={filter_str}"
        r = await s.get(url, impersonate="chrome124", headers=HEADERS)
        print(f"Search Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            print(f"Search count: {len(items)}")
            if items:
                print(f"Sample item keys: {list(items[0].keys())}")
                print(f"Sample item title: {items[0].get('title')}")

if __name__ == "__main__":
    asyncio.run(main())
