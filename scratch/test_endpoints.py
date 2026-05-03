import httpx
import asyncio

async def test_endpoint(url, name):
    print(f"Testing {name}: {url}")
    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "referer": "https://v2.komikcast.fit/",
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
    }
    
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
        try:
            r = await client.get(url)
            print(f"[{name}] Status: {r.status_code}")
            if r.status_code == 200:
                print(f"[{name}] Success!")
        except Exception as e:
            print(f"[{name}] Failed: {e}")

async def main():
    endpoints = [
        ("https://be.komikcast.cc/series", "Current Backend"),
        ("https://komikcast.cc/series", "Root Domain"),
        ("https://v2.komikcast.fit/series", "V2 Domain"),
    ]
    for url, name in endpoints:
        await test_endpoint(url, name)

if __name__ == "__main__":
    asyncio.run(main())
