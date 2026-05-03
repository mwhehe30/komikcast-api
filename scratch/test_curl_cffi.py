from curl_cffi.requests import AsyncSession
import asyncio

async def test_curl_cffi():
    url = "https://be.komikcast.cc/series?preset=rilisan_terbaru&type=project&take=20&takeChapter=3&page=1"
    
    print(f"Testing {url} with curl_cffi...")
    async with AsyncSession() as s:
        try:
            # impersonate chrome
            r = await s.get(url, impersonate="chrome124")
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                print("Success with curl_cffi!")
                # print(r.json())
            else:
                print(f"Failed with status {r.status_code}")
                print(f"Body: {r.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_curl_cffi())
