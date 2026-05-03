import httpx

BASE = "http://localhost:8000"

print("=== Search: komisan ===")
r = httpx.get(f"{BASE}/series", params={"keyword": "komisan", "take": 5}, timeout=40)
print(f"Status: {r.status_code}")
d = r.json()
items = d.get("data", [])
print(f"Count: {len(items)}")
for it in items:
    print(f"  - title={it.get('title')} | slug={it.get('slug')} | type={it.get('type')}")

print()
print("=== Genre filter: Action ===")
r2 = httpx.get(f"{BASE}/series", params={"genres": "Action", "take": 3}, timeout=40)
print(f"Status: {r2.status_code}")
d2 = r2.json()
items2 = d2.get("data", [])
print(f"Count: {len(items2)}")
for it in items2:
    print(f"  - title={it.get('title')} | type={it.get('type')} | status={it.get('status')}")

print()
print("=== Genres list ===")
r3 = httpx.get(f"{BASE}/genres", timeout=30)
d3 = r3.json()
genres = d3.get("data", [])
print(f"Count: {len(genres)}")
print(f"First 5: {[(g.get('id'), g.get('name')) for g in genres[:5]]}")
