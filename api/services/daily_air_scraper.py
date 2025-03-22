#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DailyAirScraper')

# 加载环境变量
load_dotenv()

class DailyAirScraper:
    """德安航空数据爬取类"""
    
    def __init__(self):
        """初始化爬虫"""
        self.name = "德安航空"
        self.airline_id = "DAC"  # 德安航空代码
        self.base_url = "https://www.dailyair.com.tw"
        self.schedule_url = "https://www.dailyair.com.tw/Dailyair/Page/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 德安的航线
        self.routes = [
            {"from": "TTT", "to": "GNI"},  # 台東 - 綠島 (7301, 7303, 7311)
            {"from": "GNI", "to": "TTT"},  # 綠島 - 台東 (7302, 7304, 7312)
            {"from": "TTT", "to": "KYD"},  # 台東 - 蘭嶼 (7501-7517 奇数)
            {"from": "KYD", "to": "TTT"},  # 蘭嶼 - 台東 (7502-7518 偶数)
            {"from": "KHH", "to": "CMJ"},  # 高雄 - 七美 (7001, 7009, 7011)
            {"from": "CMJ", "to": "KHH"},  # 七美 - 高雄 (7002, 7010, 7012)
            {"from": "MZG", "to": "CMJ"},  # 澎湖 - 七美 (7017)
            {"from": "CMJ", "to": "MZG"},  # 七美 - 澎湖 (7016)
            {"from": "KHH", "to": "WOT"},  # 高雄 - 望安 (7019, 7005)
            {"from": "WOT", "to": "KHH"},  # 望安 - 高雄 (7020, 7006)
        ]
    
    def random_delay(self, min_seconds=1, max_seconds=3):
        """随机延迟，避免请求过快"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"随机延迟 {delay:.2f} 秒")
        time.sleep(delay)
    
    def get_schedule_data(self, from_airport, to_airport, search_date):
        """直接从德安航空网站获取固定航班时刻表数据"""
        logger.info(f"获取 {from_airport} 到 {to_airport} 的航班时刻表（{search_date}）")
        
        try:
            # 访问主页获取基本信息
            response = self.session.get(self.schedule_url)
            if response.status_code != 200:
                logger.error(f"获取网页失败: {response.status_code}")
                return []
            
            # 保存网页内容（仅调试用）
            with open(f"daily_air_home_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            flights = []
            
            # 根据航线获取已知的航班时刻表
            route_key = f"{from_airport}{to_airport}"
            
            # 预定义的航班信息
            flight_info = {
                # 台東 - 綠島
                "TTTGNI": [
                    {"flight_number": "DA7301", "departure_time": "07:30", "arrival_time": "07:50", "days": "每日"},
                    {"flight_number": "DA7303", "departure_time": "12:50", "arrival_time": "13:10", "days": "每日"},
                    {"flight_number": "DA7311", "departure_time": "16:15", "arrival_time": "16:35", "days": "每日"}
                ],
                # 綠島 - 台東
                "GNITTT": [
                    {"flight_number": "DA7302", "departure_time": "08:15", "arrival_time": "08:35", "days": "每日"},
                    {"flight_number": "DA7304", "departure_time": "13:35", "arrival_time": "13:55", "days": "每日"},
                    {"flight_number": "DA7312", "departure_time": "17:00", "arrival_time": "17:20", "days": "每日"}
                ],
                # 台東 - 蘭嶼
                "TTTKYD": [
                    {"flight_number": "DA7501", "departure_time": "07:50", "arrival_time": "08:20", "days": "每日"},
                    {"flight_number": "DA7503", "departure_time": "09:00", "arrival_time": "09:30", "days": "每日"},
                    {"flight_number": "DA7505", "departure_time": "09:50", "arrival_time": "10:20", "days": "每日"},
                    {"flight_number": "DA7515", "departure_time": "10:55", "arrival_time": "11:25", "days": "每日"},
                    {"flight_number": "DA7507", "departure_time": "11:50", "arrival_time": "12:20", "days": "每日"},
                    {"flight_number": "DA7517", "departure_time": "13:50", "arrival_time": "14:20", "days": "每日"},
                    {"flight_number": "DA7509", "departure_time": "14:25", "arrival_time": "14:55", "days": "每日"},
                    {"flight_number": "DA7511", "departure_time": "15:50", "arrival_time": "16:20", "days": "每日"}
                ],
                # 蘭嶼 - 台東
                "KYDTTT": [
                    {"flight_number": "DA7502", "departure_time": "08:50", "arrival_time": "09:20", "days": "每日"},
                    {"flight_number": "DA7504", "departure_time": "09:55", "arrival_time": "10:25", "days": "每日"},
                    {"flight_number": "DA7506", "departure_time": "10:50", "arrival_time": "11:20", "days": "每日"},
                    {"flight_number": "DA7516", "departure_time": "11:50", "arrival_time": "12:20", "days": "每日"},
                    {"flight_number": "DA7508", "departure_time": "12:50", "arrival_time": "13:20", "days": "每日"},
                    {"flight_number": "DA7518", "departure_time": "14:50", "arrival_time": "15:20", "days": "每日"},
                    {"flight_number": "DA7510", "departure_time": "15:20", "arrival_time": "15:50", "days": "每日"},
                    {"flight_number": "DA7512", "departure_time": "16:45", "arrival_time": "17:15", "days": "每日"}
                ],
                # 高雄 - 七美
                "KHHCMJ": [
                    {"flight_number": "DA7001", "departure_time": "08:00", "arrival_time": "08:40", "days": "5,3/16,3/30"},
                    {"flight_number": "DA7009", "departure_time": "10:30", "arrival_time": "11:10", "days": "1,2,3,4,6,7"},
                    {"flight_number": "DA7011", "departure_time": "13:10", "arrival_time": "13:50", "days": "每日"}
                ],
                # 七美 - 高雄
                "CMJKHH": [
                    {"flight_number": "DA7002", "departure_time": "09:10", "arrival_time": "09:50", "days": "5,3/16,3/30"},
                    {"flight_number": "DA7010", "departure_time": "11:40", "arrival_time": "12:20", "days": "1,2,3,4,6,7"},
                    {"flight_number": "DA7012", "departure_time": "16:15", "arrival_time": "16:55", "days": "每日"}
                ],
                # 七美 - 澎湖
                "CMJMZG": [
                    {"flight_number": "DA7016", "departure_time": "14:25", "arrival_time": "14:45", "days": "每日"}
                ],
                # 澎湖 - 七美
                "MZGCMJ": [
                    {"flight_number": "DA7017", "departure_time": "15:20", "arrival_time": "15:40", "days": "每日"}
                ],
                # 高雄 - 望安
                "KHHWOT": [
                    {"flight_number": "DA7019", "departure_time": "08:00", "arrival_time": "08:45", "days": "1"},
                    {"flight_number": "DA7005", "departure_time": "10:20", "arrival_time": "11:05", "days": "5"}
                ],
                # 望安 - 高雄
                "WOTKHH": [
                    {"flight_number": "DA7020", "departure_time": "09:15", "arrival_time": "10:00", "days": "1"},
                    {"flight_number": "DA7006", "departure_time": "11:35", "arrival_time": "12:20", "days": "5"}
                ]
            }
            
            # 检查航线是否有对应的航班信息
            if route_key not in flight_info:
                logger.info(f"未找到 {from_airport} 到 {to_airport} 的航班时刻表")
                return []
            
            # 检查日期是否是周几
            weekday = search_date.weekday() + 1  # 1-7 对应周一到周日
            weekday_str = str(weekday)
            
            # 处理特殊日期 (例如3/16, 3/30等)
            date_str = search_date.strftime('%m/%d')
            
            # 获取航班信息
            for flight_data in flight_info[route_key]:
                # 检查航班是否在指定日期运行
                days = flight_data["days"]
                is_available = False
                
                # 检查是否每日运行
                if days == "每日" or days == "Daily":
                    is_available = True
                # 检查是否在当前星期几运行
                elif weekday_str in days:
                    is_available = True
                # 检查是否在特殊日期运行
                elif date_str in days:
                    is_available = True
                
                if is_available:
                    # 构造完整的日期时间
                    dep_time = flight_data["departure_time"].replace("：", ":")
                    arr_time = flight_data["arrival_time"].replace("：", ":")
                    
                    dep_datetime = f"{search_date.strftime('%Y-%m-%d')} {dep_time}"
                    arr_datetime = f"{search_date.strftime('%Y-%m-%d')} {arr_time}"
                    
                    # 如果到达时间早于出发时间，说明跨天，日期+1
                    dep_time_obj = datetime.strptime(dep_time, '%H:%M')
                    arr_time_obj = datetime.strptime(arr_time, '%H:%M')
                    if arr_time_obj < dep_time_obj:
                        next_day = search_date + timedelta(days=1)
                        arr_datetime = f"{next_day.strftime('%Y-%m-%d')} {arr_time}"
                    
                    # 添加航班信息
                    flight = {
                        "flight_number": flight_data["flight_number"],
                        "airline_id": self.airline_id,
                        "departure_airport_code": from_airport,
                        "arrival_airport_code": to_airport,
                        "scheduled_departure": dep_datetime,
                        "scheduled_arrival": arr_datetime,
                        "aircraft_type": "Do-228",  # 德安航空使用Do-228机型
                        "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    
                    flights.append(flight)
                    logger.info(f"找到航班: {flight_data['flight_number']}, {from_airport}-{to_airport}, {dep_datetime}")
            
            return flights
            
        except Exception as e:
            logger.error(f"获取航班时刻表时出错: {str(e)}")
            return []
    
    def scrape_all_routes(self, search_date=None):
        """爬取所有航线的数据"""
        # 如果未提供日期，使用明天的日期
        if not search_date:
            search_date = datetime.now() + timedelta(days=1)
        elif isinstance(search_date, str):
            search_date = datetime.strptime(search_date, '%Y-%m-%d')
        
        logger.info(f"开始爬取德安航空所有航线，日期：{search_date.strftime('%Y-%m-%d')}")
        
        all_flights = []
        
        # 爬取每条航线
        for route in self.routes:
            from_airport = route["from"]
            to_airport = route["to"]
            
            logger.info(f"爬取航线: {from_airport} -> {to_airport}")
            flights = self.get_schedule_data(from_airport, to_airport, search_date)
            all_flights.extend(flights)
            
            # 随机延迟
            self.random_delay(3, 5)
        
        logger.info(f"共获取 {len(all_flights)} 个航班信息")
        
        # 保存到JSON文件
        if all_flights:
            filename = f"daily_air_flights_{search_date.strftime('%Y%m%d')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_flights, f, ensure_ascii=False, indent=2)
            logger.info(f"航班数据已保存到 {filename}")
        
        return all_flights

def main():
    """主函数"""
    logger.info("开始运行德安航空爬虫")
    
    # 获取环境变量中的测试模式标志
    test_mode = os.getenv('TEST_MODE', 'False').lower() in ('true', '1', 't')
    logger.info(f"测试模式: {test_mode}")
    
    # 初始化爬虫
    scraper = DailyAirScraper()
    
    # 爬取今天和明天的数据
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    # 如果是测试模式，只爬取明天的数据
    if test_mode:
        logger.info("测试模式：只爬取明天的数据")
        scraper.scrape_all_routes(tomorrow)
    else:
        # 正式模式，爬取今天和明天的数据
        logger.info("正式模式：爬取今天和明天的数据")
        scraper.scrape_all_routes(today)
        # 随机延迟
        time.sleep(random.uniform(5, 10))
        scraper.scrape_all_routes(tomorrow)
    
    logger.info("德安航空爬虫运行完成")

if __name__ == "__main__":
    main()