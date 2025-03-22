import os
import sys
import logging
from datetime import datetime, timedelta
import json

# 確保daily_air_simple_scraper可以被導入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.daily_air_simple_scraper import DailyAirSimpleScraper

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestDailyAirSimpleScraper")

def main():
    """測試德安航空簡化爬蟲，並打印結果"""
    try:
        logger.info("開始測試德安航空簡化爬蟲...")
        
        # 創建爬蟲實例
        scraper = DailyAirSimpleScraper()
        
        # 獲取明天的日期進行測試
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(f"開始爬取日期: {tomorrow}")
        flights = scraper.get_flights_by_date(tomorrow)
        
        logger.info(f"日期 {tomorrow} 找到 {len(flights)} 個航班")
        
        # 按航線分類航班並打印統計信息
        routes = {}
        
        for flight in flights:
            route_key = f"{flight['origin_airport']}-{flight['destination_airport']}"
            if route_key not in routes:
                routes[route_key] = []
            routes[route_key].append(flight)
        
        logger.info(f"共找到 {len(routes)} 條航線:")
        
        for route, route_flights in routes.items():
            origin = route_flights[0]['origin_name']
            destination = route_flights[0]['destination_name']
            logger.info(f"航線 {route} ({origin}-{destination}): {len(route_flights)} 個航班")
            
            # 打印該航線的前3個航班
            for i, flight in enumerate(route_flights[:3]):
                dep_time = flight['departure_time'].split()[1].replace(':00', '')
                arr_time = flight['arrival_time'].split()[1].replace(':00', '')
                flight_number = flight['flight_number']
                logger.info(f"  - {flight_number}: {dep_time} → {arr_time} (運營: {flight['days_operated']})")
        
        # 獲取資料來源
        sources = set(flight.get('source', 'web_scraping') for flight in flights)
        logger.info(f"航班資料來源: {', '.join(sources)}")
        
        # 檢查儲存的JSON文件
        output_dir = "flight_data"
        output_file = os.path.join(output_dir, f"dailyair_simple_flights_{tomorrow}.json")
        
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
        
        logger.info(f"測試完成，共爬取 {len(flights)} 個航班")
        logger.info(f"測試通過!")
        return True
    
    except Exception as e:
        logger.error(f"測試過程中出現錯誤: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 