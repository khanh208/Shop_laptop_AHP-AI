import urllib.request
import urllib.error
import json

url = "http://127.0.0.1:5000/api/recommendations/run"
payload = {
    "usageProfile": "student_it",
    "topN": 5,
    "budget": {"min": 0, "max": 50000000},
    "filters": {"brandCode": "asus"}
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        results = res.get("results", [])
        brands = [r.get("brand") for r in results]
        print("Brands in result:", brands)
        print("Hard filter pass count:", res.get("session", {}).get("hardFilterPassCount"))
except urllib.error.HTTPError as e:
    print("Error:", e.read().decode())
except Exception as e:
    print("Exception:", e)
