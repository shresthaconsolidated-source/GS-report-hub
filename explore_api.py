import requests
import json
import os

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

config = load_config()
TOKEN = config["agentcis_api_token"]
BASE_URL = config["agentcis_base_url"].rstrip('/')

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def explore_endpoint(endpoint):
    print(f"\n--- Exploring {endpoint} ---")
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            
            # Save to file for inspection
            filename = f"dump_{endpoint.replace('/', '_')}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved response to {filename}")
            
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

def explore_endpoint_post(endpoint, payload={}):
    print(f"\n--- Exploring POST {endpoint} ---")
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            
            # Save to file for inspection
            filename = f"dump_{endpoint.replace('/', '_')}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved response to {filename}")
            
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

# Try to find reports or include extra fields
explore_endpoint("api/v2/reports")
explore_endpoint_post("api/v2/reports", {})
explore_endpoint_post("api/v2/clients/list", {"includes": ["visa_type", "visa_expiry_date"]})
explore_endpoint_post("api/v2/clients/list", {"fields": ["visa_type", "visa_expiry_date"]})
explore_endpoint_post("api/v2/clients/list", {"with": ["visa_type", "visa_expiry_date"]}) 
