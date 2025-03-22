import requests
import logging
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timedelta
import time
import random

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyAirDirectCrawler")

class DailyAirDirectCrawler:
    """
    德安航空直接爬虫
    通过直接访问官网获取最新航班时刻表
    """
    
    def __init__(self):
        self.base_url = "https://www.dailyair.com.tw"
        self.time_table_url = "https://www.dailyair.com.tw/Dailyair/Page/Flight-Schedule?a=Flight-Schedule"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # 机场代码映射
        self.airport_code_map = {
            "台東": "TTT",
            "蘭嶼": "KYD", 
            "綠島": "GNI",
            "高雄": "KHH", 
            "七美": "CMJ", 
            "望安": "WOT",
            "澎湖": "MZG",
            "馬公": "MZG"
        }
        
        # 路线映射
        self.route_map = {
            "台東蘭嶼": {"from": "TTT", "to": "KYD"},
            "蘭嶼台東": {"from": "KYD", "to": "TTT"},
            "台東綠島": {"from": "TTT", "to": "GNI"},
            "綠島台東": {"from": "GNI", "to": "TTT"},
            "高雄七美": {"from": "KHH", "to": "CMJ"},
            "七美高雄": {"from": "CMJ", "to": "KHH"},
            "七美澎湖": {"from": "CMJ", "to": "MZG"},
            "澎湖七美": {"from": "MZG", "to": "CMJ"},
            "高雄望安": {"from": "KHH", "to": "WOT"},
            "望安高雄": {"from": "WOT", "to": "KHH"}
        }
        
        # 航空公司信息
        self.airline_id = "EBC"
        self.airline_name = "德安航空"
        
        # 创建会话对象
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        logger.info("德安航空直接爬虫初始化完成")
    
    def random_delay(self, min_seconds=1, max_seconds=3):
        """引入随机延迟以避免被封IP"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"随机延迟 {delay:.2f} 秒")
        time.sleep(delay)
    
    def get_flight_tables(self):
        """
        获取航班时刻表HTML内容
        
        Returns:
            str: 网页HTML内容
        """
        try:
            logger.info(f"获取德安航空时刻表页面: {self.time_table_url}")
            self.random_delay(2, 4)
            response = self.session.get(self.time_table_url, timeout=30)
            response.raise_for_status()
            
            # 保存响应内容用于调试
            debug_dir = "debug_info"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_path = os.path.join(debug_dir, f"dailyair_timetable_{timestamp}.html")
            
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"已保存时刻表HTML至: {html_path}")
            
            return response.text
        except Exception as e:
            logger.error(f"获取时刻表页面时出错: {str(e)}")
            return None
    
    def parse_flight_tables(self, html_content):
        """
        解析HTML内容中的航班时刻表
        
        Args:
            html_content: HTML内容
            
        Returns:
            list: 航班信息列表
        """
        if not html_content:
            logger.error("HTML内容为空，无法解析")
            return []
        
        flights = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找所有表格
        tables = soup.find_all('table')
        logger.info(f"找到 {len(tables)} 个表格")
        
        for table_idx, table in enumerate(tables):
            try:
                # 查找表格标题，通常在表格之前的文本中
                title = None
                prev_element = table.find_previous()
                while prev_element and not title:
                    if prev_element.string and prev_element.string.strip():
                        title = prev_element.string.strip()
                    prev_element = prev_element.find_previous()
                
                if not title:
                    # 尝试从表格caption中获取
                    caption = table.find('caption')
                    if caption:
                        title = caption.get_text().strip()
                
                # 尝试从表格内的第一行获取具有中英文的路线信息
                first_row = table.find('tr')
                if first_row:
                    first_cell = first_row.find('th') or first_row.find('td')
                    if first_cell and first_cell.get_text().strip():
                        text = first_cell.get_text().strip()
                        # 检查是否包含航线信息格式 (如 "台東蘭嶼" 或 "台東蘭嶼（TaitungLanyu）")
                        for route in self.route_map.keys():
                            if route in text:
                                title = route
                                break
                
                if not title:
                    logger.warning(f"无法确定表格 {table_idx+1} 的航线信息，跳过")
                    continue
                
                # 尝试从标题中提取航线信息
                route = None
                for route_name in self.route_map.keys():
                    if route_name in title:
                        route = route_name
                        break
                
                if not route:
                    logger.warning(f"表格 {table_idx+1} 标题 '{title}' 无法识别航线，跳过")
                    continue
                
                logger.info(f"解析航线: {route} (表格 {table_idx+1})")
                origin_code = self.route_map[route]["from"]
                destination_code = self.route_map[route]["to"]
                
                # 获取航线的中文名称
                origin_name = None
                destination_name = None
                for airport_name, code in self.airport_code_map.items():
                    if code == origin_code:
                        origin_name = airport_name
                    if code == destination_code:
                        destination_name = airport_name
                
                # 解析表格中的航班信息
                rows = table.find_all('tr')
                
                # 查找表头行
                header_row = None
                for i, row in enumerate(rows):
                    cells = row.find_all(['th', 'td'])
                    if cells and any("班次" in cell.get_text() or "Flight No" in cell.get_text() for cell in cells):
                        header_row = i
                        break
                
                if header_row is None:
                    logger.warning(f"无法在表格 {table_idx+1} 中找到表头行，跳过")
                    continue
                
                # 提取表头列映射
                headers = rows[header_row].find_all(['th', 'td'])
                column_map = {}
                for i, header in enumerate(headers):
                    text = header.get_text().strip().lower()
                    if "班次" in text or "flight no" in text:
                        column_map["flight_number"] = i
                    elif "離場" in text or "departure" in text:
                        column_map["departure_time"] = i
                    elif "到達" in text or "arrival" in text:
                        column_map["arrival_time"] = i
                    elif "飛行日期" in text or "date" in text:
                        column_map["days_operated"] = i
                
                # 检查是否找到必要的列
                required_columns = ["flight_number", "departure_time", "arrival_time"]
                if not all(col in column_map for col in required_columns):
                    logger.warning(f"表格 {table_idx+1} 缺少必要列: {[col for col in required_columns if col not in column_map]}")
                    continue
                
                # 解析数据行
                for i in range(header_row + 1, len(rows)):
                    row = rows[i]
                    cells = row.find_all(['th', 'td'])
                    
                    # 跳过空行或英文重复行
                    if len(cells) < len(column_map) or not cells[column_map["flight_number"]].get_text().strip():
                        continue
                    
                    try:
                        # 提取航班号
                        flight_number = cells[column_map["flight_number"]].get_text().strip()
                        
                        # 标准化航班号格式
                        if not flight_number.startswith("DA"):
                            flight_number = "DA" + flight_number
                        
                        # 提取出发和到达时间
                        departure_time = cells[column_map["departure_time"]].get_text().strip()
                        arrival_time = cells[column_map["arrival_time"]].get_text().strip()
                        
                        # 提取运营日期
                        days_operated = "每日"  # 默认值
                        if "days_operated" in column_map and len(cells) > column_map["days_operated"]:
                            days_operated = cells[column_map["days_operated"]].get_text().strip()
                            if not days_operated:
                                days_operated = "每日"
                        
                        # 为日期字段设置当前日期（实际应用中会设置为适当的日期）
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        
                        # 创建航班记录
                        flight = {
                            "flight_number": flight_number,
                            "airline": self.airline_name,
                            "airline_code": self.airline_id,
                            "origin_airport": origin_code,
                            "origin_name": origin_name,
                            "destination_airport": destination_code,
                            "destination_name": destination_name,
                            "departure_time": f"{today_str} {departure_time}:00",
                            "arrival_time": f"{today_str} {arrival_time}:00",
                            "days_operated": days_operated,
                            "price": None,  # 价格需要额外请求
                            "source": "direct_web_scraping"
                        }
                        
                        flights.append(flight)
                        logger.debug(f"解析到航班: {flight_number}, {origin_code} -> {destination_code}, {departure_time}")
                    
                    except Exception as e:
                        logger.error(f"解析表格 {table_idx+1} 第 {i+1} 行时出错: {str(e)}")
                        continue
            
            except Exception as e:
                logger.error(f"解析表格 {table_idx+1} 时出错: {str(e)}")
        
        logger.info(f"共解析到 {len(flights)} 个航班")
        return flights
    
    def adjust_flight_dates(self, flights, date_str):
        """
        调整航班日期为指定日期
        
        Args:
            flights: 航班列表
            date_str: 目标日期字符串 (YYYY-MM-DD)
            
        Returns:
            list: 调整日期后的航班列表
        """
        adjusted_flights = []
        
        # 解析目标日期
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        target_day_of_week = (target_date.weekday() + 1) % 7 + 1  # 转换为1-7表示周一到周日
        
        for flight in flights:
            # 检查该航班在目标日期是否运营
            days_operated = flight["days_operated"]
            
            # 检查航班是否在目标日期运营
            is_operating = False
            
            # 处理常见的运营日期格式
            if days_operated == "每日" or days_operated == "Daily":
                is_operating = True
            elif any(str(target_day_of_week) == day for day in days_operated.split('.')):
                is_operating = True
            elif target_day_of_week in [int(d) for d in re.findall(r'\d+', days_operated)]:
                is_operating = True
            
            # 如果航班在目标日期运营，则添加到结果列表
            if is_operating:
                # 拷贝航班信息并更新日期
                flight_copy = flight.copy()
                
                # 更新出发和到达时间的日期部分
                dep_time = flight_copy["departure_time"].split(" ")[1]
                arr_time = flight_copy["arrival_time"].split(" ")[1]
                
                flight_copy["departure_time"] = f"{date_str} {dep_time}"
                flight_copy["arrival_time"] = f"{date_str} {arr_time}"
                
                adjusted_flights.append(flight_copy)
        
        logger.info(f"日期 {date_str} 有 {len(adjusted_flights)} 个航班")
        return adjusted_flights
    
    def get_flights_by_date(self, date_str):
        """
        获取指定日期的航班信息
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            list: 航班信息列表
        """
        logger.info(f"获取德安航空 {date_str} 的航班数据")
        
        # 获取时刻表页面内容
        html_content = self.get_flight_tables()
        
        if not html_content:
            logger.warning("无法获取时刻表页面，使用备用数据")
            return self.get_hardcoded_flights(date_str)
        
        # 解析航班信息
        flights = self.parse_flight_tables(html_content)
        
        if not flights:
            logger.warning("未能从页面解析到航班信息，使用备用数据")
            return self.get_hardcoded_flights(date_str)
        
        # 调整航班日期
        flights = self.adjust_flight_dates(flights, date_str)
        
        # 保存结果到JSON文件
        self.save_flights_to_json(flights, date_str)
        
        return flights
    
    def get_hardcoded_flights(self, date_str):
        """
        获取硬编码的航班信息（当爬虫失败时使用）
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            list: 航班信息列表
        """
        logger.info("使用硬编码航班数据")
        
        flights = [
            # 台东 - 兰屿航线
            {
                "flight_number": "DA7501",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "KYD",
                "destination_name": "蘭嶼",
                "departure_time": f"{date_str} 07:50:00",
                "arrival_time": f"{date_str} 08:20:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7503",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "KYD",
                "destination_name": "蘭嶼",
                "departure_time": f"{date_str} 09:00:00",
                "arrival_time": f"{date_str} 09:30:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7505",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "KYD",
                "destination_name": "蘭嶼",
                "departure_time": f"{date_str} 09:50:00",
                "arrival_time": f"{date_str} 10:20:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7515",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "KYD",
                "destination_name": "蘭嶼",
                "departure_time": f"{date_str} 10:55:00",
                "arrival_time": f"{date_str} 11:25:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            # 兰屿 - 台东航线
            {
                "flight_number": "DA7502",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "KYD",
                "origin_name": "蘭嶼",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{date_str} 08:50:00",
                "arrival_time": f"{date_str} 09:20:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7504",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "KYD",
                "origin_name": "蘭嶼",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{date_str} 09:55:00",
                "arrival_time": f"{date_str} 10:25:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            # 台东 - 绿岛航线
            {
                "flight_number": "DA7301",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "GNI",
                "destination_name": "綠島",
                "departure_time": f"{date_str} 07:30:00",
                "arrival_time": f"{date_str} 07:50:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7303",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "GNI",
                "destination_name": "綠島",
                "departure_time": f"{date_str} 12:50:00",
                "arrival_time": f"{date_str} 13:10:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            # 绿岛 - 台东航线
            {
                "flight_number": "DA7302",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "GNI",
                "origin_name": "綠島",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{date_str} 08:15:00",
                "arrival_time": f"{date_str} 08:35:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7304",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "GNI",
                "origin_name": "綠島",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{date_str} 13:35:00",
                "arrival_time": f"{date_str} 13:55:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
        ]
        
        return flights
    
    def save_flights_to_json(self, flights, date_str):
        """
        保存航班信息到JSON文件
        
        Args:
            flights: 航班列表
            date_str: 日期字符串
        """
        # 创建输出目录
        output_dir = "flight_data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录: {output_dir}")
        
        # 保存文件
        output_file = os.path.join(output_dir, f"dailyair_direct_flights_{date_str}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(flights, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存 {len(flights)} 个航班数据至 {output_file}")
    
    def save_to_database(self, flights, connection_string=None):
        """
        将航班数据保存到数据库
        
        Args:
            flights: 航班列表
            connection_string: 数据库连接字符串，如果为None则使用环境变量
        
        Returns:
            bool: 是否成功保存
        """
        try:
            import pyodbc
            from dotenv import load_dotenv
            
            # 加载环境变量
            load_dotenv()
            
            # 获取数据库连接字符串
            if not connection_string:
                connection_string = os.getenv("DB_CONNECTION_STRING")
                if not connection_string:
                    logger.error("未提供数据库连接字符串，且环境变量DB_CONNECTION_STRING未设置")
                    return False
            
            logger.info(f"连接到数据库: {connection_string.split(';')[1] if ';' in connection_string else '(隐藏)'}")
            
            # 建立数据库连接
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            
            # 插入或更新航班数据
            insert_count = 0
            update_count = 0
            
            for flight in flights:
                # 检查航班是否已存在
                check_sql = """
                SELECT COUNT(*) FROM flights 
                WHERE flight_number = ? AND scheduled_departure = ?
                """
                
                departure_time = datetime.strptime(flight["departure_time"], "%Y-%m-%d %H:%M:%S")
                arrival_time = datetime.strptime(flight["arrival_time"], "%Y-%m-%d %H:%M:%S")
                
                cursor.execute(check_sql, (flight["flight_number"], departure_time))
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    # 更新现有航班
                    update_sql = """
                    UPDATE flights SET
                        airline_id = ?,
                        departure_airport_code = ?,
                        arrival_airport_code = ?,
                        scheduled_arrival = ?,
                        updated_at = GETDATE()
                    WHERE flight_number = ? AND scheduled_departure = ?
                    """
                    
                    cursor.execute(update_sql, (
                        flight["airline_code"],
                        flight["origin_airport"],
                        flight["destination_airport"],
                        arrival_time,
                        flight["flight_number"],
                        departure_time
                    ))
                    update_count += 1
                else:
                    # 插入新航班
                    insert_sql = """
                    INSERT INTO flights (
                        flight_number, scheduled_departure, airline_id,
                        departure_airport_code, arrival_airport_code, scheduled_arrival,
                        flight_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
                    """
                    
                    cursor.execute(insert_sql, (
                        flight["flight_number"],
                        departure_time,
                        flight["airline_code"],
                        flight["origin_airport"],
                        flight["destination_airport"],
                        arrival_time,
                        "on_time"  # 默认状态
                    ))
                    insert_count += 1
            
            # 提交事务
            conn.commit()
            logger.info(f"成功保存到数据库: {insert_count} 条新增, {update_count} 条更新")
            
            # 关闭连接
            cursor.close()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"保存到数据库时出错: {str(e)}")
            return False

if __name__ == "__main__":
    # 获取未来7天的航班信息
    crawler = DailyAirDirectCrawler()
    
    # 获取未来7天的日期
    date_list = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
    
    for date_str in date_list:
        flights = crawler.get_flights_by_date(date_str)
        print(f"日期 {date_str} 获取到 {len(flights)} 个航班")
        
        # 打印前5个航班作为示例
        for i, flight in enumerate(flights[:5]):
            print(f"{i+1}. {flight['flight_number']}: {flight['origin_name']} → {flight['destination_name']}, 出发: {flight['departure_time']}")
        
        # 可选: 保存到数据库
        # crawler.save_to_database(flights) 