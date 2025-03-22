import requests
import logging
import time
import random
import json
import os
from datetime import datetime, timedelta

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyAirAPIScraper")

class DailyAirAPIScraper:
    """
    通過API獲取德安航空的航班資訊
    根據分析，德安航空可能使用API來獲取航班資訊
    """

    def __init__(self):
        self.base_url = "https://www.dailyair.com.tw/"
        # 可能的API端點，將在嘗試階段測試
        self.api_endpoints = [
            "api/flight/schedule",
            "api/flights",
            "ajax/schedule",
            "schedule/api"
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.dailyair.com.tw/",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json; charset=UTF-8"
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
        # 預定義的航線
        self.routes = [
            {"origin": "TTT", "destination": "GNI"},  # 台東 -> 綠島
            {"origin": "GNI", "destination": "TTT"},  # 綠島 -> 台東
            {"origin": "TTT", "destination": "KYD"},  # 台東 -> 蘭嶼
            {"origin": "KYD", "destination": "TTT"},  # 蘭嶼 -> 台東
            {"origin": "KHH", "destination": "CMJ"},  # 高雄 -> 七美
            {"origin": "CMJ", "destination": "KHH"},  # 七美 -> 高雄
            {"origin": "KHH", "destination": "WOT"},  # 高雄 -> 望安
            {"origin": "WOT", "destination": "KHH"},  # 望安 -> 高雄
            {"origin": "MZG", "destination": "CMJ"},  # 馬公 -> 七美
            {"origin": "CMJ", "destination": "MZG"}   # 七美 -> 馬公
        ]
        # 初始化請求session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        logger.info("德安航空API爬蟲初始化完成")

    def _init_session(self):
        """初始化會話並獲取必要的cookie"""
        try:
            logger.info("初始化會話並獲取cookie...")
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            logger.info(f"成功獲取首頁，可用的cookie: {dict(response.cookies)}")
            return True
        except Exception as e:
            logger.error(f"初始化會話時出錯: {str(e)}")
            return False

    def _test_api_endpoints(self):
        """測試可能的API端點以尋找有效的接口"""
        valid_endpoints = []
        
        # 獲取會話和cookie
        if not self._init_session():
            logger.warning("初始化會話失敗，繼續嘗試API端點...")
        
        logger.info("開始測試可能的API端點...")
        
        # 獲取當前日期
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 準備測試參數
        test_params = [
            {},  # 無參數
            {"date": today},
            {"date": tomorrow},
            {"from": "TTT", "to": "GNI"},
            {"origin": "TTT", "destination": "GNI"},
            {"flight_date": today}
        ]
        
        for endpoint in self.api_endpoints:
            api_url = f"{self.base_url.rstrip('/')}/{endpoint}"
            logger.info(f"測試API端點: {api_url}")
            
            for params in test_params:
                try:
                    # 添加隨機延遲
                    time.sleep(random.uniform(1, 3))
                    
                    # GET請求測試
                    response = self.session.get(api_url, params=params, timeout=30)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info(f"找到有效的GET API端點: {api_url} 參數: {params}")
                            valid_endpoints.append({
                                "url": api_url,
                                "method": "GET",
                                "params": params,
                                "sample_response": data
                            })
                            # 保存樣本響應
                            self._save_sample_response(endpoint, "GET", params, data)
                        except:
                            pass
                    
                    # POST請求測試
                    response = self.session.post(api_url, json=params, timeout=30)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info(f"找到有效的POST API端點: {api_url} 參數: {params}")
                            valid_endpoints.append({
                                "url": api_url,
                                "method": "POST",
                                "params": params,
                                "sample_response": data
                            })
                            # 保存樣本響應
                            self._save_sample_response(endpoint, "POST", params, data)
                        except:
                            pass
                except Exception as e:
                    logger.warning(f"測試端點 {api_url} 時出錯: {str(e)}")
        
        logger.info(f"API端點測試完成，找到 {len(valid_endpoints)} 個有效端點")
        return valid_endpoints

    def _save_sample_response(self, endpoint, method, params, data):
        """保存API樣本響應"""
        debug_dir = "debug_info"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        params_str = "_".join([f"{k}_{v}" for k, v in params.items()]) if params else "no_params"
        filename = f"dailyair_api_{endpoint.replace('/', '_')}_{method}_{params_str}_{timestamp}.json"
        file_path = os.path.join(debug_dir, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存API樣本響應至: {file_path}")

    def fetch_flights_via_api(self, date_str):
        """嘗試通過API獲取航班信息
        
        Args:
            date_str: 日期字符串，格式為 YYYY-MM-DD
            
        Returns:
            包含航班資訊的列表，如果無法獲取則返回空列表
        """
        logger.info(f"嘗試通過API獲取 {date_str} 的航班資訊")
        
        # 首先測試有效的API端點
        valid_endpoints = self._test_api_endpoints()
        
        if not valid_endpoints:
            logger.warning("未找到有效的API端點，無法獲取航班資訊")
            return []
        
        flights = []
        
        # 嘗試從每個有效端點獲取數據
        for endpoint_info in valid_endpoints:
            try:
                url = endpoint_info["url"]
                method = endpoint_info["method"]
                params = endpoint_info["params"].copy()
                
                # 添加或更新日期參數
                date_params = ["date", "flight_date", "flightDate", "departureDate"]
                added = False
                for param in date_params:
                    if param in params:
                        params[param] = date_str
                        added = True
                
                if not added and not params:
                    # 如果沒有日期參數且參數為空，添加日期參數
                    params["date"] = date_str
                
                logger.info(f"嘗試從 {url} 獲取航班信息，方法: {method}，參數: {params}")
                
                # 添加隨機延遲
                time.sleep(random.uniform(1, 3))
                
                response = None
                if method == "GET":
                    response = self.session.get(url, params=params, timeout=30)
                else:  # POST
                    response = self.session.post(url, json=params, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"成功從API獲取數據，狀態碼: {response.status_code}")
                    
                    # 嘗試解析JSON響應
                    try:
                        data = response.json()
                        
                        # 保存原始響應以便分析
                        self._save_sample_response("fetch_flights", method, params, data)
                        
                        # 嘗試解析航班數據
                        api_flights = self._parse_api_response(data, date_str)
                        
                        if api_flights:
                            logger.info(f"從API解析出 {len(api_flights)} 個航班")
                            flights.extend(api_flights)
                    except Exception as e:
                        logger.error(f"解析API響應時出錯: {str(e)}")
            
            except Exception as e:
                logger.error(f"從端點 {endpoint_info['url']} 獲取航班信息時出錯: {str(e)}")
        
        logger.info(f"API爬取完成，共找到 {len(flights)} 個航班")
        return flights

    def _parse_api_response(self, data, date_str):
        """解析API響應以提取航班信息
        
        由於我們不確定確切的API響應格式，此方法嘗試常見的數據結構
        """
        flights = []
        
        # 檢查常見的JSON結構
        # 結構1: 直接是航班數組
        if isinstance(data, list):
            for item in data:
                flight = self._extract_flight_from_item(item, date_str)
                if flight:
                    flights.append(flight)
        
        # 結構2: 數據包含在data或results鍵中
        elif isinstance(data, dict):
            # 嘗試常見的數據容器鍵
            for key in ['data', 'result', 'results', 'flights', 'flightList', 'schedule']:
                if key in data and (isinstance(data[key], list) or isinstance(data[key], dict)):
                    container = data[key]
                    
                    # 如果容器是列表
                    if isinstance(container, list):
                        for item in container:
                            flight = self._extract_flight_from_item(item, date_str)
                            if flight:
                                flights.append(flight)
                    
                    # 如果容器是字典，可能包含按航線或日期組織的航班
                    elif isinstance(container, dict):
                        for _, value in container.items():
                            if isinstance(value, list):
                                for item in value:
                                    flight = self._extract_flight_from_item(item, date_str)
                                    if flight:
                                        flights.append(flight)
        
        return flights

    def _extract_flight_from_item(self, item, date_str):
        """從API響應項中提取航班信息"""
        if not isinstance(item, dict):
            return None
        
        # 嘗試提取必要字段
        flight_number = None
        origin_airport = None
        destination_airport = None
        departure_time = None
        arrival_time = None
        days_operated = "每日"
        
        # 航班號可能的鍵
        for key in ['flightNumber', 'flight_number', 'flight', 'flightNo', 'flight_no', 'no']:
            if key in item and item[key]:
                flight_number = str(item[key])
                # 確保格式正確（添加DA前綴如果沒有）
                if not flight_number.startswith("DA"):
                    flight_number = "DA" + flight_number
                break
        
        # 起飛機場可能的鍵
        for key in ['origin', 'departure', 'from', 'departureAirport', 'originAirport']:
            if key in item and item[key]:
                origin_value = str(item[key])
                # 檢查是否為機場代碼
                if origin_value in self.airport_mapping:
                    origin_airport = origin_value
                else:
                    # 嘗試通過名稱查找代碼
                    for code, name in self.airport_mapping.items():
                        if name in origin_value:
                            origin_airport = code
                            break
                break
        
        # 抵達機場可能的鍵
        for key in ['destination', 'arrival', 'to', 'arrivalAirport', 'destinationAirport']:
            if key in item and item[key]:
                destination_value = str(item[key])
                # 檢查是否為機場代碼
                if destination_value in self.airport_mapping:
                    destination_airport = destination_value
                else:
                    # 嘗試通過名稱查找代碼
                    for code, name in self.airport_mapping.items():
                        if name in destination_value:
                            destination_airport = code
                            break
                break
        
        # 提取時間信息
        # 出發時間可能的鍵
        for key in ['departureTime', 'departure_time', 'depTime', 'dep_time', 'startTime']:
            if key in item and item[key]:
                dep_value = str(item[key])
                # 處理不同的時間格式
                if ':' in dep_value:
                    if len(dep_value) <= 5:  # 格式為 HH:MM
                        departure_time = f"{date_str} {dep_value}:00"
                    else:  # 可能包含完整日期時間
                        departure_time = dep_value
                else:
                    # 可能是數字格式，例如 800 表示 08:00
                    try:
                        time_int = int(dep_value)
                        hours = time_int // 100
                        minutes = time_int % 100
                        departure_time = f"{date_str} {hours:02d}:{minutes:02d}:00"
                    except:
                        pass
                break
        
        # 抵達時間可能的鍵
        for key in ['arrivalTime', 'arrival_time', 'arrTime', 'arr_time', 'endTime']:
            if key in item and item[key]:
                arr_value = str(item[key])
                # 處理不同的時間格式
                if ':' in arr_value:
                    if len(arr_value) <= 5:  # 格式為 HH:MM
                        arrival_time = f"{date_str} {arr_value}:00"
                    else:  # 可能包含完整日期時間
                        arrival_time = arr_value
                else:
                    # 可能是數字格式，例如 830 表示 08:30
                    try:
                        time_int = int(arr_value)
                        hours = time_int // 100
                        minutes = time_int % 100
                        arrival_time = f"{date_str} {hours:02d}:{minutes:02d}:00"
                    except:
                        pass
                break
        
        # 檢查是否獲取到所有必要信息
        if not all([flight_number, origin_airport, destination_airport, departure_time, arrival_time]):
            return None
        
        # 構建航班對象
        flight = {
            "flight_number": flight_number,
            "airline": "德安航空",
            "airline_code": "EBC",
            "origin_airport": origin_airport,
            "origin_name": self.airport_mapping.get(origin_airport, "未知機場"),
            "destination_airport": destination_airport,
            "destination_name": self.airport_mapping.get(destination_airport, "未知機場"),
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "days_operated": days_operated,
            "price": item.get("price") if "price" in item else None,
            "source": "api"
        }
        
        return flight

    def get_hardcoded_flights(self):
        """返回預設航班數據，當API獲取失敗時使用"""
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
        
        # 先嘗試通過API獲取數據
        flights = self.fetch_flights_via_api(date_str)
        
        # 如果API獲取失敗，則使用預設數據
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
            
        output_file = os.path.join(output_dir, f"dailyair_api_flights_{date_str}.json")
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(flights, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存 {len(flights)} 個航班數據至 {output_file}")
        
        return flights

if __name__ == "__main__":
    # 獲取明天的日期
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 爬取並打印結果
    scraper = DailyAirAPIScraper()
    flights = scraper.get_flights_by_date(tomorrow)
    
    print(f"共獲取到 {len(flights)} 個航班:")
    for flight in flights[:5]:  # 只打印前5個
        print(f"{flight['flight_number']}: {flight['origin_name']} -> {flight['destination_name']}, 起飛時間: {flight['departure_time']}") 