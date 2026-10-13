import time
import requests

# URL of your local background server
URL = "http://127.0.0.1:8000/generate"

# Simple test payload
payload = {
    "prompt": "Write a 3-sentence summary of why Apple Silicon is efficient.",
    "max_tokens": 150
    }

print("Pinging local Mellum 2.1 background server...")
start_time = time.time()

try:
    response = requests.post(URL, json=payload)
    
    if response.status_code == 200:
        elapsed = time.time() - start_time
        print(f"Success! Response received in {elapsed:.2f} seconds:\n")
        print("-" * 50)
        print(response.json().get("response"))
        print("-" * 50)
    else:
        print(f"❌ Server returned an error code: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("❌ Error: Could not connect to the server.")
    print("Check if the background service is running via: 'ps aux | grep run_mellum.py'")
