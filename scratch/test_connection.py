from curl_cffi.requests import AsyncSession
import asyncio
import os

async def test_request():
    # Gunakan PROXY_BASE_URL jika ada (sama seperti main.py)
    BASE = os.getenv("PROXY_BASE_URL", "https://be.komikcast.cc").rstrip("/")
    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "origin": "https://v2.komikcast.fit",
        "referer": "https://v2.komikcast.fit/",
        "x-requested-with": "XMLHttpRequest",
    }
    
    url = f"{BASE}/series?preset=rilisan_terbaru&type=project&take=20&takeChapter=3&page=1"
    
    print(f"Testing URL: {url}")
    async with AsyncSession() as s:
        try:
            r = await s.get(url, impersonate="chrome124", headers=HEADERS, timeout=30)
            print(f"Status Code: {r.status_code}")
            if r.status_code == 200:
                print("Success!")
            else:
                print(f"Error Body: {r.text[:200]}...")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_request())
