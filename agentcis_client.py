import requests
import json
import pandas as pd
from datetime import datetime
import time

class AgentcisClient:
    def __init__(self, api_token, base_url):
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def fetch_visa_data(self, limit=None, progress_callback=None, data_callback=None):
        """
        Fetches clients and their detailed visa information.
        Uses ThreadPoolExecutor for parallel fetching to speed up the process.
        """
        import concurrent.futures

        if progress_callback:
            progress_callback("Fetching client list from Agentcis...")
        else:
            print("Fetching client list from Agentcis...")
            
        clients_url = f"{self.base_url}/api/v2/clients/list"
        
        all_clients = []
        page = 1
        has_more = True
        
        # 1. Fetch all clients (Pagination)
        while has_more:
            try:
                msg = f"Fetching client list page {page}..."
                if progress_callback: progress_callback(msg)
                else: print(msg)

                payload = {"page": page, "limit": 50} 
                response = requests.post(clients_url, headers=self.headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    current_batch = data.get('data', [])
                    
                    if not current_batch:
                        break
                        
                    all_clients.extend(current_batch)
                    
                    # Send batch to UI for visualization
                    if data_callback:
                        # Extract just a few fields for the preview table
                        preview_data = []
                        for c in current_batch:
                            preview_data.append({
                                "ID": c.get('id'),
                                "Name": c.get('full_name'),
                                "Email": c.get('email')
                            })
                        data_callback(preview_data)
                    
                    meta = data.get('meta', {})
                    if page >= meta.get('last_page', 1):
                        has_more = False
                    else:
                        page += 1
                        
                    if limit and len(all_clients) >= limit:
                        all_clients = all_clients[:limit]
                        break
                else:
                    msg = f"Error fetching list: {response.text}"
                    if progress_callback: progress_callback(msg)
                    else: print(msg)
                    break
            except Exception as e:
                msg = f"Exception fetching list: {e}"
                if progress_callback: progress_callback(msg)
                else: print(msg)
                break

        msg = f"Found {len(all_clients)} clients. Fetching details in parallel (100 threads)..."
        if progress_callback: progress_callback(msg)
        else: print(msg)
        
        detailed_data = []
        total_clients = len(all_clients)
        completed_count = 0
        
        # 2. Define helper for single client fetch
        def fetch_single_client(client):
            client_id = client.get('id')
            if not client_id:
                return None
                
            try:
                detail_url = f"{self.base_url}/api/v2/clients/{client_id}"
                detail_res = requests.get(detail_url, headers=self.headers)
                
                if detail_res.status_code == 200:
                    detail_json = detail_res.json()
                    client_data = detail_json.get('data', {})
                    
                    visa_expiry_obj = client_data.get('visa_expiry_date')
                    visa_expiry = visa_expiry_obj.get('actual') if visa_expiry_obj else None
                    visa_type = client_data.get('visa_type')
                    
                    return {
                        "Client Name": client_data.get('full_name'),
                        "Visa Type": visa_type,
                        "Visa Expiry Date": visa_expiry,
                        "Email": client_data.get('email', {}).get('primary'),
                        "Phone": client_data.get('phone', {}).get('formatted')
                    }
            except Exception as e:
                print(f"Error fetching details for client {client_id}: {e}")
            return None

        # 3. Execute in parallel
        # Increased to 100 workers as requested
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            future_to_client = {executor.submit(fetch_single_client, client): client for client in all_clients}
            
            for future in concurrent.futures.as_completed(future_to_client):
                result = future.result()
                if result:
                    detailed_data.append(result)
                
                completed_count += 1
                if completed_count % 20 == 0 or completed_count == total_clients:
                    msg = f"Processed {completed_count}/{total_clients} clients..."
                    if progress_callback: progress_callback(msg)
                    else: print(msg)

        return pd.DataFrame(detailed_data)

if __name__ == "__main__":
    # Test run
    import json
    with open("config.json", "r") as f:
        config = json.load(f)
    
    client = AgentcisClient(config["agentcis_api_token"], config["agentcis_base_url"])
    df = client.fetch_visa_data(limit=10)
    print(df.head())
