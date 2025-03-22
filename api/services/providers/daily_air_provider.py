#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
德安航空航班資料提供者
通過網頁爬蟲獲取德安航空的航班資料
"""

import os
import datetime
import time
import random
from typing import Dict, List, Optional, Any, Tuple
import requests
from bs4 import BeautifulSoup

from api.services.providers.base import FlightProvider
from api.services.daily_air_db_scraper import DailyAirDBScraper

class DailyAirProvider(FlightProvider):
    """德安航空提供者實現，使用網頁爬蟲"""
    
    def __init__(self):
        """初始化德安航空提供者"""
        super().__init__("DailyAir")
        self.scraper = DailyAirDBScraper()
        self.airline_id = "DA"  # 德安航空的IATA代碼
        
    def get_flights(self, flight_date: str = None, **kwargs) -> List[Dict]:
        """
        獲取德安航空的航班資料
        
        參數:
            flight_date: 航班日期 (YYYY-MM-DD格式)，德安航空爬蟲目前不支援指定日期
            **kwargs: 其他參數
            
        返回:
            航班資料列表
        """
        self.logger.info("爬取德安航空航班資料")
        
        # 爬取航班資料
        flights = self.scraper.crawl_and_save()
        
        # 轉換為標準格式
        std_flights = self.transform_data(flights)
        
        # 過濾日期 (如果提供了日期)
        if flight_date:
            try:
                target_date = datetime.datetime.strptime(flight_date, '%Y-%m-%d').date()
                
                # 由於德安航空爬蟲沒有指定日期功能，我們從爬取的所有航班中過濾
                # 這是一個簡單的過濾，實際上可能需要更複雜的邏輯
                self.logger.info(f"過濾 {flight_date} 的航班")
                std_flights = [
                    f for f in std_flights 
                    if f.get('scheduled_departure').date() == target_date
                ]
                self.logger.info(f"過濾後得到 {len(std_flights)} 個航班")
            except Exception as e:
                self.logger.error(f"過濾航班日期時出錯: {e}")
        
        return std_flights
    
    def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        將德安航空爬蟲獲取的資料轉換為標準格式
        
        參數:
            raw_data: 爬蟲獲取的原始航班資料
            
        返回:
            轉換後的標準格式航班列表
        """
        if not raw_data:
            return []
        
        std_flights = []
        
        for flight in raw_data:
            try:
                # 獲取並格式化日期時間
                departure_time = flight.get('scheduled_departure_time', '')
                arrival_time = flight.get('scheduled_arrival_time', '')
                crawl_date = flight.get('crawl_date', datetime.datetime.now().strftime('%Y-%m-%d'))
                
                # 創建完整的日期時間字符串
                departure_datetime = self._combine_date_time(crawl_date, departure_time)
                arrival_datetime = self._combine_date_time(crawl_date, arrival_time)
                
                # 如果到達時間早於出發時間，可能是跨天航班，加一天
                if arrival_datetime and departure_datetime and arrival_datetime < departure_datetime:
                    arrival_datetime = arrival_datetime + datetime.timedelta(days=1)
                
                # 創建標準格式的航班數據
                std_flight = {
                    'flight_number': flight.get('flight_no', ''),
                    'airline_id': self.airline_id,
                    'departure_airport_code': flight.get('departure', ''),
                    'arrival_airport_code': flight.get('arrival', ''),
                    'scheduled_departure': departure_datetime,
                    'scheduled_arrival': arrival_datetime,
                    'flight_status': 'on_time',  # 德安航空爬蟲不提供航班狀態，預設為準時
                    'aircraft_type': 'DHC6',  # 德安航空使用DHC-6雙水欄渦輪螺旋槳飛機
                    'price': None,  # 德安航空爬蟲不提供價格
                    'booking_link': 'https://www.dailyair.com.tw/Page/Booking',
                    'scrape_date': datetime.datetime.now()
                }
                
                # 驗證數據
                if self.validate_flight_data(std_flight):
                    std_flights.append(std_flight)
                
            except Exception as e:
                self.logger.error(f"轉換航班數據時出錯: {e}")
        
        self.logger.info(f"轉換了 {len(std_flights)} 個德安航空航班為標準格式")
        return std_flights
    
    def _combine_date_time(self, date_str: str, time_str: str) -> Optional[datetime.datetime]:
        """
        合併日期和時間字符串為datetime對象
        
        參數:
            date_str: 日期字符串 (YYYY-MM-DD)
            time_str: 時間字符串 (HH:MM)
            
        返回:
            datetime對象，轉換失敗則返回None
        """
        try:
            if not date_str or not time_str:
                return None
            
            # 移除可能的空格
            date_str = date_str.strip()
            time_str = time_str.strip()
            
            # 轉換時間格式
            datetime_str = f"{date_str} {time_str}"
            return datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        except Exception as e:
            self.logger.error(f"合併日期時間時出錯: {date_str} {time_str} - {e}")
            return None