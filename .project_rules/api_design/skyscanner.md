import requests

def search_flights(origin, destination, departure_date, return_date=None):
    # 創建會話
    create_url = "https://skyscanner-api.com/flights-live-prices/create"
    create_payload = {
        "market": "TW",
        "locale": "zh-TW", 
        "currency": "TWD",
        "queryLegs": [
            {
                "originPlaceId": {"iata": origin},
                "destinationPlaceId": {"iata": destination},
                "date": {"year": departure_date.year, "month": departure_date.month, "day": departure_date.day}
            }
        ],
        "adults": 1,
        "children": 0,
        "infants": 0,
        "cabinClass": "CABIN_CLASS_ECONOMY"
    }
    
    # 如果有返程日期，添加返程信息
    if return_date:
        create_payload["queryLegs"].append({
            "originPlaceId": {"iata": destination},
            "destinationPlaceId": {"iata": origin}, 
            "date": {"year": return_date.year, "month": return_date.month, "day": return_date.day}
        })
    
    # 發送請求獲取會話token
    response = requests.post(create_url, json=create_payload)
    session_token = response.json().get("sessionToken")
    
    # 輪詢結果
    poll_url = f"https://skyscanner-api.com/flights-live-prices/poll/{session_token}"
    poll_response = requests.get(poll_url)
    
    return poll_response.json()

