#!/usr/bin/env python
"""
測試AviationStack API的功能與航班資料導入
"""
import os
import sys
import json
import datetime
import logging
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# 添加專案根目錄到路徑以便導入模組
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from api.services.external_apis import (
    ensure_cache_dir,
    get_cache_key,
    generate_mock_flight_data,
    save_to_cache,
    get_from_cache
)
from api.services.aviation_stack_importer import (
    bulk_import_flights,
    get_import_statistics
)

# 自定義JSON編碼器處理datetime對象
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

# 設置日誌
def setup_logging():
    """設置日誌配置"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"test_aviation_stack_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('test_aviation_stack')

# 載入環境變數
env_path = project_root / ".env"
load_dotenv(env_path)

def test_cache_functionality():
    """測試緩存功能"""
    logger = logging.getLogger('test_aviation_stack')
    
    logger.info("\n測試緩存功能:")
    
    # 確保緩存目錄存在
    cache_dir = ensure_cache_dir()
    logger.info(f"緩存目錄: {cache_dir}")
    
    # 測試參數
    endpoint = 'airlines'
    test_params = {
        'airline_iata': 'CI',
        'access_key': 'test_key'
    }
    
    # 測試緩存鍵生成
    cache_key = get_cache_key(endpoint, test_params)
    logger.info(f"測試參數的緩存鍵: {cache_key}")
    
    # 創建測試數據並保存到緩存
    test_data = {
        'airline': {
            'name': 'China Airlines',
            'iata_code': 'CI'
        }
    }
    
    save_to_cache(endpoint, test_params, test_data)
    logger.info("已保存測試數據到緩存")
    
    # 從緩存獲取數據
    cached_data = get_from_cache(endpoint, test_params)
    logger.info(f"從緩存獲取數據: {cached_data['airline']['name'] if cached_data else '未找到'}")
    
    # 檢查緩存目錄中的文件
    files = list(cache_dir.glob('*.pkl'))
    logger.info(f"緩存目錄中有 {len(files)} 個文件")
    
    # 驗證數據是否正確保存和檢索
    is_cached_correctly = (cached_data and cached_data['airline']['name'] == 'China Airlines')
    logger.info(f"緩存功能測試結果: {'成功' if is_cached_correctly else '失敗'}")
    return is_cached_correctly

def test_mock_data_functionality():
    """測試模擬數據功能"""
    logger = logging.getLogger('test_aviation_stack')
    
    logger.info("\n測試模擬數據功能:")
    
    # 生成模擬航班數據
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    logger.info(f"生成 {today} 的模擬航班數據...")
    
    # 定義測試用航空公司、機場和優先路線
    airlines = ['CI', 'BR', 'CX']
    airports = ['TPE', 'HKG', 'NRT', 'ICN']
    priority_routes = [('TPE', 'HKG'), ('TPE', 'NRT'), ('TPE', 'ICN')]
    
    mock_flights = generate_mock_flight_data(
        flight_date=today,
        airlines=airlines,
        airports=airports,
        priority_routes=priority_routes
    )
    logger.info(f"生成了 {len(mock_flights)} 個模擬航班")
    
    # 保存模擬數據示例到文件，以檢查結構
    output_dir = project_root / "logs"
    output_dir.mkdir(exist_ok=True)
    try:
        with open(output_dir / 'mock_flights_sample.json', 'w', encoding='utf-8') as f:
            json.dump(mock_flights, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
        logger.info("模擬航班示例已保存到 logs/mock_flights_sample.json")
    except Exception as e:
        logger.error(f"保存模擬數據時出錯: {e}")
    
    # 驗證模擬數據結構
    if mock_flights and len(mock_flights) > 0:
        sample_flight = mock_flights[0]
        # 打印樣本的一些基本屬性
        try:
            flight_info = {}
            for key in sample_flight.keys():
                if isinstance(sample_flight[key], (dict, list, str, int, float, bool, type(None))):
                    flight_info[key] = sample_flight[key]
                else:
                    flight_info[key] = str(sample_flight[key])
            
            logger.info(f"模擬航班樣本屬性: {flight_info.keys()}")
        except Exception as e:
            logger.error(f"處理模擬航班樣本時出錯: {e}")
        
        # 嘗試訪問結構，使用更安全的方式
        try:
            flight_number = str(sample_flight.get('flight_number', 'N/A'))
            airline = str(sample_flight.get('airline_iata', 'N/A'))
            departure = str(sample_flight.get('departure_airport', 'N/A'))
            arrival = str(sample_flight.get('arrival_airport', 'N/A'))
            
            logger.info(f"模擬航班範例: {airline}{flight_number} {departure} -> {arrival}")
        except Exception as e:
            logger.error(f"訪問模擬航班屬性時出錯: {e}")
        
    success = len(mock_flights) > 0
    logger.info(f"模擬數據功能測試結果: {'成功' if success else '失敗'}")
    return success

def test_bulk_import_with_mock():
    """測試使用模擬數據進行批量導入"""
    logger = logging.getLogger('test_aviation_stack')
    
    logger.info("\n測試使用模擬數據進行批量導入:")
    
    # 使用模擬數據進行批量導入
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    logger.info(f"使用模擬數據導入 {today} 的航班...")
    
    try:
        successful, total = bulk_import_flights(
            flight_date=today,
            limit=10,
            max_api_calls=0,  # 不使用API調用
            use_cache=False,  # 不使用緩存
            use_mock_data=True  # 強制使用模擬數據
        )
        
        success_rate = (successful / total * 100) if total > 0 else 0
        logger.info(f"導入結果: {successful}/{total} 成功率: {success_rate:.2f}%")
        
        # 檢查是否有航班被成功導入
        success = successful > 0
    except Exception as e:
        logger.error(f"模擬數據批量導入測試時出錯: {e}")
        success = False
    
    logger.info(f"模擬數據批量導入測試結果: {'成功' if success else '失敗'}")
    return success

def main():
    """主函數"""
    logger = setup_logging()
    
    logger.info("開始 AviationStack API 替代方案測試")
    logger.info("注意: 跳過實際API調用，僅測試緩存和模擬數據功能")
    
    # 記錄環境信息
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"當前目錄: {project_root}")
    
    # 測試緩存功能
    try:
        cache_test_success = test_cache_functionality()
        logger.info(f"緩存功能測試結果: {'成功' if cache_test_success else '失敗'}")
    except Exception as e:
        logger.error(f"緩存功能測試時出錯: {e}")
        cache_test_success = False
    
    # 測試模擬數據功能
    try:
        mock_test_success = test_mock_data_functionality()
        logger.info(f"模擬數據功能測試結果: {'成功' if mock_test_success else '失敗'}")
    except Exception as e:
        logger.error(f"模擬數據功能測試時出錯: {e}")
        mock_test_success = False
    
    # 測試使用模擬數據進行批量導入
    try:
        import_test_success = test_bulk_import_with_mock()
        logger.info(f"模擬數據批量導入測試結果: {'成功' if import_test_success else '失敗'}")
    except Exception as e:
        logger.error(f"批量導入測試時出錯: {e}")
        import_test_success = False
    
    # 總結結果
    overall_success = cache_test_success and mock_test_success and import_test_success
    if overall_success:
        logger.info("所有替代方案測試成功")
    else:
        logger.warning("部分替代方案測試失敗")
    
    logger.info("測試完成")

if __name__ == "__main__":
    main() 