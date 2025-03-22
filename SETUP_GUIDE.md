# AerotwineX 航班查詢系統設置指南

本指南將引導您設置和運行 AerotwineX 航班查詢系統，包括後端 API 和前端 Vue 應用程序。

## 先決條件

確保您的系統已安裝以下軟件：

1. **Node.js** (v14 或更高版本)
2. **Python** (v3.6 或更高版本)
3. **Microsoft SQL Server**
4. **SQL Server ODBC 驅動程序**

## 數據庫設置

1. 確保您的 MSSQL 數據庫已經創建，並包含以下表：
   - `Airlines`
   - `Airports`
   - `Flights`

2. 根據需要調整 `api/app.py` 中的數據庫連接配置：

```python
DB_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}',
    'server': 'localhost',  # 修改為您的 SQL Server 實例名稱
    'database': 'AerotwineX',  # 修改為您的數據庫名稱
    'uid': 'sa',  # 修改為您的數據庫用戶名
    'pwd': 'YourPassword',  # 修改為您的數據庫密碼
    'trusted_connection': 'no'
}
```

## 設置和運行後端 API

1. 進入 API 目錄：
   ```
   cd api
   ```

2. 安裝所需的 Python 庫：
   ```
   pip install -r requirements.txt
   ```

3. 啟動 API 服務器：
   ```
   python app.py
   ```

4. API 服務器將在 http://localhost:5000 運行。

## 設置和運行前端應用程序

1. 進入前端目錄：
   ```
   cd frontend
   ```

2. 安裝所需的 Node.js 庫：
   ```
   npm install
   ```

3. 啟動 Vue 開發服務器：
   ```
   npm run serve
   ```

4. 前端應用程序將在 http://localhost:8080 運行。

## 訪問應用程序

在瀏覽器中打開 http://localhost:8080 訪問 AerotwineX 航班查詢系統。

## API 端點

後端 API 提供以下端點：

1. `GET /api/airports` - 獲取國內出發機場列表
2. `GET /api/destinations?departure={airport_id}` - 根據出發地獲取可直飛的目的地機場列表
3. `GET /api/airlines?departure={airport_id}&destination={airport_id}` - 根據出發地和目的地獲取航空公司列表
4. `GET /api/flights?departure={airport_id}&destination={airport_id}&date={YYYY-MM-DD}&airline={airline_id}` - 獲取符合條件的航班

## 故障排除

1. **資料庫連接錯誤**：
   - 確保 SQL Server 正在運行
   - 驗證資料庫連接設定是否正確
   - 確保已安裝正確的 ODBC 驅動程序

2. **API 連接錯誤**：
   - 確保後端 API 服務器正在運行
   - 檢查前端 `src/services/api.js` 中的 API 基礎 URL 是否正確

3. **前端錯誤**：
   - 檢查瀏覽器控制台中的錯誤消息
   - 確保所有 npm 依賴項都已正確安裝