# AviationStack API 整合服務

本目錄包含用於整合和使用AviationStack API的服務，用於查詢和獲取航班資訊。

## 檔案說明

- `external_apis.py`: AviationStack API的主要接口，封裝了API的調用邏輯
- `aviation_stack_importer.py`: 用於將API獲取的航班數據導入到數據庫
- `test_aviation_stack.py`: 測試AviationStack API的各項功能
- `README.md`: 本文件，說明使用方法

## 環境設置

1. 確保在專案根目錄的`.env`文件中已設置AviationStack API的密鑰：

```
AVIATIONSTACK_API_KEY=your_api_key_here
DB_CONNECTION_STRING=your_db_connection_string_here
```

2. 安裝所需依賴：

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 測試API功能

運行測試腳本以驗證API功能是否正常：

```bash
python api/services/test_aviation_stack.py
```

此腳本將測試API的各項功能，並將結果輸出到`logs`目錄。

### 2. 導入航班數據

使用導入腳本將航班數據導入到數據庫：

```bash
python scripts/import_aviation_stack_flights.py --date 2023-04-15 --limit 100
```

參數說明：
- `--date`: 指定要導入的航班日期，格式為YYYY-MM-DD，不指定則使用當天
- `--limit`: 限制處理的記錄數量，默認為100
- `--days`: 從指定日期開始，導入多少天的數據，默認為1

### 3. 在代碼中使用API

```python
from api.services.external_apis import get_real_time_flights, get_route_flights

# 獲取特定航班資訊
flight_info = get_real_time_flights(airline_code="CI", flight_number="100")

# 獲取特定航線的航班
route_flights = get_route_flights(departure_airport="TPE", arrival_airport="HND")
```

## 注意事項

1. AviationStack API有調用限制，請合理控制調用頻率和數量。
2. 免費版API僅支持HTTP（非HTTPS），如需HTTPS請升級到付費版。
3. 導入數據時，會自動避免重複記錄，對已存在的記錄將進行更新。

## API功能一覽

- `get_real_time_flights`: 獲取航班實時狀態
- `get_airport_flights`: 獲取機場出發/抵達的航班
- `get_route_flights`: 獲取特定航線的航班
- `get_airline_info`: 獲取航空公司資訊
- `get_airport_info`: 獲取機場資訊
- `get_flights_for_configured_airlines_airports`: 批量獲取配置中指定的航空公司和機場的航班

更多詳細的API使用方法請參考代碼中的文檔字符串。 