import httpx
import asyncio

async def test_domain(domain):
    print(f"Testing {domain}...")
    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "origin": "https://v2.komikcast.fit",
        "referer": "https://v2.komikcast.fit/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    }
    
    url = f"https://{domain}/series?preset=rilisan_terbaru&type=project&take=2&takeChapter=3&page=1"
    
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        try:
            r = await client.get(url)
            print(f"[{domain}] Status: {r.status_code}")
            return r.status_code == 200
        except Exception as e:
            print(f"[{domain}] Failed: {e}")
            return False

async def main():
    domains = ["be.komikcast.cc", "be.komikcast.fit", "be.komikcast.me", "be.komikcast.site", "api.komikcast.fit"]
    for d in domains:
        await test_domain(d)

if __name__ == "__main__":
    asyncio.run(main())
