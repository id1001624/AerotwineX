# AviationStack API 整合優化指南

## 概述

此文檔詳細說明了對AviationStack API整合所做的優化，以解決免費API計劃的限制並確保系統在開發和生產環境中的穩定性。

## 主要限制

AviationStack免費API計劃有以下限制：
- 每月僅500次API調用
- 某些高級功能（如實時航班查詢）不可用
- 有請求頻率限制

## 優化策略

### 1. API調用優化

#### 實現內容
- **智能緩存系統**：
  - 在`external_apis.py`中實現了基於pickle的缓存系統
  - 通過`ensure_cache_dir()`, `get_cache_key()`, `get_from_cache()`, `save_to_cache()`函數管理缓存
  - 默認啟用緩存，可通過參數禁用

- **優先順序策略**：
  - 為重要航空公司和機場設置優先順序
  - 在緩存失效時優先更新高頻查詢的航班

- **批量處理與限制**：
  - 通過`max_api_calls`參數限制單次操作的API調用次數
  - 實現隨機延遲以避免頻率限制

### 2. 資料導入策略

#### 實現內容
- **漸進式導入**：
  - 通過`import_multiple_days`支持跨多天的小批量導入
  - 可以設置每日導入的航班數量限制

- **重複檢測**：
  - 在`import_flight`中實現了重複航班檢測
  - 避免浪費API調用在已導入的數據上

- **統計與監控**：
  - 添加了`get_import_statistics`以監控導入進度
  - 追蹤數據來源（API、緩存、模擬）分佈

### 3. 替代數據來源

#### 實現內容
- **模擬數據生成**：
  - 在`external_apis.py`中添加了`generate_mock_flight_data`
  - 當API不可用或超出限制時自動回退到模擬數據
  - 可以通過`use_mock_data`參數控制

- **無縫切換**：
  - 資料來源無縫整合到導入流程中
  - 系統跟踪數據來源以便後續分析

### 4. 架構調整

#### 實現內容
- **統一錯誤處理**：
  - 改進的`make_api_request`函數包含全面的錯誤處理
  - 特定錯誤代碼（401、403、429）的特殊處理

- **環境變數管理**：
  - 使用絕對路徑加載`.env`文件
  - 更健壯的環境變數檢索

- **高級日誌記錄**：
  - 按日期時間戳分割日誌文件
  - 記錄API請求、回應和錯誤的詳細信息
  - 追蹤緩存命中和未命中

## 文件和函數概述

### external_apis.py
- `ensure_cache_dir()`: 確保緩存目錄存在
- `get_cache_key()`: 生成唯一緩存鍵
- `get_from_cache()`: 從緩存獲取數據
- `save_to_cache()`: 保存數據到緩存
- `make_api_request()`: 統一API請求處理
- `generate_mock_flight_data()`: 生成模擬航班數據
- `get_flights_for_configured_airlines_airports()`: 優化批量獲取航班

### aviation_stack_importer.py
- `import_flight()`: 導入單個航班，檢查重複
- `bulk_import_flights()`: 批量導入航班，支持緩存和模擬數據
- `import_multiple_days()`: 跨多天導入航班數據
- `get_import_statistics()`: 獲取導入統計信息

### import_aviation_stack_flights.py
- 更新的命令行參數：
  - `--date`: 指定導入日期
  - `--days`: 指定導入天數
  - `--limit`: 每天導入航班數量限制
  - `--api-calls`: 最大API調用次數
  - `--no-cache`: 禁用緩存
  - `--no-mock`: 禁用模擬數據
  - `--stats`: 顯示導入統計信息

## 使用例子

### 使用緩存導入航班數據
```bash
python scripts/import_aviation_stack_flights.py --date 2023-05-01 --limit 50
```

### 跨多天導入少量航班，保留API限制
```bash
python scripts/import_aviation_stack_flights.py --days 5 --limit 10 --api-calls 20
```

### 使用模擬數據進行開發測試
```bash
python scripts/import_aviation_stack_flights.py --date 2023-05-01 --limit 100 --api-calls 0
```

### 查看導入統計信息
```bash
python scripts/import_aviation_stack_flights.py --stats
```

## 升級到付費計劃準備

系統已設計為可以無縫升級到付費API計劃：
1. 更新`.env`文件中的API密鑰
2. 調整`max_api_calls`參數以適應更高的限制
3. 移除對模擬數據的依賴（或保留用於測試）

## 最佳實踐

1. **開發階段**：
   - 優先使用緩存和模擬數據
   - 將API調用限制設置為最低值
   - 定期運行測試腳本以驗證功能

2. **生產前階段**：
   - 逐步增加API調用以擴充資料庫
   - 監控導入統計信息以確保數據質量
   - 建立API使用模式以便制定升級計劃

3. **生產階段**：
   - 考慮升級到更高級的API計劃
   - 保持緩存系統以減少冗餘調用
   - 實施定期增量更新策略