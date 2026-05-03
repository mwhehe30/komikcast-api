import httpx
import asyncio
from urllib.parse import urlparse

async def test_request():
    BASE = "https://be.komikcast.cc"
    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,id;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "origin": "https://v2.komikcast.fit",
        "referer": "https://v2.komikcast.fit/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "x-requested-with": "XMLHttpRequest",
    }
    
    url = f"{BASE}/series?preset=rilisan_terbaru&type=project&take=20&takeChapter=3&page=1"
    
    print(f"Testing URL: {url}")
    async with httpx.AsyncClient(headers=HEADERS, timeout=30.0, follow_redirects=True, http2=True) as client:
        try:
            r = await client.get(url)
            print(f"Status Code: {r.status_code}")
            print(f"HTTP Version: {r.http_version}")
            if r.status_code == 200:
                print("Success!")
                # print(f"Sample Data: {r.json()['data'][0]['title'] if r.json().get('data') else 'No data'}")
            else:
                print(f"Error Body: {r.text[:200]}...")
                if r.status_code == 403:
                    print(f"Detail: Source blocked (403). Possible Cloudflare protection on {urlparse(url).netloc}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_request())
