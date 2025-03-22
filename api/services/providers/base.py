#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
航班資料提供者的基礎類別
所有航班資料來源都應該繼承並實現這個基類
"""

import datetime
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('flight_provider')

class FlightProvider(ABC):
    """
    航班資料提供者抽象基類
    定義了所有航班資料來源必須實現的介面
    """
    
    def __init__(self, name: str):
        """
        初始化提供者
        
        參數:
            name: 提供者名稱
        """
        self.name = name
        self.logger = logging.getLogger(f'flight_provider.{name.lower()}')
    
    @abstractmethod
    def get_flights(self, flight_date: str, **kwargs) -> List[Dict]:
        """
        獲取指定日期的航班資料
        
        參數:
            flight_date: 航班日期 (YYYY-MM-DD格式)
            **kwargs: 其他參數
            
        返回:
            航班資料列表
        """
        pass
    
    @abstractmethod
    def transform_data(self, raw_data: Any) -> List[Dict]:
        """
        將原始資料轉換為標準格式
        
        參數:
            raw_data: 原始資料
            
        返回:
            轉換後的標準格式航班列表
        """
        pass
    
    def get_provider_info(self) -> Dict[str, str]:
        """
        獲取提供者資訊
        
        返回:
            提供者資訊字典
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "version": "1.0",
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    def validate_flight_data(self, flight: Dict) -> bool:
        """
        驗證航班資料是否符合格式要求
        
        參數:
            flight: 航班資料字典
            
        返回:
            是否有效
        """
        required_fields = ['flight_number', 'airline_id', 
                          'departure_airport_code', 'arrival_airport_code', 
                          'scheduled_departure']
        
        for field in required_fields:
            if field not in flight or flight[field] is None:
                self.logger.warning(f"航班缺少必要欄位: {field}")
                return False
        
        return True