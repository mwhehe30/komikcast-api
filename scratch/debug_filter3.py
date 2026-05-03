"""
Test the exact URLs being built by the fixed main.py filter logic.
"""
import asyncio
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,id;q=0.8",
    "origin": "https://v2.komikcast.fit",
    "referer": "https://v2.komikcast.fit/",
    "x-requested-with": "XMLHttpRequest",
}

BASE = "https://be.komikcast.cc"

def build_filter(keyword=None, genres=None, status=None, type_=None):
    or_filters = []
    and_filters = []

    if keyword:
        kw = keyword.replace('"', '')
        or_filters.append(f'title=like="{kw}"')
        or_filters.append(f'nativeTitle=like="{kw}"')

    if genres:
        quoted = [f'"{g.strip()}"' for g in genres if g.strip()]
        if quoted:
            and_filters.append(f'genres.name=in=[{",".join(quoted)}]')

    if status:
        and_filters.append(f'status=eq="{status}"')

    if type_:
        and_filters.append(f'type=eq="{type_}"')

    filter_parts = []
    if or_filters:
        filter_parts.append(",".join(or_filters))
    filter_parts.extend(and_filters)

    return ";".join(filter_parts) if filter_parts else None

async def test(session, label, keyword=None, genres=None, status=None, type_=None):
    f = build_filter(keyword=keyword, genres=genres, status=status, type_=type_)
    url = f"{BASE}/series?take=3&takeChapter=1&page=1&sort=latest&sortOrder=desc"
    if f:
        url += f"&filter={quote(f)}"
    print(f"\n[{label}]")
    print(f"  Filter: {f}")
    print(f"  Encoded: {quote(f) if f else 'none'}")
    try:
        r = await session.get(url, impersonate="chrome124", headers=HEADERS, timeout=30)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            print(f"  Count: {len(items)}")
            if items:
                item = items[0]
                print(f"  Keys: {list(item.keys())}")
                inner = item.get("data", {})
                print(f"  Title: {inner.get('title') if isinstance(inner, dict) else '?'}")
        else:
            print(f"  Response: {r.text[:400]}")
    except Exception as e:
        print(f"  ERROR: {e}")

async def main():
    async with AsyncSession() as s:
        await test(s, "keyword=solo", keyword="solo")
        await test(s, "genre=Action", genres=["Action"])
        await test(s, "keyword=solo + genre=Action", keyword="solo", genres=["Action"])
        await test(s, "status=ongoing", status="ongoing")
        await test(s, "type=Manhwa", type_="Manhwa")
        await test(s, "genre=Action + status=ongoing", genres=["Action"], status="ongoing")

if __name__ == "__main__":
    asyncio.run(main())
