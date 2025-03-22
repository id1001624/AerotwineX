# AerotwineX API 文件

此API提供航班搜尋、機場查詢和航空公司查詢的功能，支援前端應用的數據需求。

## 安裝與設定

1. 確保已安裝所需依賴：
   ```
   pip install -r ../requirements.txt
   ```

2. 啟動API服務：
   ```
   python start_api.py
   ```

## API端點

### 機場列表

獲取所有支援的機場列表。

- **URL**: `/api/airports`
- **方法**: `GET`
- **回應範例**:
  ```json
  [
    {"code": "TPE", "name": "台灣桃園國際機場"},
    {"code": "TSA", "name": "台北松山機場"},
    {"code": "KHH", "name": "高雄國際機場"}
  ]
  ```

### 航空公司列表

獲取所有支援的航空公司列表。

- **URL**: `/api/airlines`
- **方法**: `GET`
- **回應範例**:
  ```json
  [
    {"id": "CI", "name": "中華航空"},
    {"id": "BR", "name": "長榮航空"},
    {"id": "AE", "name": "華信航空"}
  ]
  ```

### 航班搜尋

根據條件搜尋航班。

- **URL**: `/api/flights/search`
- **方法**: `GET`
- **參數**:
  - `departure` (必填): 出發機場代碼
  - `arrival` (必填): 到達機場代碼
  - `date` (必填): 日期 (YYYY-MM-DD)
  - `airline` (選填): 航空公司ID
- **回應範例**:
  ```json
  {
    "status": "success",
    "data": [
      {
        "flight_number": "CI123",
        "scheduled_departure": "2025-03-25T08:30:00",
        "scheduled_arrival": "2025-03-25T10:15:00",
        "departure_airport_code": "TPE",
        "arrival_airport_code": "KHH",
        "airline_id": "CI",
        "flight_status": "scheduled",
        "aircraft_type": "A330-300",
        "price": 2500,
        "booking_link": "#"
      }
    ],
    "count": 1,
    "search_criteria": {
      "departure": "TPE",
      "arrival": "KHH",
      "date": "2025-03-25",
      "airline": "CI"
    }
  }
  ```

## 錯誤處理

API會返回適當的HTTP狀態碼和JSON格式的錯誤訊息：

```json
{
  "status": "error",
  "message": "錯誤訊息描述",
  "error": "詳細錯誤資訊"
}
```

常見HTTP狀態碼：
- 200: 成功
- 400: 請求參數錯誤
- 404: 資源不存在
- 500: 伺服器內部錯誤

## 未來擴展

計劃中的功能：
1. 整合真實航班數據API
2. 添加航班詳情端點
3. 添加機票價格查詢功能
4. 支援多日期搜尋
5. 支援航班實時狀態更新