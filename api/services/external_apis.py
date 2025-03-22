"""
AviationStack API整合服務
用於查詢和獲取航班資料
"""
import os
import requests
import json
import datetime
import logging
import time
import random
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from dotenv import load_dotenv
import pytz
import pickle
from pathlib import Path

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/aviation_stack_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('aviation_stack_api')

# 載入環境變數 - 使用絕對路徑
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
env_path = os.path.join(project_root, '.env')
print(f"嘗試加載環境變數文件: {env_path}")
load_dotenv(env_path)

# API 設定
AVIATIONSTACK_API_KEY = os.getenv('AVIATIONSTACK_API_KEY')
print(f"API金鑰加載狀態: {'已加載' if AVIATIONSTACK_API_KEY else '未加載'}")
if AVIATIONSTACK_API_KEY:
    # 顯示前4位和後4位，中間用***替代
    masked_key = AVIATIONSTACK_API_KEY[:4] + '***' + AVIATIONSTACK_API_KEY[-4:]
    print(f"API金鑰(部分): {masked_key}")
else:
    print("API金鑰未設置，請檢查.env文件")
AVIATIONSTACK_BASE_URL = 'http://api.aviationstack.com/v1/'

# 載入航空公司與機場配置
def load_airlines_airports_config():
    try:
        with open('config/airlines_airports.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"無法載入航空公司/機場配置: {e}")
        return {"airlines": [], "airports": []}

# 創建緩存目錄
def ensure_cache_dir():
    """確保緩存目錄存在"""
    cache_dir = Path(os.path.join(project_root, 'cache', 'aviation_stack'))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

# 緩存管理
def get_cache_key(endpoint: str, params: Dict) -> str:
    """生成緩存鍵"""
    # 排序參數以確保相同參數的不同順序產生相同的鍵
    param_str = json.dumps(params, sort_keys=True)
    # 創建緩存鍵
    cache_key = hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()
    return cache_key

def get_from_cache(endpoint: str, params: Dict) -> Optional[Dict]:
    """從緩存獲取數據"""
    cache_dir = ensure_cache_dir()
    cache_key = get_cache_key(endpoint, params)
    cache_file = cache_dir / f"{cache_key}.pkl"
    
    if cache_file.exists():
        try:
            # 檢查緩存是否過期（預設24小時）
            cache_age = datetime.datetime.now().timestamp() - cache_file.stat().st_mtime
            if cache_age < 24 * 60 * 60:  # 24小時
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            else:
                logger.info(f"緩存已過期: {endpoint} {params}")
        except Exception as e:
            logger.error(f"讀取緩存出錯: {e}")
    
    return None

def save_to_cache(endpoint: str, params: Dict, data: Dict) -> None:
    """保存數據到緩存"""
    cache_dir = ensure_cache_dir()
    cache_key = get_cache_key(endpoint, params)
    cache_file = cache_dir / f"{cache_key}.pkl"
    
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"已保存到緩存: {endpoint}")
    except Exception as e:
        logger.error(f"保存緩存出錯: {e}")

