#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AviationStack航班資料提供者
從AviationStack API獲取航班資料
"""

import os
import datetime
import time
import random
from typing import Dict, List, Optional, Any, Tuple
import json

from api.services.providers.base import FlightProvider
from api.services.external_apis import (
    get_flights_for_configured_airlines_airports,
    transform_flight_data_for_db,
    generate_mock_flight_data,
    load_airlines_airports_config
)

class AviationStackProvider(FlightProvider):
    """AviationStack API提供者實現"""
    
    def __init__(self):
        """初始化AviationStack提供者"""
        super().__init__("AviationStack")
        self.config = load_airlines_airports_config()
        
    def get_flights(self, flight_date: str, **kwargs) -> List[Dict]:
        """
        獲取指定日期的航班資料
        
        參數:
            flight_date: 航班日期 (YYYY-MM-DD格式)
            **kwargs: 其他參數，可包含:
                limit_airlines: 限制查詢的航空公司列表
                limit_airports: 限制查詢的機場列表
                max_api_calls: 最大API調用次數
                use_cache: 是否使用緩存
                use_mock_data: 是否在無法從API獲取資料時使用模擬資料
                priority_routes: 優先查詢的航線列表
            
        返回:
            航班資料列表
        """
        self.logger.info(f"從AviationStack獲取 {flight_date} 的航班數據")
        
        # 設置默認值
        limit_airlines = kwargs.get('limit_airlines')
        limit_airports = kwargs.get('limit_airports')
        max_api_calls = kwargs.get('max_api_calls', 20)
        use_cache = kwargs.get('use_cache', True)
        use_mock_data = kwargs.get('use_mock_data', False)
        priority_routes = kwargs.get('priority_routes')
        
        # 調用API獲取航班
        flights = get_flights_for_configured_airlines_airports(
            flight_date=flight_date,
            limit_airlines=limit_airlines,
            limit_airports=limit_airports,
            max_api_calls=max_api_calls,
            use_cache=use_cache,
            use_mock_data=use_mock_data,
            priority_routes=priority_routes
        )
        
        self.logger.info(f"從AviationStack獲取到 {len(flights)} 個航班")
        return flights
    
    def transform_data(self, raw_data: Any) -> List[Dict]:
        """
        將原始資料轉換為標準格式
        這個方法對於AviationStack不需要額外處理，因為get_flights_for_configured_airlines_airports
        已經返回了轉換後的標準格式
        
        參數:
            raw_data: 原始API回應
            
        返回:
            轉換後的標準格式航班列表
        """
        # 確保資料是字典列表格式
        if isinstance(raw_data, list):
            return raw_data
        
        # 如果是單一API回應
        if isinstance(raw_data, dict) and 'data' in raw_data:
            flights = []
            for flight_data in raw_data.get('data', []):
                db_record = transform_flight_data_for_db(flight_data)
                flights.append(db_record)
            return flights
        
        self.logger.warning("無法識別的資料格式")
        return []
    
    def generate_mock_flights(self, flight_date: str, **kwargs) -> List[Dict]:
        """
        生成模擬航班數據
        
        參數:
            flight_date: 航班日期 (YYYY-MM-DD)
            **kwargs: 其他參數
            
        返回:
            模擬航班數據列表
        """
        # 設置默認值
        limit_airlines = kwargs.get('limit_airlines')
        limit_airports = kwargs.get('limit_airports')
        priority_routes = kwargs.get('priority_routes')
        
        # 使用配置中的航空公司和機場
        airlines = limit_airlines or self.config.get('airlines', [])[:5]
        airports = limit_airports or self.config.get('airports', [])[:10]
        
        # 設置默認優先航線
        if not priority_routes:
            priority_routes = [
                ('TPE', 'HKG'), ('TPE', 'NRT'), ('TPE', 'HND'), 
                ('TPE', 'ICN'), ('TPE', 'BKK'), ('TPE', 'SIN')
            ]
        
        self.logger.info(f"生成 {flight_date} 的模擬航班數據")
        mock_flights = generate_mock_flight_data(
            flight_date=flight_date,
            airlines=airlines,
            airports=airports,
            priority_routes=priority_routes
        )
        
        self.logger.info(f"生成了 {len(mock_flights)} 個模擬航班")
        return mock_flights