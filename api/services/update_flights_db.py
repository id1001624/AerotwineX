#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 設定路徑以導入其他模組
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入爬蟲模組
from services.daily_air_db_scraper import DailyAirDBScraper
from services.daily_air_realtime_updater import DailyAirRealTimeUpdater

# 加載環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("flight_update.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FlightUpdateService')

class FlightUpdateService:
    """
    航班資訊更新服務
    整合航班時刻表爬取和實時狀態更新功能
    """
    
    def __init__(self):
        """初始化服務"""
        logger.info("初始化航班資訊更新服務")
        
        # 檢查是否為測試模式
        self.test_mode = os.getenv('TEST_MODE', 'False').lower() in ('true', '1', 't')
        if self.test_mode:
            logger.info("運行在測試模式")
        
        # 創建爬蟲實例
        self.db_scraper = DailyAirDBScraper()
        self.realtime_updater = DailyAirRealTimeUpdater()
    
    def run_update(self):
        """執行完整的更新流程"""
        logger.info("開始執行航班資訊更新流程")
        
        try:
            # 步驟1: 爬取最新的航班時刻表數據
            logger.info("步驟1: 爬取德安航空航班時刻表")
            flights = self.db_scraper.crawl_and_save()
            logger.info(f"成功獲取 {len(flights)} 個航班資訊")
            
            # 步驟2: 等待一段時間 (允許數據寫入完成)
            time.sleep(5)
            
            # 步驟3: 更新實時航班狀態和起降時間
            logger.info("步驟2: 更新實時航班狀態和起降時間")
            realtime_info = self.realtime_updater.update_realtime_info()
            logger.info(f"成功更新 {len(realtime_info) if realtime_info else 0} 個航班的實時資訊")
            
            # 步驟4: 生成更新報告
            self._generate_report(flights, realtime_info)
            
            logger.info("航班資訊更新流程完成")
            
            return True
            
        except Exception as e:
            logger.error(f"更新過程中發生錯誤: {e}")
            return False
    
    def _generate_report(self, flights, realtime_info):
        """生成更新報告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"flight_update_report_{timestamp}.txt"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"航班資訊更新報告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*50 + "\n\n")
                
                # 航班時刻表統計
                f.write("1. 航班時刻表數據\n")
                f.write(f"   - 總航班數: {len(flights)}\n")
                
                # 按航線統計
                routes = {}
                for flight in flights:
                    route_key = f"{flight['departure']}-{flight['arrival']}"
                    routes[route_key] = routes.get(route_key, 0) + 1
                
                f.write("   - 航線統計:\n")
                for route, count in routes.items():
                    f.write(f"     * {route}: {count} 班\n")
                
                # 實時資訊統計
                f.write("\n2. 實時航班資訊\n")
                if not realtime_info:
                    f.write("   - 未獲取到實時航班資訊\n")
                else:
                    f.write(f"   - 更新航班數: {len(realtime_info)}\n")
                    
                    # 按狀態統計
                    status_count = {
                        'on_time': 0,
                        'delayed': 0,
                        'cancelled': 0,
                        'departed': 0,
                        'arrived': 0
                    }
                    
                    for info in realtime_info:
                        status = info.get('flight_status', 'on_time')
                        status_count[status] = status_count.get(status, 0) + 1
                    
                    f.write("   - 狀態統計:\n")
                    f.write(f"     * 準時: {status_count['on_time']} 班\n")
                    f.write(f"     * 延誤: {status_count['delayed']} 班\n")
                    f.write(f"     * 取消: {status_count['cancelled']} 班\n")
                    f.write(f"     * 已起飛: {status_count['departed']} 班\n")
                    f.write(f"     * 已抵達: {status_count['arrived']} 班\n")
                
                f.write("\n3. 執行摘要\n")
                f.write(f"   - 更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"   - 測試模式: {'是' if self.test_mode else '否'}\n")
                f.write(f"   - 數據已保存到數據庫: {'否' if self.test_mode else '是'}\n")
                
            logger.info(f"更新報告已生成: {report_file}")
            
        except Exception as e:
            logger.error(f"生成報告時出錯: {e}")

def main():
    """主函數"""
    service = FlightUpdateService()
    success = service.run_update()
    
    if success:
        logger.info("航班更新服務執行成功")
    else:
        logger.error("航班更新服務執行失敗")
    
    return success

if __name__ == "__main__":
    main() 