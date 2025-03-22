import os
import sys
import logging
from datetime import datetime, timedelta
import json

# 確保daily_air_scraper可以被導入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.daily_air_scraper import DailyAirScraper

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestDailyAirScraper")

def main():
    """測試德安航空爬蟲，並打印結果"""
    try:
        logger.info("開始測試德安航空爬蟲...")
        
        # 創建爬蟲實例 (使用無頭模式)
        scraper = DailyAirScraper(headless=True)
        
        # 獲取未來三天的日期進行測試
        today = datetime.now()
        test_dates = [
            today.strftime("%Y-%m-%d"),
            (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            (today + timedelta(days=7)).strftime("%Y-%m-%d")
        ]
        
        total_flights = 0
        
        # 對每個日期進行測試
        for date_str in test_dates:
            logger.info(f"開始爬取日期: {date_str}")
            flights = scraper.get_flights_by_date(date_str)
            
            logger.info(f"日期 {date_str} 找到 {len(flights)} 個航班")
            
            # 打印前5個航班信息
            for i, flight in enumerate(flights[:5]):
                logger.info(f"航班 {i+1}: {flight['flight_number']} - "
                           f"{flight['origin_name']}({flight['origin_airport']}) → "
                           f"{flight['destination_name']}({flight['destination_airport']}), "
                           f"{flight['departure_time'].split()[1]} → {flight['arrival_time'].split()[1]}")
            
            total_flights += len(flights)
            
            # 檢查儲存的JSON文件
            output_dir = "flight_data"
            output_file = os.path.join(output_dir, f"dailyair_flights_{date_str}.json")
            
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                logger.info(f"已保存航班資料至 {output_file} (文件大小: {file_size} 字節)")
                
                # 讀取保存的數據進行驗證
                with open(output_file, "r", encoding="utf-8") as f:
                    saved_flights = json.load(f)
                
                logger.info(f"驗證保存的數據: 文件中包含 {len(saved_flights)} 個航班記錄")
                assert len(saved_flights) == len(flights), "保存的航班數量與爬取的不一致"
            else:
                logger.warning(f"未找到保存的航班數據文件: {output_file}")
        
        logger.info(f"測試完成，共爬取 {total_flights} 個航班")
        logger.info(f"測試通過!")
        return True
    
    except Exception as e:
        logger.error(f"測試過程中出現錯誤: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 