# API請求函數（增加緩存和重試機制）
def make_api_request(endpoint: str, params: Dict = None, use_cache: bool = True, max_retries: int = 3, retry_delay: int = 2) -> Dict:
    """
    向AviationStack API發送請求（帶緩存和重試機制）

    參數:
        endpoint: API端點
        params: 查詢參數
        use_cache: 是否使用緩存
        max_retries: 最大重試次數
        retry_delay: 重試延遲(秒)

    返回:
        API回應的JSON數據
    """
    if params is None:
        params = {}
    
    # 確保有API金鑰
    params['access_key'] = AVIATIONSTACK_API_KEY
    
    # 檢查緩存
    if use_cache:
        cached_data = get_from_cache(endpoint, params)
        if cached_data:
            logger.info(f"從緩存獲取數據: {endpoint}")
            return cached_data
    
    # 記錄請求信息
    logger.info(f"發送請求到 {AVIATIONSTACK_BASE_URL}{endpoint} 參數: {params}")
    
    # 重試邏輯
    for retry in range(max_retries):
        try:
            # 發起請求
            response = requests.get(f"{AVIATIONSTACK_BASE_URL}{endpoint}", params=params)
            
            # 處理成功響應
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    
                    # 檢查API錯誤
                    if 'error' in json_response:
                        error_info = json_response.get('error', {})
                        error_code = error_info.get('code', 'unknown')
                        error_message = error_info.get('message', 'Unknown error')
                        logger.error(f"API返回錯誤: {error_code} - {error_message}")
                        
                        # 處理配額限制
                        if error_code == 'usage_limit_reached':
                            logger.warning("月度API配額已用盡，將使用緩存或模擬數據")
                            return {"error": error_info, "data": None, "source": "api_error"}
                    
                    # 保存到緩存
                    if use_cache and 'data' in json_response:
                        save_to_cache(endpoint, params, json_response)
                    
                    return json_response
                except Exception as e:
                    logger.error(f"處理API回應時出錯: {e}")
                    if retry < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return {"error": str(e), "data": None, "source": "parse_error"}
            
            # 處理HTTP錯誤
            else:
                logger.error(f"API請求失敗: {response.status_code} {response.reason}")
                logger.error(f"回應內容: {response.text}")
                
                # 處理特定錯誤
                if response.status_code == 429:  # Too Many Requests
                    # 如果達到限制，等待更長時間
                    wait_time = retry_delay * (retry + 1) * 2
                    logger.warning(f"達到API速率限制，等待{wait_time}秒後重試")
                    time.sleep(wait_time)
                elif response.status_code == 401:  # Unauthorized
                    return {"error": "API金鑰無效或未授權", "data": None, "source": "auth_error"}
                elif response.status_code == 403:  # Forbidden
                    return {"error": "API功能受限，該功能在您的方案中不可用", "data": None, "source": "plan_error"}
                elif retry < max_retries - 1:
                    # 一般錯誤重試
                    time.sleep(retry_delay)
                else:
                    return {"error": f"{response.status_code} {response.reason}", "data": None, "source": "http_error"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API請求異常: {e}")
            if retry < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return {"error": str(e), "data": None, "source": "request_error"}
    
    return {"error": "達到最大重試次數", "data": None, "source": "max_retries"}

# 獲取實時航班狀態
def get_real_time_flights(
    airline_code: Optional[str] = None,
    flight_number: Optional[str] = None,
    departure_airport: Optional[str] = None,
    arrival_airport: Optional[str] = None,
    flight_status: Optional[str] = None,
    flight_date: Optional[str] = None
) -> Dict:
    """
    獲取實時航班狀態

    參數:
        airline_code: 航空公司代碼 (如 'CI' 代表中華航空)
        flight_number: 航班編號 (如 'CI100')
        departure_airport: 出發機場IATA代碼 (如 'TPE')
        arrival_airport: 抵達機場IATA代碼 (如 'HKG')
        flight_status: 航班狀態 ('scheduled', 'active', 'landed', 'cancelled', 'incident', 'diverted')
        flight_date: 航班日期 (YYYY-MM-DD)

    返回:
        包含航班資訊的字典
    """
    params = {}
    
    # 組合航班編號
    if airline_code and flight_number:
        if not flight_number.startswith(airline_code):
            params['flight_iata'] = f"{airline_code}{flight_number}"
        else:
            params['flight_iata'] = flight_number
    elif airline_code:
        params['airline_iata'] = airline_code
    elif flight_number:
        params['flight_iata'] = flight_number
    
    # 添加其他參數
    if departure_airport:
        params['dep_iata'] = departure_airport
    if arrival_airport:
        params['arr_iata'] = arrival_airport
    if flight_status:
        params['flight_status'] = flight_status
    if flight_date:
        params['flight_date'] = flight_date
    else:
        # 默認使用當天日期
        params['flight_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
    
    return make_api_request('flights', params)

# 搜尋特定機場的航班
def get_airport_flights(
    airport_code: str,
    flight_type: str = 'departure',  # 'departure' 或 'arrival'
    flight_date: Optional[str] = None
) -> Dict:
    """
    獲取特定機場的航班

    參數:
        airport_code: 機場IATA代碼 (如 'TPE')
        flight_type: 航班類型 ('departure' 或 'arrival')
        flight_date: 航班日期 (YYYY-MM-DD)

    返回:
        包含航班資訊的字典
    """
    params = {}
    
    if flight_type.lower() == 'departure':
        params['dep_iata'] = airport_code
    else:  # arrival
        params['arr_iata'] = airport_code
    
    if flight_date:
        params['flight_date'] = flight_date
    else:
        # 默認使用當天日期
        params['flight_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
    
    return make_api_request('flights', params)

# 獲取特定航線的航班
def get_route_flights(
    departure_airport: str,
    arrival_airport: str,
    flight_date: Optional[str] = None,
    airline_code: Optional[str] = None
) -> Dict:
    """
    獲取特定航線的航班

    參數:
        departure_airport: 出發機場IATA代碼 (如 'TPE')
        arrival_airport: 抵達機場IATA代碼 (如 'HKG')
        flight_date: 航班日期 (YYYY-MM-DD)
        airline_code: 航空公司代碼 (如 'CI')

    返回:
        包含航班資訊的字典
    """
    params = {
        'dep_iata': departure_airport,
        'arr_iata': arrival_airport
    }
    
    if airline_code:
        params['airline_iata'] = airline_code
    
    if flight_date:
        params['flight_date'] = flight_date
    else:
        # 默認使用當天日期
        params['flight_date'] = datetime.datetime.now().strftime('%Y-%m-%d')
    
    return make_api_request('flights', params)

# 獲取航空公司資訊
def get_airline_info(airline_code: str) -> Dict:
    """
    獲取航空公司資訊

    參數:
        airline_code: 航空公司IATA代碼 (如 'CI')

    返回:
        包含航空公司資訊的字典
    """
    params = {
        'airline_iata': airline_code
    }
    
    return make_api_request('airlines', params)

# 獲取機場資訊
def get_airport_info(airport_code: str) -> Dict:
    """
    獲取機場資訊

    參數:
        airport_code: 機場IATA代碼 (如 'TPE')

    返回:
        包含機場資訊的字典
    """
    params = {
        'iata': airport_code
    }
    
    return make_api_request('airports', params)

# 將API回應轉換為數據庫格式
def transform_flight_data_for_db(flight_data: Dict) -> Dict:
    """
    將AviationStack API的航班資料轉換為適合數據庫的格式

    參數:
        flight_data: API返回的航班數據

    返回:
        適合插入到Flights表的數據字典
    """
    # 處理日期時間格式
    def parse_datetime(dt_str):
        if not dt_str:
            return None
        try:
            # AviationStack API 返回的時間是UTC格式
            dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt
        except ValueError:
            logger.error(f"無法解析日期時間: {dt_str}")
            return None
    
    # 獲取航班基本信息
    flight = flight_data.get('flight', {})
    departure = flight_data.get('departure', {})
    arrival = flight_data.get('arrival', {})
    airline = flight_data.get('airline', {})
    
    # 確定航班狀態
    status_mapping = {
        'scheduled': 'on_time',
        'active': 'departed',
        'landed': 'arrived',
        'cancelled': 'cancelled',
        'incident': 'delayed',
        'diverted': 'delayed'
    }
    flight_status = status_mapping.get(flight_data.get('flight_status', ''), 'on_time')
    
    # 創建數據庫記錄 - 移除不需要的欄位
    db_record = {
        'flight_number': flight.get('iata', ''),
        'scheduled_departure': parse_datetime(departure.get('scheduled', '')),
        'airline_id': airline.get('iata', ''),
        'departure_airport_code': departure.get('iata', ''),
        'arrival_airport_code': arrival.get('iata', ''),
        'scheduled_arrival': parse_datetime(arrival.get('scheduled', '')),
        'flight_status': flight_status,
        'aircraft_type': flight.get('aircraft', {}).get('iata', ''),
        'price': None,  # AviationStack 不提供價格資訊
        'booking_link': None,  # AviationStack 不提供訂票連結
        'scrape_date': datetime.datetime.now()
    }
    
    return db_record

# 批量獲取指定航空公司和機場的航班資訊（優化版）
def get_flights_for_configured_airlines_airports(
    flight_date: Optional[str] = None,
    limit_airlines: Optional[List[str]] = None,
    limit_airports: Optional[List[str]] = None,
    max_api_calls: int = 20,
    use_cache: bool = True,
    use_mock_data: bool = False,
    priority_routes: Optional[List[Tuple[str, str]]] = None
) -> List[Dict]:
    """
    獲取配置中指定航空公司和機場的所有航班信息(優化版)

    參數:
        flight_date: 航班日期 (YYYY-MM-DD)
        limit_airlines: 限制查詢的航空公司列表
        limit_airports: 限制查詢的機場列表
        max_api_calls: 最大API調用次數
        use_cache: 是否使用緩存
        use_mock_data: 是否在無法從API獲取數據時使用模擬數據
        priority_routes: 優先查詢的航線列表，格式為[(出發機場, 到達機場),...]

    返回:
        符合條件的航班資料列表
    """
    # 加載配置
    config = load_airlines_airports_config()
    airlines = limit_airlines or config.get('airlines', [])[:5]  # 只使用前5個航空公司作為默認值
    airports = limit_airports or config.get('airports', [])[:10]  # 只使用前10個機場作為默認值
    
    # 設置優先級路線
    if priority_routes is None:
        # 默認優先級：台北出發的主要航線
        priority_routes = [
            ('TPE', 'HKG'), ('TPE', 'NRT'), ('TPE', 'HND'), 
            ('TPE', 'ICN'), ('TPE', 'BKK'), ('TPE', 'SIN')
        ]
    
    # 初始化結果容器
    all_flights = []
    processed_flights = set()  # 用於去重
    api_calls = 0
    mock_data_used = False
    
    # 設置日期
    if not flight_date:
        flight_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"批量獲取航班信息 - 日期: {flight_date}, " + 
                f"最大API調用: {max_api_calls}, 使用緩存: {use_cache}, 使用模擬: {use_mock_data}")
    
    # 首先處理優先航線
    for dep, arr in priority_routes:
        if api_calls >= max_api_calls:
            logger.warning(f"已達最大API調用次數({max_api_calls})，停止查詢")
            break
        
        if dep in airports and arr in airports:
            logger.info(f"查詢優先航線 {dep}-{arr} 的航班...")
            response = make_api_request(
                'flights', 
                {
                    'dep_iata': dep,
                    'arr_iata': arr,
                    'flight_date': flight_date
                },
                use_cache=use_cache
            )
            api_calls += 1
            
            if 'data' in response and response['data']:
                for flight_data in response['data']:
                    flight_key = f"{flight_data.get('flight', {}).get('iata', '')}-{flight_date}"
                    if flight_key not in processed_flights:
                        processed_flights.add(flight_key)
                        db_record = transform_flight_data_for_db(flight_data)
                        all_flights.append(db_record)
            
            # 檢查配額限制
            elif response.get('source') in ['auth_error', 'plan_error'] or 'usage_limit_reached' in str(response.get('error', {})):
                logger.warning("API配額限制或授權問題，停止API調用")
                break
            
            # 隨機延遲以避免速率限制
            time.sleep(random.uniform(1.0, 2.5))
    
    # 如果還沒達到最大API調用次數，查詢其他航空公司
    remaining_calls = max_api_calls - api_calls
    if remaining_calls > 0 and len(airlines) > 0:
        logger.info(f"查詢航空公司航班，剩餘API調用次數: {remaining_calls}")
        
        # 計算每個航空公司分配的API調用次數
        calls_per_airline = max(1, remaining_calls // len(airlines))
        
        for airline in airlines:
            if api_calls >= max_api_calls:
                break
                
            logger.info(f"查詢航空公司 {airline} 的航班...")
            response = make_api_request(
                'flights', 
                {
                    'airline_iata': airline,
                    'flight_date': flight_date
                },
                use_cache=use_cache
            )
            api_calls += 1
            
            if 'data' in response and response['data']:
                for flight_data in response['data']:
                    flight_key = f"{flight_data.get('flight', {}).get('iata', '')}-{flight_date}"
                    if flight_key not in processed_flights:
                        processed_flights.add(flight_key)
                        db_record = transform_flight_data_for_db(flight_data)
                        all_flights.append(db_record)
            
            # 檢查配額限制
            elif response.get('source') in ['auth_error', 'plan_error'] or 'usage_limit_reached' in str(response.get('error', {})):
                logger.warning("API配額限制或授權問題，停止API調用")
                break
            
            # 隨機延遲以避免速率限制
            time.sleep(random.uniform(1.5, 3.0))
    
    # 如果沒有查詢到航班或被要求使用模擬數據，生成模擬數據
    if (len(all_flights) == 0 or use_mock_data) and not mock_data_used:
        logger.info("使用模擬航班數據")
        mock_flights = generate_mock_flight_data(flight_date, airlines, airports, priority_routes)
        all_flights.extend(mock_flights)
        mock_data_used = True
    
    logger.info(f"總共獲取了 {len(all_flights)} 個航班資訊，API調用次數：{api_calls}")
    return all_flights

# 生成模擬航班數據
def generate_mock_flight_data(flight_date: str, airlines: List[str], airports: List[str], priority_routes: List[Tuple[str, str]]) -> List[Dict]:
    """生成模擬的航班數據用於開發和測試"""
    
    mock_flights = []
    flight_date_obj = datetime.datetime.strptime(flight_date, '%Y-%m-%d')
    
    # 生成優先航線的模擬數據
    for dep, arr in priority_routes:
        # 為每個優先航線生成2-3個航班
        for _ in range(random.randint(2, 3)):
            # 隨機選擇航空公司
            airline = random.choice(airlines)
            # 生成隨機的航班號
            flight_number = f"{airline}{random.randint(100, 999)}"
            
            # 生成隨機的起飛和到達時間
            hour = random.randint(6, 22)
            minute = random.choice([0, 15, 30, 45])
            scheduled_departure = flight_date_obj.replace(hour=hour, minute=minute)
            
            # 根據出發和到達地估算飛行時間
            # 簡單估算：每對機場間的飛行時間在2-6小時之間
            flight_duration = datetime.timedelta(hours=random.uniform(2, 6))
            scheduled_arrival = scheduled_departure + flight_duration
            
            # 生成模擬的航班狀態
            statuses = ['on_time', 'delayed', 'departed', 'arrived', 'cancelled']
            status_weights = [0.7, 0.1, 0.1, 0.05, 0.05]  # 大多數是準時的
            flight_status = random.choices(statuses, weights=status_weights, k=1)[0]
            
            # 創建航班記錄 - 移除不需要的欄位
            flight = {
                'flight_number': flight_number,
                'scheduled_departure': scheduled_departure,
                'airline_id': airline,
                'departure_airport_code': dep,
                'arrival_airport_code': arr,
                'scheduled_arrival': scheduled_arrival,
                'flight_status': flight_status,
                'aircraft_type': random.choice(['B738', 'A320', 'B77W', 'A333', 'B789']),
                'price': random.randint(2000, 15000),  # 模擬價格
                'booking_link': f"https://example.com/book/{flight_number}",
                'scrape_date': datetime.datetime.now()
            }
            
            mock_flights.append(flight)
    
    # 再生成其他隨機航線的模擬數據
    for _ in range(random.randint(10, 20)):
        # 隨機選擇不同的出發和到達機場
        dep = random.choice(airports)
        # 確保到達機場與出發機場不同
        arr_candidates = [a for a in airports if a != dep]
        if arr_candidates:
            arr = random.choice(arr_candidates)
            
            # 隨機選擇航空公司
            airline = random.choice(airlines)
            # 生成隨機的航班號
            flight_number = f"{airline}{random.randint(100, 999)}"
            
            # 生成隨機的起飛和到達時間
            hour = random.randint(6, 22)
            minute = random.choice([0, 15, 30, 45])
            scheduled_departure = flight_date_obj.replace(hour=hour, minute=minute)
            
            # 根據出發和到達地估算飛行時間
            flight_duration = datetime.timedelta(hours=random.uniform(2, 6))
            scheduled_arrival = scheduled_departure + flight_duration
            
            # 生成模擬的航班狀態
            statuses = ['on_time', 'delayed', 'departed', 'arrived', 'cancelled']
            status_weights = [0.7, 0.1, 0.1, 0.05, 0.05]
            flight_status = random.choices(statuses, weights=status_weights, k=1)[0]
            
            # 創建航班記錄 - 移除不需要的欄位
            flight = {
                'flight_number': flight_number,
                'scheduled_departure': scheduled_departure,
                'airline_id': airline,
                'departure_airport_code': dep,
                'arrival_airport_code': arr,
                'scheduled_arrival': scheduled_arrival,
                'flight_status': flight_status,
                'aircraft_type': random.choice(['B738', 'A320', 'B77W', 'A333', 'B789']),
                'price': random.randint(2000, 15000),
                'booking_link': f"https://example.com/book/{flight_number}",
                'scrape_date': datetime.datetime.now()
            }
            
            mock_flights.append(flight)
    
    return mock_flights

# 測試API連接
def test_api_connection() -> bool:
    """
    測試API連接是否正常

    返回:
        連接是否成功
    """
    try:
        # 簡單請求以測試連接
        response = make_api_request('airlines', {'limit': 1})
        return 'data' in response and len(response['data']) > 0
    except Exception as e:
        logger.error(f"API連接測試失敗: {e}")
        return False

if __name__ == "__main__":
    # 簡單測試
    print("測試 AviationStack API 連接...")
    connection_ok = test_api_connection()
    print(f"API 連接測試結果: {'成功' if connection_ok else '失敗'}")
    
    if connection_ok:
        # 獲取中華航空的航班
        print("\n中華航空航班資訊:")
        ci_flights = get_real_time_flights(airline_code="CI")
        print(f"獲取到 {len(ci_flights.get('data', []))} 個航班")
        
        # 獲取台北機場的航班
        print("\n台北機場出發航班:")
        tpe_flights = get_airport_flights(airport_code="TPE")
        print(f"獲取到 {len(tpe_flights.get('data', []))} 個航班") 