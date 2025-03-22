import requests
import logging
import time
import random
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyAirSimpleScraper")

class DailyAirSimpleScraper:
    """簡化版德安航空爬蟲，直接從官網獲取航班資訊"""

    def __init__(self):
        self.base_url = "https://www.dailyair.com.tw/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.dailyair.com.tw/"
        }
        # 機場代碼對應表
        self.airport_mapping = {
            "TTT": "台東",
            "GNI": "綠島",
            "KYD": "蘭嶼",
            "KHH": "高雄",
            "MZG": "馬公",
            "CMJ": "七美",
            "WOT": "望安"
        }
        logger.info("德安航空簡化爬蟲初始化完成")

    def scrape_schedule(self):
        """爬取首頁上的航班時刻表數據"""
        try:
            logger.info("開始爬取德安航空首頁數據")
            
            # 隨機延遲避免被識別為爬蟲
            time.sleep(random.uniform(1, 3))
            
            # 獲取首頁內容
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 保存cookies
            cookies = response.cookies
            
            logger.info(f"成功獲取首頁，狀態碼: {response.status_code}")
            
            # 保存HTML以便調試
            debug_dir = "debug_info"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_path = os.path.join(debug_dir, f"dailyair_home_{timestamp}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"已保存頁面HTML至: {html_path}")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 先嘗試找帶有特定類別的表格
            flight_tables = soup.select("table.table.table-striped")
            
            # 如果沒找到，嘗試找所有表格
            if not flight_tables:
                logger.info("未找到帶有特定類的表格，嘗試查找所有表格")
                flight_tables = soup.find_all("table")
                
                # 過濾表格，只保留那些可能包含航班信息的表格
                filtered_tables = []
                for table in flight_tables:
                    headers = table.find_all('th')
                    if headers and len(headers) >= 3:
                        # 檢查表頭是否包含航班相關信息
                        header_text = " ".join([h.text.strip() for h in headers]).lower()
                        if any(keyword in header_text for keyword in ['航班', '時間', '抵達', '出發', '班機', '機號']):
                            filtered_tables.append(table)
                
                flight_tables = filtered_tables
            
            if not flight_tables:
                logger.warning("未找到航班時刻表，將使用預設航班數據")
                return []
            
            flights = []
            
            # 解析每個時刻表
            for table_idx, table in enumerate(flight_tables):
                try:
                    # 尋找表格附近的航線信息
                    route_info = None
                    
                    # 優先從h4標籤獲取
                    route_header = table.find_previous('h4')
                    if route_header:
                        route_info = route_header.text.strip()
                    
                    # 如果沒有h4，嘗試從h3標籤獲取
                    if not route_info:
                        route_header = table.find_previous('h3')
                        if route_header:
                            route_info = route_header.text.strip()
                    
                    # 如果仍未找到，嘗試從表格前面的任何文本節點獲取
                    if not route_info:
                        prev_sibling = table.find_previous_sibling()
                        if prev_sibling and prev_sibling.string:
                            route_info = prev_sibling.string.strip()
                    
                    # 如果仍未找到，使用默認值
                    if not route_info:
                        route_info = f"未知航線{table_idx}"
                    
                    logger.info(f"開始解析航線: {route_info}")
                    
                    # 解析表頭
                    headers = []
                    thead = table.find('thead')
                    if thead:
                        headers = [th.text.strip() for th in thead.find_all('th')]
                    
                    # 如果沒有找到thead，嘗試從第一行獲取表頭
                    if not headers:
                        first_row = table.find('tr')
                        if first_row:
                            headers = [th.text.strip() for th in first_row.find_all('th')]
                    
                    # 確認必要的表頭存在
                    if not headers or len(headers) < 3:
                        logger.warning(f"航線 {route_info} 的表頭格式不符合預期: {headers}")
                        continue
                    
                    # 提取航線起訖點
                    origin_dest = []
                    for separator in ['←→', '-', '到', '往返']:
                        if separator in route_info:
                            origin_dest = route_info.split(separator)
                            break
                    
                    if len(origin_dest) != 2:
                        # 嘗試使用正則表達式匹配城市名稱
                        import re
                        city_pattern = '|'.join(self.airport_mapping.values())
                        cities = re.findall(f'({city_pattern})', route_info)
                        
                        if len(cities) >= 2:
                            origin_name = cities[0]
                            destination_name = cities[1]
                        else:
                            logger.warning(f"無法從 '{route_info}' 提取起訖點")
                            origin_name = "未知起點"
                            destination_name = "未知終點"
                    else:
                        origin_name = origin_dest[0].strip()
                        destination_name = origin_dest[1].strip()
                    
                    # 映射到機場代碼
                    origin_airport = None
                    destination_airport = None
                    
                    for code, name in self.airport_mapping.items():
                        if name in origin_name:
                            origin_airport = code
                        if name in destination_name:
                            destination_airport = code
                    
                    if not origin_airport or not destination_airport:
                        logger.warning(f"無法映射機場代碼: {origin_name} - {destination_name}")
                        # 使用預設代碼
                        if '台東' in route_info and '綠島' in route_info:
                            origin_airport = 'TTT'
                            destination_airport = 'GNI'
                        elif '台東' in route_info and '蘭嶼' in route_info:
                            origin_airport = 'TTT'
                            destination_airport = 'KYD'
                        elif '高雄' in route_info and '望安' in route_info:
                            origin_airport = 'KHH'
                            destination_airport = 'WOT'
                        elif '高雄' in route_info and '七美' in route_info:
                            origin_airport = 'KHH'
                            destination_airport = 'CMJ'
                        elif '馬公' in route_info and '七美' in route_info:
                            origin_airport = 'MZG'
                            destination_airport = 'CMJ'
                        else:
                            origin_airport = 'UNK'
                            destination_airport = 'UNK'
                    
                    # 解析每一行
                    body_rows = []
                    tbody = table.find('tbody')
                    if tbody:
                        body_rows = tbody.find_all('tr')
                    else:
                        # 如果沒有tbody，從第二行開始獲取所有行
                        all_rows = table.find_all('tr')
                        if len(all_rows) > 1:
                            body_rows = all_rows[1:]  # 跳過表頭行
                    
                    for row in body_rows:
                        cells = row.find_all('td')
                        if not cells or len(cells) < 3:
                            continue
                        
                        # 嘗試提取航班號、出發時間和到達時間
                        flight_number = None
                        departure_time = None
                        arrival_time = None
                        days_operated = "每日"
                        
                        # 根據表頭識別每列的內容
                        for idx, header in enumerate(headers):
                            if idx >= len(cells):
                                break
                                
                            cell_text = cells[idx].text.strip()
                            
                            if any(keyword in header.lower() for keyword in ['航班', '班機', '機號']):
                                flight_number = cell_text
                            elif any(keyword in header.lower() for keyword in ['出發', '起飛']):
                                departure_time = cell_text
                            elif any(keyword in header.lower() for keyword in ['抵達', '到達']):
                                arrival_time = cell_text
                            elif any(keyword in header.lower() for keyword in ['出勤', '營運日', '班表', '飛行日']):
                                if cell_text and cell_text != "每日":
                                    days_operated = cell_text
                        
                        # 如果沒有成功識別，嘗試按位置識別
                        if not flight_number and len(cells) >= 1:
                            flight_number = cells[0].text.strip()
                            
                        if not departure_time and len(cells) >= 2:
                            departure_time = cells[1].text.strip()
                            
                        if not arrival_time and len(cells) >= 3:
                            arrival_time = cells[2].text.strip()
                            
                        if days_operated == "每日" and len(cells) > 3:
                            days_cell = cells[3].text.strip()
                            if days_cell and days_cell != "每日":
                                days_operated = days_cell
                        
                        # 確保提取到了有效的數據
                        if not flight_number or not departure_time or not arrival_time:
                            logger.warning(f"無法從行提取完整的航班信息: {[c.text.strip() for c in cells]}")
                            continue
                        
                        # 確保航班號格式正確
                        if not flight_number.startswith("DA"):
                            flight_number = "DA" + flight_number
                        
                        # 格式化時間
                        dep_time = datetime.now().strftime("%Y-%m-%d") + " " + departure_time + (":00" if ":" in departure_time else ":00")
                        arr_time = datetime.now().strftime("%Y-%m-%d") + " " + arrival_time + (":00" if ":" in arrival_time else ":00")
                        
                        flight = {
                            "flight_number": flight_number,
                            "airline": "德安航空",
                            "airline_code": "EBC",
                            "origin_airport": origin_airport,
                            "origin_name": origin_name,
                            "destination_airport": destination_airport,
                            "destination_name": destination_name,
                            "departure_time": dep_time,
                            "arrival_time": arr_time,
                            "days_operated": days_operated,
                            "price": None,  # 價格可能需要額外的請求
                            "source": "web_scraping"
                        }
                        
                        flights.append(flight)
                        logger.debug(f"解析到航班: {flight_number}, {origin_airport} -> {destination_airport}, {departure_time}")
                
                except Exception as e:
                    logger.error(f"解析表格 {table_idx} 時出錯: {str(e)}")
            
            logger.info(f"成功解析到 {len(flights)} 個航班")
            return flights
        
        except Exception as e:
            logger.error(f"爬取德安航空首頁時出錯: {str(e)}")
            return []

    def get_hardcoded_flights(self):
        """返回預設航班數據，當爬蟲失敗時使用"""
        logger.info("使用預設航班數據")
        
        # 基準日期，用於生成未來日期
        base_date = datetime.now().strftime("%Y-%m-%d")
        
        # 預設航班
        flights = [
            # 台東 - 綠島航線
            {
                "flight_number": "DA7010",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "GNI",
                "destination_name": "綠島",
                "departure_time": f"{base_date} 08:00:00",
                "arrival_time": f"{base_date} 08:20:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7020",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "GNI",
                "destination_name": "綠島",
                "departure_time": f"{base_date} 14:30:00",
                "arrival_time": f"{base_date} 14:50:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            # 綠島 - 台東航線
            {
                "flight_number": "DA7015",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "GNI",
                "origin_name": "綠島",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{base_date} 08:40:00",
                "arrival_time": f"{base_date} 09:00:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7025",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "GNI",
                "origin_name": "綠島",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{base_date} 15:10:00",
                "arrival_time": f"{base_date} 15:30:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            # 台東 - 蘭嶼航線
            {
                "flight_number": "DA7102",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "KYD",
                "destination_name": "蘭嶼",
                "departure_time": f"{base_date} 10:00:00",
                "arrival_time": f"{base_date} 10:30:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7104",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "TTT",
                "origin_name": "台東",
                "destination_airport": "KYD",
                "destination_name": "蘭嶼",
                "departure_time": f"{base_date} 13:00:00",
                "arrival_time": f"{base_date} 13:30:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            # 蘭嶼 - 台東航線
            {
                "flight_number": "DA7103",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "KYD",
                "origin_name": "蘭嶼",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{base_date} 11:00:00",
                "arrival_time": f"{base_date} 11:30:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
            {
                "flight_number": "DA7105",
                "airline": "德安航空",
                "airline_code": "EBC",
                "origin_airport": "KYD",
                "origin_name": "蘭嶼",
                "destination_airport": "TTT",
                "destination_name": "台東",
                "departure_time": f"{base_date} 14:00:00",
                "arrival_time": f"{base_date} 14:30:00",
                "days_operated": "每日",
                "price": None,
                "source": "hardcoded"
            },
        ]
        
        return flights

    def get_flights_by_date(self, date_str):
        """根據指定日期獲取航班信息，並保存為JSON文件"""
        logger.info(f"獲取德安航空日期 {date_str} 的航班")
        
        # 先嘗試爬取實時數據
        flights = self.scrape_schedule()
        
        # 如果爬取失敗，則使用預設數據
        if not flights:
            flights = self.get_hardcoded_flights()
        
        # 調整日期為指定日期
        for flight in flights:
            dep_time = flight["departure_time"].split(" ")[1]
            arr_time = flight["arrival_time"].split(" ")[1]
            
            flight["departure_time"] = f"{date_str} {dep_time}"
            flight["arrival_time"] = f"{date_str} {arr_time}"
        
        # 保存為JSON文件
        output_dir = "flight_data"
        # 創建輸出目錄（如果不存在）
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"創建輸出目錄: {output_dir}")
            
        output_file = os.path.join(output_dir, f"dailyair_simple_flights_{date_str}.json")
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(flights, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存 {len(flights)} 個航班數據至 {output_file}")
        
        return flights

if __name__ == "__main__":
    # 獲取明天的日期
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 爬取並打印結果
    scraper = DailyAirSimpleScraper()
    flights = scraper.get_flights_by_date(tomorrow)
    
    print(f"共獲取到 {len(flights)} 個航班:")
    for flight in flights[:5]:  # 只打印前5個
        print(f"{flight['flight_number']}: {flight['origin_name']} -> {flight['destination_name']}, 起飛時間: {flight['departure_time']}")