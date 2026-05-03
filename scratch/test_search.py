import httpx
import json

BASE_URL = "http://localhost:8000"

def test_genres():
    print("Testing /genres...")
    try:
        response = httpx.get(f"{BASE_URL}/genres")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            genres = data.get("data", [])
            print(f"Found {len(genres)} genres")
            if genres:
                print(f"First genre: {genres[0].get('name')} (ID: {genres[0].get('id')})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

def test_search(keyword):
    print(f"\nTesting /series?keyword={keyword}...")
    try:
        response = httpx.get(f"{BASE_URL}/series", params={"keyword": keyword, "take": 5}, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", [])
            print(f"Found {len(items)} items")
            for item in items:
                print(f"- {item.get('title')} ({item.get('slug')})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

def test_filter_genre(genre):
    print(f"\nTesting /series?genres={genre}...")
    try:
        response = httpx.get(f"{BASE_URL}/series", params={"genres": [genre], "take": 5}, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", [])
            print(f"Found {len(items)} items")
            for item in items:
                print(f"- {item.get('title')} ({item.get('slug')})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_genres()
    test_search("solo")
    test_filter_genre("Action")
