#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from dotenv import load_dotenv
from daily_air_improved_scraper import DailyAirImprovedScraper

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TestDailyAirImproved')

# 加载环境变量
load_dotenv()

def main():
    """测试德安航空爬虫改进版"""
    # 强制设置测试模式
    os.environ['TEST_MODE'] = 'True'
    logger.info("运行在测试模式")
    
    # 创建爬虫实例
    scraper = DailyAirImprovedScraper()
    
    # 抓取航班时刻表
    logger.info("开始测试抓取航班时刻表...")
    flight_schedule = scraper.scrape_flight_schedule()
    
    if flight_schedule:
        logger.info(f"成功抓取 {len(flight_schedule)} 个航班信息")
        
        # 打印部分航班信息
        logger.info("航班信息示例:")
        for i, flight in enumerate(flight_schedule[:3]):  # 只显示前3个
            logger.info(f"航班 {i+1}: {flight}")
    else:
        logger.error("未能抓取到航班信息")
    
    # 测试生成未来三天的航班
    logger.info("开始测试生成未来3天的航班...")
    flights = scraper.run(days=3)
    
    if flights:
        logger.info(f"成功生成 {len(flights)} 个未来航班")
        
        # 打印航线统计
        route_counts = {}
        for flight in flights:
            route = f"{flight['departure_airport_code']}-{flight['arrival_airport_code']}"
            if route not in route_counts:
                route_counts[route] = 0
            route_counts[route] += 1
        
        logger.info("航线统计:")
        for route, count in sorted(route_counts.items()):
            logger.info(f"  - {route}: {count} 个航班")
        
        # 打印部分生成的航班
        logger.info("生成的航班示例:")
        for i, flight in enumerate(flights[:3]):  # 只显示前3个
            logger.info(f"航班 {i+1}: {flight}")
    else:
        logger.error("未能生成未来航班")
    
    logger.info("测试完成")
    return flights

if __name__ == "__main__":
    main()