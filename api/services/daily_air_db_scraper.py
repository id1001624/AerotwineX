#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import os
import json
from datetime import datetime, timedelta
import time
import random
import re
import pyodbc
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DailyAirDBScraper')

# 嘗試導入數據庫模組，依實際情況可能需要調整
try:
    from database.flight_db import FlightDB
except ImportError:
    # 如果無法導入，創建一個模擬的DB類
    class FlightDB:
        def __init__(self):
            self.connected = False
            self.test_mode = True
            logging.warning("使用模擬的FlightDB類 - 資料不會實際寫入資料庫")
        
        def connect(self):
            self.connected = True
            return True
        
        def insert_flights(self, flights):
            logging.info(f"模擬寫入 {len(flights)} 個航班到資料庫")
            return len(flights)
        
        def close(self):
            self.connected = False

class DailyAirDBScraper:
    """
    德安航空网站爬虫
    用于获取德安航空的航班信息并存储到数据库
    """
    
    def __init__(self):
        """初始化爬虫"""
        self.name = "德安航空"
        self.airline_id = 1  # 假設德安航空的ID是1
        self.base_url = "https://www.dailyair.com.tw"
        self.schedule_url = "https://www.dailyair.com.tw/Page/Schedule"
        
        # 設定請求頭
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': 'https://www.dailyair.com.tw/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        # 創建會話
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 初始化資料庫連接
        self.db = FlightDB()
        
        # 檢查是否為測試模式
        self.test_mode = os.getenv('TEST_MODE', 'False').lower() in ('true', '1', 't')
        if self.test_mode:
            logger.info("運行在測試模式")
        
        # 航線資訊 - 德安航空的航線代碼
        self.routes = [
            {"departure": "KHH", "arrival": "KYD", "dep_name": "高雄", "arr_name": "蘭嶼"},
            {"departure": "KHH", "arrival": "TTT", "dep_name": "高雄", "arr_name": "臺東"},
            {"departure": "GNI", "arrival": "KHH", "dep_name": "綠島", "arr_name": "高雄"},
            {"departure": "KHH", "arrival": "GNI", "dep_name": "高雄", "arr_name": "綠島"},
            {"departure": "KYD", "arrival": "KHH", "dep_name": "蘭嶼", "arr_name": "高雄"},
            {"departure": "KYD", "arrival": "TTT", "dep_name": "蘭嶼", "arr_name": "臺東"},
            {"departure": "TTT", "arrival": "KHH", "dep_name": "臺東", "arr_name": "高雄"},
            {"departure": "TTT", "arrival": "KYD", "dep_name": "臺東", "arr_name": "蘭嶼"},
            {"departure": "TTT", "arrival": "GNI", "dep_name": "臺東", "arr_name": "綠島"},
            {"departure": "GNI", "arrival": "TTT", "dep_name": "綠島", "arr_name": "臺東"}
        ]
        
        # 获取数据库连接
        self.connection_string = os.getenv('DB_CONNECTION_STRING')
        
        if self.test_mode:
            logger.info("运行在测试模式，不会连接数据库")
            self.conn = None
            self.cursor = None
        else:
            if not self.connection_string:
                logger.error("缺少数据库连接字符串环境变量 DB_CONNECTION_STRING")
                raise ValueError("缺少数据库连接字符串环境变量 DB_CONNECTION_STRING")
            
            logger.info("初始化数据库连接")
            try:
                self.conn = pyodbc.connect(self.connection_string, timeout=30)
                self.cursor = self.conn.cursor()
                logger.info("数据库连接成功")
            except Exception as e:
                logger.error(f"数据库连接失败: {e}")
                raise
        
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
    
    def random_delay(self, min_seconds=1, max_seconds=3):
        """随机延迟，避免请求过快"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"等待 {delay:.2f} 秒")
        time.sleep(delay)
    
    def get_schedule_page(self):
        """獲取航班時刻表頁面"""
        try:
            logger.info(f"正在獲取德安航空時刻表頁面: {self.schedule_url}")
            response = self.session.get(self.schedule_url, timeout=10)
            
            if response.status_code == 200:
                logger.info("成功獲取時刻表頁面")
                return response.text
            else:
                logger.error(f"無法獲取時刻表頁面，狀態碼: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"獲取時刻表頁面時發生錯誤: {e}")
            return None
    
    def parse_schedule_data(self, html_content):
        """解析航班時刻表數據"""
        if not html_content:
            logger.error("沒有HTML內容可供解析")
            return []
        
        flights = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.info("開始解析航班時刻表數據")
            
            # 尋找包含航班時刻表的表格
            # 注意：這裡的選擇器需要根據實際網頁結構調整
            schedule_tables = soup.select('.schedule-table')
            
            if not schedule_tables:
                logger.warning("未找到航班時刻表表格")
                # 如果找不到表格元素，嘗試尋找其他可能包含數據的元素
                schedule_tables = soup.select('.flight-schedule') or soup.select('table')
            
            for table in schedule_tables:
                # 嘗試解析每個表格
                logger.info(f"解析航班表格")
                
                # 假設每個表格代表一條航線的時刻表
                rows = table.select('tr')
                
                # 跳過表頭
                for row in rows[1:]:
                    try:
                        # 獲取單元格數據
                        cells = row.select('td')
                        if len(cells) >= 4:  # 假設至少有 航班號、出發地、目的地、時間 四列
                            flight_no = cells[0].text.strip()
                            departure = cells[1].text.strip()
                            arrival = cells[2].text.strip()
                            time_str = cells[3].text.strip()
                            
                            # 將時間字符串拆分為出發和到達時間
                            time_parts = time_str.split('-')
                            if len(time_parts) == 2:
                                departure_time = time_parts[0].strip()
                                arrival_time = time_parts[1].strip()
                                
                                # 嘗試找到對應的航線代碼
                                route = None
                                for r in self.routes:
                                    if departure in r["dep_name"] and arrival in r["arr_name"]:
                                        route = r
                                        break
                                
                                if route:
                                    # 構建航班信息
                                    flight = {
                                        'flight_no': flight_no,
                                        'airline': self.name,
                                        'airline_id': self.airline_id,
                                        'departure': route['departure'],
                                        'arrival': route['arrival'],
                                        'departure_name': route['dep_name'],
                                        'arrival_name': route['arr_name'],
                                        'scheduled_departure_time': departure_time,
                                        'scheduled_arrival_time': arrival_time,
                                        'crawl_date': datetime.now().strftime('%Y-%m-%d'),
                                        'crawl_time': datetime.now().strftime('%H:%M:%S')
                                    }
                                    flights.append(flight)
                                    logger.debug(f"解析到航班: {flight_no}, {departure}-{arrival}, {departure_time}-{arrival_time}")
                    except Exception as e:
                        logger.warning(f"解析行數據時出錯: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"解析航班時刻表時發生錯誤: {e}")
        
        logger.info(f"成功解析 {len(flights)} 個航班信息")
        return flights
    
    def save_to_file(self, flights, filename=None):
        """保存航班數據到文件（用於測試）"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"daily_air_flights_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(flights, f, ensure_ascii=False, indent=2)
            logger.info(f"航班數據已保存到文件: {filename}")
            return True
        except Exception as e:
            logger.error(f"保存數據到文件時發生錯誤: {e}")
            return False
    
    def save_to_database(self, flights):
        """保存航班數據到資料庫"""
        if not flights:
            logger.warning("沒有航班數據可保存到資料庫")
            return 0
        
        if self.test_mode:
            logger.info(f"測試模式: 模擬保存 {len(flights)} 個航班到資料庫")
            return len(flights)
        
        try:
            # 連接資料庫
            if not self.db.connect():
                logger.error("無法連接到資料庫")
                return 0
            
            # 插入航班數據
            inserted_count = self.db.insert_flights(flights)
            logger.info(f"成功將 {inserted_count} 個航班保存到資料庫")
            
            # 關閉資料庫連接
            self.db.close()
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"保存數據到資料庫時發生錯誤: {e}")
            return 0
    
    def crawl_and_save(self):
        """爬取航班數據並保存"""
        logger.info(f"開始爬取德安航空航班時刻表")
        
        # 獲取時刻表頁面
        html_content = self.get_schedule_page()
        
        if not html_content:
            logger.error("未能獲取到有效的HTML內容，爬取失敗")
            return []
        
        # 隨機延遲
        self.random_delay()
        
        # 解析航班數據
        flights = self.parse_schedule_data(html_content)
        
        if not flights:
            logger.warning("未解析到任何航班數據")
            return []
        
        # 在測試模式下保存到文件
        if self.test_mode:
            self.save_to_file(flights)
        
        # 保存到資料庫
        self.save_to_database(flights)
        
        logger.info(f"爬取完成，共獲取 {len(flights)} 個航班信息")
        return flights

def main():
    """主函數，用於獨立運行測試"""
    # 配置日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("daily_air_scraper.log"),
            logging.StreamHandler()
        ]
    )
    
    # 創建爬蟲實例並運行
    scraper = DailyAirDBScraper()
    flights = scraper.crawl_and_save()
    
    print(f"爬取完成，共獲取 {len(flights)} 個航班")
    return flights

if __name__ == "__main__":
    main() 