"""Quick end-to-end test of the classify → confirm → save pipeline."""
import httpx

BASE = "http://127.0.0.1:8000"

users = httpx.get(f"{BASE}/api/users/").json()
sid = users[0]["id"]
print(f"Speaker: {users[0]['name']}")

# Classify a Catalan baby entry
r = httpx.post(f"{BASE}/api/voice/classify", json={
    "text": "La nena ha menjat a les 4 del mati i ha fet pipi",
    "speaker_id": sid,
    "language_hint": "ca",
}, timeout=30)
data = r.json()
vid = data["voice_entry_id"]
print(f"Classified: {data['category']} / {data['type']}")
print(f"Extracted: {data.get('extracted_data')}")

# Confirm
r2 = httpx.post(f"{BASE}/api/voice/confirm?voice_entry_id={vid}")
print(f"Confirmed: {r2.json()}")

# Check baby logs
r3 = httpx.get(f"{BASE}/api/baby/logs")
logs = r3.json()
latest = logs[0]
print(f"Baby log: feed_time={latest['feed_time']}, diaper={latest['diaper_count']}x{latest['diaper_type']}")

# Check today feed
r4 = httpx.get(f"{BASE}/api/voice/today")
feed = r4.json()
print(f"Today feed: {len(feed)} entries")
