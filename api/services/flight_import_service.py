#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
航班導入服務
提供統一的介面來導入來自不同來源的航班資料
"""

import os
import datetime
import logging
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Type, Union

from api.services.providers.base import FlightProvider
from api.services.providers.aviation_stack_provider import AviationStackProvider
from api.services.providers.daily_air_provider import DailyAirProvider
from api.services.aviation_stack_importer import import_flight, get_import_statistics

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/flight_import_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('flight_import_service')

class FlightImportService:
    """
    航班導入服務
    統一管理從不同來源導入航班資料
    """
    
    def __init__(self):
        """初始化航班導入服務"""
        self.providers = {}
        self.register_default_providers()
    
    def register_default_providers(self):
        """註冊默認的航班資料提供者"""
        self.register_provider("aviation_stack", AviationStackProvider())
        self.register_provider("daily_air", DailyAirProvider())
        logger.info(f"已註冊 {len(self.providers)} 個航班資料提供者")
    
    def register_provider(self, name: str, provider: FlightProvider):
        """
        註冊航班資料提供者
        
        參數:
            name: 提供者名稱
            provider: 提供者實例
        """
        self.providers[name] = provider
        logger.info(f"註冊航班提供者: {name}")
    
    def get_provider(self, name: str) -> Optional[FlightProvider]:
        """
        獲取指定名稱的提供者
        
        參數:
            name: 提供者名稱
            
        返回:
            提供者實例，不存在則返回None
        """
        return self.providers.get(name)
    
    def list_providers(self) -> List[str]:
        """
        列出所有已註冊的提供者
        
        返回:
            提供者名稱列表
        """
        return list(self.providers.keys())
    
    def import_flights(
        self,
        provider_name: str,
        flight_date: str,
        limit: int = 100,
        **kwargs
    ) -> Tuple[int, int]:
        """
        導入指定提供者和日期的航班資料
        
        參數:
            provider_name: 提供者名稱
            flight_date: 航班日期 (YYYY-MM-DD)
            limit: 最大導入數量
            **kwargs: 其他參數
            
        返回:
            (成功導入數量, 總嘗試數量)
        """
        provider = self.get_provider(provider_name)
        if not provider:
            logger.error(f"未找到提供者: {provider_name}")
            return 0, 0
        
        logger.info(f"從 {provider_name} 導入 {flight_date} 的航班資料")
        
        try:
            # 獲取航班資料
            flights = provider.get_flights(flight_date=flight_date, **kwargs)
            
            # 限制數量
            if limit > 0 and len(flights) > limit:
                flights = flights[:limit]
            
            # 開始導入
            successful = 0
            total = len(flights)
            
            logger.info(f"開始導入 {total} 個航班...")
            
            for i, flight in enumerate(flights):
                if import_flight(flight):
                    successful += 1
                
                # 每導入10個航班顯示進度
                if (i + 1) % 10 == 0 or i == total - 1:
                    logger.info(f"進度: {i+1}/{total} ({successful} 成功)")
                
                # 隨機延遲，避免過快寫入
                time.sleep(random.uniform(0.1, 0.3))
            
            success_rate = (successful / total * 100) if total > 0 else 0
            logger.info(f"導入完成: {successful}/{total} 成功率: {success_rate:.2f}%")
            
            return successful, total
            
        except Exception as e:
            logger.error(f"導入航班時出錯: {e}")
            return 0, 0
    
    def import_multiple_providers(
        self,
        providers: List[str],
        flight_date: str,
        limit_per_provider: int = 50,
        **kwargs
    ) -> Dict[str, Tuple[int, int]]:
        """
        從多個提供者導入航班資料
        
        參數:
            providers: 提供者名稱列表
            flight_date: 航班日期 (YYYY-MM-DD)
            limit_per_provider: 每個提供者的最大導入數量
            **kwargs: 其他參數
            
        返回:
            包含每個提供者導入結果的字典 {提供者: (成功數, 總數)}
        """
        results = {}
        
        for provider_name in providers:
            logger.info(f"從提供者 {provider_name} 導入資料...")
            successful, total = self.import_flights(
                provider_name=provider_name,
                flight_date=flight_date,
                limit=limit_per_provider,
                **kwargs
            )
            results[provider_name] = (successful, total)
        
        return results
    
    def import_multiple_days(
        self,
        provider_name: str,
        start_date: str,
        days: int = 1,
        limit_per_day: int = 50,
        **kwargs
    ) -> Dict[str, Tuple[int, int]]:
        """
        導入多天的航班資料
        
        參數:
            provider_name: 提供者名稱
            start_date: 開始日期 (YYYY-MM-DD)
            days: 天數
            limit_per_day: 每天最大導入航班數
            **kwargs: 其他參數
            
        返回:
            包含每天導入結果的字典 {日期: (成功數, 總數)}
        """
        results = {}
        
        try:
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            
            for day in range(days):
                current_date = start_date_obj + datetime.timedelta(days=day)
                date_str = current_date.strftime('%Y-%m-%d')
                
                logger.info(f"導入日期 {date_str} 的航班...")
                
                successful, total = self.import_flights(
                    provider_name=provider_name,
                    flight_date=date_str,
                    limit=limit_per_day,
                    **kwargs
                )
                
                results[date_str] = (successful, total)
                
                # 日期之間的間隔，避免過載
                if day < days - 1:
                    logger.info(f"等待3秒後處理下一天...")
                    time.sleep(3)
            
            return results
            
        except Exception as e:
            logger.error(f"導入多天航班時出錯: {e}")
            return results
    
    def get_statistics(self, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        獲取導入統計資訊
        
        參數:
            start_date: 統計開始日期 (可選)
            end_date: 統計結束日期 (可選)
            
        返回:
            包含統計資訊的字典
        """
        return get_import_statistics(start_date=start_date, end_date=end_date)


# 單例實現
_service_instance = None

def get_service() -> FlightImportService:
    """
    獲取航班導入服務的單例實例
    
    返回:
        航班導入服務實例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = FlightImportService()
    return _service_instance