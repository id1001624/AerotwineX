import logging
import os
import sys
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加模塊路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入爬蟲模塊
from services.daily_air_simple_scraper import DailyAirSimpleScraper
from services.daily_air_api_scraper import DailyAirAPIScraper

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyAirManager")

class DailyAirManager:
    """
    德安航空爬蟲管理類，統一管理多種爬蟲方法
    1. 支援同時使用多種爬蟲策略（簡單爬蟲、API爬蟲等）
    2. 自動合併多個爬蟲源的結果
    3. 優先使用更可靠的數據源
    """

    def __init__(self):
        self.scrapers = [
            DailyAirSimpleScraper(),
            DailyAirAPIScraper()
        ]
        self.output_dir = "flight_data"
        logger.info("德安航空爬蟲管理器初始化完成")

    def get_flights_by_date(self, date_str, use_all_scrapers=True, combine_results=True):
        """
        獲取指定日期的航班數據
        
        Args:
            date_str: 日期字符串，格式為 YYYY-MM-DD
            use_all_scrapers: 是否使用所有爬蟲
            combine_results: 是否合併多個爬蟲的結果
            
        Returns:
            包含航班資訊的列表
        """
        logger.info(f"開始獲取德安航空 {date_str} 的航班數據")
        
        # 確保輸出目錄存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"創建輸出目錄: {self.output_dir}")
        
        all_flights = []
        scraper_results = {}
        
        # 使用線程池並發運行爬蟲
        with ThreadPoolExecutor(max_workers=len(self.scrapers)) as executor:
            # 啟動所有爬蟲任務
            future_to_scraper = {
                executor.submit(scraper.get_flights_by_date, date_str): scraper.__class__.__name__
                for scraper in self.scrapers
            }
            
            # 收集完成的任務結果
            for future in as_completed(future_to_scraper):
                scraper_name = future_to_scraper[future]
                try:
                    flights = future.result()
                    logger.info(f"爬蟲 {scraper_name} 成功獲取 {len(flights)} 個航班")
                    
                    # 保存各爬蟲的數據
                    scraper_results[scraper_name] = flights
                    
                    # 合併到總結果中
                    if combine_results:
                        all_flights.extend(flights)
                except Exception as e:
                    logger.error(f"爬蟲 {scraper_name} 執行時出錯: {str(e)}")
        
        # 如果需要合併結果，進行重複數據的處理
        if combine_results and all_flights:
            all_flights = self._process_combined_results(all_flights)
        
        # 保存合併後的結果
        self._save_combined_results(date_str, all_flights, scraper_results)
        
        logger.info(f"德安航空 {date_str} 的數據獲取完成，共 {len(all_flights)} 個航班")
        return all_flights

    def _process_combined_results(self, flights):
        """處理合併後的結果，去除重複項並優先保留更可靠的數據源"""
        logger.info(f"開始處理合併結果，共 {len(flights)} 個航班")
        
        # 按航班號和航線分組
        flight_groups = {}
        for flight in flights:
            # 創建唯一鍵：航班號+起飛機場+降落機場+日期（不含時間）
            flight_key = f"{flight['flight_number']}_{flight['origin_airport']}_{flight['destination_airport']}_{flight['departure_time'].split()[0]}"
            
            if flight_key not in flight_groups:
                flight_groups[flight_key] = []
            
            flight_groups[flight_key].append(flight)
        
        # 處理每組航班，選擇最可靠的數據
        processed_flights = []
        for key, group in flight_groups.items():
            if len(group) == 1:
                # 只有一個來源，直接添加
                processed_flights.append(group[0])
            else:
                # 多個來源，按優先級選擇
                # 優先級：api > web_scraping > hardcoded
                priority_order = {"api": 0, "web_scraping": 1, "hardcoded": 2}
                
                # 按優先級排序
                sorted_group = sorted(group, key=lambda x: priority_order.get(x.get('source', 'unknown'), 99))
                
                # 選擇優先級最高的
                best_flight = sorted_group[0]
                processed_flights.append(best_flight)
        
        logger.info(f"處理完成，去除重複後共 {len(processed_flights)} 個航班")
        return processed_flights

    def _save_combined_results(self, date_str, all_flights, scraper_results):
        """保存合併後的結果和各爬蟲的原始結果"""
        # 保存合併結果
        combined_file = os.path.join(self.output_dir, f"dailyair_combined_flights_{date_str}.json")
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(all_flights, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存合併結果至 {combined_file}，共 {len(all_flights)} 個航班")
        
        # 保存爬蟲統計信息
        stats = {
            "date": date_str,
            "total_flights": len(all_flights),
            "scrapers": {}
        }
        
        for scraper_name, flights in scraper_results.items():
            # 保存每個爬蟲的統計信息
            source_types = {}
            for flight in flights:
                source = flight.get('source', 'unknown')
                if source not in source_types:
                    source_types[source] = 0
                source_types[source] += 1
            
            stats["scrapers"][scraper_name] = {
                "total": len(flights),
                "sources": source_types
            }
        
        # 保存統計文件
        stats_file = os.path.join(self.output_dir, f"dailyair_stats_{date_str}.json")
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存爬蟲統計信息至 {stats_file}")

if __name__ == "__main__":
    # 獲取未來7天的日期
    dates = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
    
    # 創建爬蟲管理器
    manager = DailyAirManager()
    
    # 爬取未來7天的數據
    for date_str in dates:
        flights = manager.get_flights_by_date(date_str)
        print(f"日期 {date_str} 獲取到 {len(flights)} 個航班")
        
        # 打印前3個航班作為示例
        for i, flight in enumerate(flights[:3]):
            print(f"{i+1}. {flight['flight_number']}: {flight['origin_name']} → {flight['destination_name']}, 出發: {flight['departure_time']}, 來源: {flight.get('source', 'unknown')}") 