#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from daily_air_scraper import DailyAirScraper

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TestDailyAir')

# 加载环境变量
load_dotenv()

def test_daily_air_scraper():
    """测试德安航空爬虫"""
    logger.info("开始测试德安航空爬虫...")
    
    # 将测试模式设置为True
    os.environ['TEST_MODE'] = 'True'
    
    # 初始化爬虫
    scraper = DailyAirScraper()
    
    # 使用特定日期进行测试 (例如明天)
    tomorrow = datetime.now() + timedelta(days=1)
    logger.info(f"测试日期: {tomorrow.strftime('%Y-%m-%d')}")
    
    # 仅测试一条航线
    test_route = scraper.routes[0]  # 第一条航线：松山 - 馬公
    from_airport = test_route["from"]
    to_airport = test_route["to"]
    
    logger.info(f"测试航线: {from_airport} -> {to_airport}")
    
    # 执行爬取
    flights = scraper.get_schedule_data(from_airport, to_airport, tomorrow)
    
    # 输出结果
    logger.info(f"获取到 {len(flights)} 个航班")
    for flight in flights:
        logger.info(f"航班: {flight['flight_number']}, {flight['departure_airport_code']}-{flight['arrival_airport_code']}, "
                   f"出发: {flight['scheduled_departure']}, 到达: {flight['scheduled_arrival']}")
    
    logger.info("德安航空爬虫测试完成")
    return flights

if __name__ == "__main__":
    test_daily_air_scraper()