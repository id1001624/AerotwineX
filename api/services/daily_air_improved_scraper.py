#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import logging
import os
import json
import pyodbc
from datetime import datetime, timedelta
import time
import random
import re
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DailyAirImprovedScraper')

# 加载环境变量
load_dotenv()

class DailyAirImprovedScraper:
    """
    德安航空网站爬虫改进版
    用于获取德安航空的航班信息并存入数据库
    """
    
    def __init__(self):
        """初始化爬虫"""
        self.name = "德安航空"
        self.airline_id = "DAC"  # 航空公司代码
        self.base_url = "https://www.dailyair.com.tw/Dailyair/Page/"
        self.session = requests.Session()
        
        # 设置请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive'
        })
        
        # 测试模式标志
        self.test_mode = os.getenv('TEST_MODE', 'False').lower() == 'true'
        
        # 航线信息
        self.routes = {
            # 台东-兰屿路线
            "TTT-KYD": {"dep": "TTT", "arr": "KYD", "route_name_zh": "台東蘭嶼", "route_name_en": "TaitungLanyu"},
            "KYD-TTT": {"dep": "KYD", "arr": "TTT", "route_name_zh": "蘭嶼台東", "route_name_en": "LanyuTaitung"},
            
            # 台东-绿岛路线
            "TTT-GNI": {"dep": "TTT", "arr": "GNI", "route_name_zh": "台東綠島", "route_name_en": "TaitungLudao"},
            "GNI-TTT": {"dep": "GNI", "arr": "TTT", "route_name_zh": "綠島台東", "route_name_en": "LudaoTaitung"},
            
            # 高雄-七美路线
            "KHH-CMJ": {"dep": "KHH", "arr": "CMJ", "route_name_zh": "高雄七美", "route_name_en": "KaohsiungQimei"},
            "CMJ-KHH": {"dep": "CMJ", "arr": "KHH", "route_name_zh": "七美高雄", "route_name_en": "QimeiKaohsiung"},
            
            # 澎湖-七美路线
            "MZG-CMJ": {"dep": "MZG", "arr": "CMJ", "route_name_zh": "澎湖七美", "route_name_en": "PenghuQimei"},
            "CMJ-MZG": {"dep": "CMJ", "arr": "MZG", "route_name_zh": "七美澎湖", "route_name_en": "QimeiPenghu"},
            
            # 高雄-望安路线
            "KHH-WOT": {"dep": "KHH", "arr": "WOT", "route_name_zh": "高雄望安", "route_name_en": "KaohsiungWang-an"},
            "WOT-KHH": {"dep": "WOT", "arr": "KHH", "route_name_zh": "望安高雄", "route_name_en": "Wang-anKaohsiung"}
        }
        
    def random_delay(self, min_seconds=1, max_seconds=3):
        """随机延迟，避免请求过快"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"等待 {delay:.2f} 秒")
        time.sleep(delay)
    
    def scrape_flight_schedule(self):
        """抓取德安航空网站的航班时刻表"""
        logger.info(f"开始抓取{self.name}航班时刻表...")
        
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 保存HTML以供调试
            debug_file = f"daily_air_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            logger.info(f"已保存HTML到 {debug_file}")
            
            # 查找所有表格
            all_flights = []
            
            # 遍历所有可能的航线
            for route_key, route_info in self.routes.items():
                logger.info(f"查找航线: {route_info['route_name_zh']} ({route_key})")
                route_name_zh = route_info['route_name_zh']
                route_name_en = route_info['route_name_en']
                
                # 查找包含航线名称的表格
                tables = []
                for table in soup.find_all('table'):
                    # 检查表格前面的元素是否包含航线名称
                    prev_element = table.find_previous(['h3', 'h4', 'p', 'div'])
                    if prev_element and (route_name_zh in prev_element.text or route_name_en in prev_element.text):
                        tables.append(table)
                        logger.info(f"找到航线表格: {route_name_zh}")
                        break
                
                if not tables:
                    logger.warning(f"没有找到航线 {route_name_zh} 的表格")
                    continue
                
                # 处理找到的表格
                for table in tables:
                    # 查找所有行
                    rows = table.find_all('tr')
                    
                    # 跳过表头
                    for row in rows[1:]:  # 从第2行开始（索引1）
                        cells = row.find_all(['td'])
                        if len(cells) >= 4:  # 确保有足够的单元格
                            flight_number = cells[0].text.strip()
                            departure_time = cells[1].text.strip().replace('：', ':')
                            arrival_time = cells[2].text.strip().replace('：', ':')
                            flight_days = cells[3].text.strip()
                            
                            # 添加到航班列表
                            flight_info = {
                                "flight_number": flight_number,
                                "complete_flight_number": f"{self.airline_id}{flight_number}",
                                "airline_id": self.airline_id,
                                "departure_airport_code": route_info["dep"],
                                "arrival_airport_code": route_info["arr"],
                                "departure_time": departure_time,
                                "arrival_time": arrival_time,
                                "flight_days": flight_days,
                                "route": route_key
                            }
                            all_flights.append(flight_info)
                            logger.info(f"添加航班: {flight_info['complete_flight_number']} - {route_info['dep']} -> {route_info['arr']} ({departure_time} -> {arrival_time})")
            
            logger.info(f"共抓取到 {len(all_flights)} 个航班信息")
            return all_flights
            
        except Exception as e:
            logger.error(f"抓取航班时刻表时出错: {str(e)}")
            return []
    
    def generate_flight_schedule(self, flight_info, target_date):
        """根据航班信息和目标日期生成具体航班计划"""
        # 解析航班日期规则
        is_flight_day = False
        
        # 检查是否为每日航班
        if "每日" in flight_info["flight_days"] or "Daily" in flight_info["flight_days"]:
            is_flight_day = True
        else:
            # 检查是否是特定日期的航班（如 "3/16（日）"）
            date_patterns = re.findall(r'(\d+)/(\d+)（[一二三四五六日]）', flight_info["flight_days"])
            if date_patterns:
                for month, day in date_patterns:
                    month = int(month)
                    day = int(day)
                    if target_date.month == month and target_date.day == day:
                        is_flight_day = True
                        break
            
            # 检查是否是特定星期几的航班（如 "1.2.3.4.5.6.7"，分别代表周一到周日）
            weekday_pattern = re.findall(r'[1-7]', flight_info["flight_days"])
            if weekday_pattern:
                # 将datetime星期几（0-6，周一为0）转换为1-7格式（周一为1）
                target_weekday = (target_date.weekday() + 1) % 7
                if target_weekday == 0:  # 星期日
                    target_weekday = 7
                
                if str(target_weekday) in weekday_pattern:
                    is_flight_day = True
        
        if not is_flight_day:
            return None
        
        # 解析时间
        departure_hour, departure_minute = map(int, flight_info["departure_time"].split(":"))
        arrival_hour, arrival_minute = map(int, flight_info["arrival_time"].split(":"))
        
        # 生成完整的日期时间
        scheduled_departure = datetime(
            target_date.year, target_date.month, target_date.day, 
            departure_hour, departure_minute
        )
        
        scheduled_arrival = datetime(
            target_date.year, target_date.month, target_date.day, 
            arrival_hour, arrival_minute
        )
        
        # 处理跨天情况（如果到达时间早于出发时间）
        if scheduled_arrival < scheduled_departure:
            scheduled_arrival += timedelta(days=1)
        
        return {
            "flight_number": flight_info["complete_flight_number"],
            "airline_id": self.airline_id,
            "departure_airport_code": flight_info["departure_airport_code"],
            "arrival_airport_code": flight_info["arrival_airport_code"],
            "scheduled_departure": scheduled_departure.strftime("%Y-%m-%d %H:%M:%S"),
            "scheduled_arrival": scheduled_arrival.strftime("%Y-%m-%d %H:%M:%S"),
            "aircraft_type": "DO-228",  # 德安航空使用的机型
            "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def save_to_database(self, flights):
        """将航班信息保存到数据库"""
        if self.test_mode:
            logger.info("测试模式: 不保存到数据库")
            return
        
        try:
            # 获取数据库连接字符串
            connection_string = os.getenv('DB_CONNECTION_STRING')
            if not connection_string:
                logger.error("未设置数据库连接字符串")
                return
            
            # 连接到数据库
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            
            # 准备批量插入
            inserted_count = 0
            for flight in flights:
                # 检查是否已存在相同航班
                check_query = """
                SELECT COUNT(*) FROM TempFlights 
                WHERE flight_number = ? AND scheduled_departure = ?
                """
                cursor.execute(check_query, 
                              (flight["flight_number"], flight["scheduled_departure"]))
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # 插入新航班
                    insert_query = """
                    INSERT INTO TempFlights (
                        flight_number, airline_id, departure_airport_code, 
                        arrival_airport_code, scheduled_departure, scheduled_arrival, 
                        aircraft_type, scrape_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_query, 
                                  (flight["flight_number"], flight["airline_id"],
                                   flight["departure_airport_code"], flight["arrival_airport_code"],
                                   flight["scheduled_departure"], flight["scheduled_arrival"],
                                   flight["aircraft_type"], flight["scrape_date"]))
                    inserted_count += 1
            
            # 提交事务
            conn.commit()
            logger.info(f"成功将 {inserted_count} 个航班信息保存到数据库（共 {len(flights)} 个航班）")
            
            # 关闭连接
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存到数据库时出错: {str(e)}")
    
    def save_to_json(self, data, filename=None):
        """保存数据为JSON文件"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'daily_air_flights_{timestamp}.json'
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存数据时出错: {e}")
    
    def run(self, days=7):
        """运行爬虫，抓取未来几天的航班信息"""
        try:
            # 抓取基本航班时刻表
            all_flight_info = self.scrape_flight_schedule()
            if not all_flight_info:
                logger.error("没有获取到航班信息")
                return []
            
            # 保存原始航班表数据
            self.save_to_json(all_flight_info, 'daily_air_raw_flights.json')
            
            # 生成未来几天的具体航班
            all_flights = []
            today = datetime.now()
            
            for day_offset in range(days):
                target_date = today + timedelta(days=day_offset)
                logger.info(f"生成 {target_date.strftime('%Y-%m-%d')} 的航班计划")
                
                for flight_info in all_flight_info:
                    flight = self.generate_flight_schedule(flight_info, target_date)
                    if flight:
                        all_flights.append(flight)
                
                # 在处理不同日期之间添加延迟
                if day_offset < days - 1:
                    self.random_delay(0.5, 1.5)
            
            logger.info(f"共生成 {len(all_flights)} 个航班计划")
            
            # 保存生成的航班数据
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.save_to_json(all_flights, f'daily_air_flights_{timestamp}.json')
            
            # 保存到数据库
            self.save_to_database(all_flights)
            
            return all_flights
            
        except Exception as e:
            logger.error(f"运行爬虫时出错: {str(e)}")
            return []


def main():
    # 检查测试模式
    test_mode = os.getenv('TEST_MODE', 'False').lower() == 'true'
    if test_mode:
        logger.info("运行在测试模式")
    
    # 创建爬虫实例并运行
    scraper = DailyAirImprovedScraper()
    flights = scraper.run(days=7)  # 抓取未来7天的航班
    
    # 输出结果统计
    route_counts = {}
    
    for flight in flights:
        route = f"{flight['departure_airport_code']}-{flight['arrival_airport_code']}"
        
        if route not in route_counts:
            route_counts[route] = 0
        route_counts[route] += 1
    
    logger.info("航线统计:")
    for route, count in route_counts.items():
        logger.info(f"  - {route}: {count} 个航班")
    
    logger.info(f"共抓取 {len(flights)} 个航班信息")
    return flights


if __name__ == "__main__":
    main()