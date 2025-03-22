"""
航班控制器 - 處理航班搜尋、機場和航空公司相關的API請求
"""
from flask import Blueprint, jsonify, request
import os
import json
from pathlib import Path
import datetime
import pyodbc
import logging

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('flight_controller')

# 創建藍圖
flight_blueprint = Blueprint('flights', __name__)

# 獲取資料庫連接字串
def get_db_connection():
    """獲取資料庫連接"""
    try:
        # 嘗試從環境變數獲取
        connection_string = os.getenv('DB_CONNECTION_STRING')
        
        # 如果環境變數不存在，使用預設連接字串
        if not connection_string:
            connection_string = 'Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=FlightBookingDB;Trusted_Connection=yes;'
            logger.warning("找不到環境變數DB_CONNECTION_STRING，使用預設連接字串")
        
        conn = pyodbc.connect(connection_string)
        return conn
    except Exception as e:
        logger.error(f"資料庫連接失敗: {e}")
        return None

# 機場列表端點
@flight_blueprint.route('/airports', methods=['GET'])
def get_airports():
    """獲取所有機場列表"""
    try:
        conn = get_db_connection()
        if not conn:
            # 如果無法連接到資料庫，使用備用資料
            logger.warning("資料庫連接失敗，使用備用機場資料")
            fallback_airports = [
                {"code": "TPE", "name": "台灣桃園國際機場"},
                {"code": "TSA", "name": "台北松山機場"},
                {"code": "KHH", "name": "高雄國際機場"},
                {"code": "RMQ", "name": "台中國際機場"},
                {"code": "HND", "name": "東京羽田機場"},
                {"code": "NRT", "name": "東京成田國際機場"},
                {"code": "HKG", "name": "香港國際機場"},
                {"code": "ICN", "name": "首爾仁川國際機場"},
                {"code": "TTT", "name": "台東機場"},
                {"code": "KYD", "name": "蘭嶼機場"},
                {"code": "KNH", "name": "金門機場"},
                {"code": "MZG", "name": "馬公機場"}
            ]
            return jsonify(fallback_airports)

        # 查詢資料庫中的機場資料
        cursor = conn.cursor()
        query = """
        SELECT airport_id as code, airport_name_zh as name 
        FROM Airports 
        ORDER BY airport_name_zh
        """
        
        cursor.execute(query)
        
        # 將查詢結果轉換為字典列表
        airports = []
        for row in cursor.fetchall():
            airports.append({
                "code": row.code,
                "name": row.name
            })
        
        cursor.close()
        conn.close()
        
        # 如果沒有找到任何資料，使用備用資料
        if not airports:
            logger.warning("資料庫中沒有找到機場資料，使用備用資料")
            airports = [
                {"code": "TPE", "name": "台灣桃園國際機場"},
                {"code": "TSA", "name": "台北松山機場"},
                # 其他備用資料...
            ]
        
        return jsonify(airports)
        
    except Exception as e:
        logger.error(f"獲取機場資料時出錯: {e}")
        # 發生錯誤時使用備用資料
        fallback_airports = [
            {"code": "TPE", "name": "台灣桃園國際機場"},
            {"code": "TSA", "name": "台北松山機場"},
            {"code": "KHH", "name": "高雄國際機場"},
            {"code": "RMQ", "name": "台中國際機場"},
            {"code": "HND", "name": "東京羽田機場"},
            {"code": "NRT", "name": "東京成田國際機場"},
            {"code": "HKG", "name": "香港國際機場"},
            {"code": "ICN", "name": "首爾仁川國際機場"},
            {"code": "TTT", "name": "台東機場"},
            {"code": "KYD", "name": "蘭嶼機場"},
            {"code": "KNH", "name": "金門機場"},
            {"code": "MZG", "name": "馬公機場"}
        ]
        return jsonify(fallback_airports)

# 機場詳細資料端點（包含城市資訊）
@flight_blueprint.route('/airports/details', methods=['GET'])
def get_airports_with_city():
    """獲取所有機場列表，包含城市資訊"""
    try:
        conn = get_db_connection()
        if not conn:
            # 如果無法連接到資料庫，使用備用資料
            logger.warning("資料庫連接失敗，使用備用機場城市資料")
            fallback_airports = [
                {"code": "TPE", "name": "台灣桃園國際機場", "city_zh": "桃園", "country": "TW", "country_name": "台灣"},
                {"code": "TSA", "name": "台北松山機場", "city_zh": "臺北", "country": "TW", "country_name": "台灣"},
                {"code": "KHH", "name": "高雄國際機場", "city_zh": "高雄", "country": "TW", "country_name": "台灣"},
                {"code": "RMQ", "name": "台中清泉崗機場", "city_zh": "台中", "country": "TW", "country_name": "台灣"},
                {"code": "TTT", "name": "台東機場", "city_zh": "臺東", "country": "TW", "country_name": "台灣"},
                {"code": "KYD", "name": "蘭嶼機場", "city_zh": "臺東", "country": "TW", "country_name": "台灣"},
                {"code": "KNH", "name": "金門機場", "city_zh": "金門", "country": "TW", "country_name": "台灣"},
                {"code": "MZG", "name": "澎湖馬公機場", "city_zh": "澎湖", "country": "TW", "country_name": "台灣"},
                {"code": "HUN", "name": "花蓮機場", "city_zh": "花蓮", "country": "TW", "country_name": "台灣"},
                {"code": "GNI", "name": "綠島機場", "city_zh": "臺東", "country": "TW", "country_name": "台灣"},
                {"code": "MFK", "name": "北竿機場", "city_zh": "連江", "country": "TW", "country_name": "台灣"},
                {"code": "LZN", "name": "南竿機場", "city_zh": "連江", "country": "TW", "country_name": "台灣"},
                {"code": "TNN", "name": "台南機場", "city_zh": "台南", "country": "TW", "country_name": "台灣"},
                {"code": "CMJ", "name": "七美機場", "city_zh": "澎湖", "country": "TW", "country_name": "台灣"},
                {"code": "WOT", "name": "望安機場", "city_zh": "澎湖", "country": "TW", "country_name": "台灣"},
                
                {"code": "HND", "name": "東京羽田機場", "city_zh": "東京", "country": "JP", "country_name": "日本"},
                {"code": "NRT", "name": "東京成田國際機場", "city_zh": "東京", "country": "JP", "country_name": "日本"},
                {"code": "KIX", "name": "大阪關西國際機場", "city_zh": "大阪", "country": "JP", "country_name": "日本"},
                {"code": "FUK", "name": "福岡機場", "city_zh": "福岡", "country": "JP", "country_name": "日本"},
                {"code": "CTS", "name": "札幌新千歲機場", "city_zh": "札幌", "country": "JP", "country_name": "日本"},
                {"code": "NGO", "name": "名古屋中部國際機場", "city_zh": "名古屋", "country": "JP", "country_name": "日本"},
                {"code": "OKA", "name": "沖繩那霸機場", "city_zh": "沖繩", "country": "JP", "country_name": "日本"},
                
                {"code": "HKG", "name": "香港國際機場", "city_zh": "香港", "country": "HK", "country_name": "香港"},
                {"code": "ICN", "name": "首爾仁川國際機場", "city_zh": "首爾", "country": "KR", "country_name": "韓國"},
                {"code": "GMP", "name": "首爾金浦國際機場", "city_zh": "首爾", "country": "KR", "country_name": "韓國"},
                {"code": "PVG", "name": "上海浦東國際機場", "city_zh": "上海", "country": "CN", "country_name": "中國大陸"},
                {"code": "PEK", "name": "北京首都國際機場", "city_zh": "北京", "country": "CN", "country_name": "中國大陸"},
                {"code": "SIN", "name": "新加坡樟宜機場", "city_zh": "新加坡", "country": "SG", "country_name": "新加坡"},
                {"code": "BKK", "name": "曼谷素萬那普機場", "city_zh": "曼谷", "country": "TH", "country_name": "泰國"},
                {"code": "MNL", "name": "馬尼拉尼諾伊阿基諾國際機場", "city_zh": "馬尼拉", "country": "PH", "country_name": "菲律賓"},
                
                {"code": "HIJ", "name": "廣島機場", "city_zh": "廣島", "country": "JP", "country_name": "日本"},
                {"code": "SDJ", "name": "仙台機場", "city_zh": "仙台", "country": "JP", "country_name": "日本"},
                {"code": "KIJ", "name": "新潟機場", "city_zh": "新潟", "country": "JP", "country_name": "日本"},
                {"code": "ADL", "name": "阿德萊德機場", "city_zh": "阿德萊德", "country": "AU", "country_name": "澳洲"},
                {"code": "ANC", "name": "安克拉治機場", "city_zh": "安克拉治", "country": "US", "country_name": "美國"}
            ]
            return jsonify(fallback_airports)

        # 查詢資料庫中的機場資料，包含城市名稱
        cursor = conn.cursor()
        query = """
        SELECT airport_id as code, airport_name_zh as name, city_zh, country
        FROM Airports 
        ORDER BY airport_name_zh
        """
        
        cursor.execute(query)
        
        # 將查詢結果轉換為字典列表
        airports = []
        # 國家名稱對應
        country_names = {
            'TW': '台灣',
            'JP': '日本',
            'KR': '韓國',
            'CN': '中國大陸',
            'HK': '香港',
            'SG': '新加坡',
            'TH': '泰國',
            'PH': '菲律賓',
            'US': '美國',
            'CA': '加拿大',
            'AU': '澳洲',
            'NZ': '紐西蘭',
            'UK': '英國',
            'FR': '法國',
            'DE': '德國',
            'IT': '義大利',
            'ES': '西班牙'
        }
        
        for row in cursor.fetchall():
            country_code = row.country if row.country else 'XX'
            airports.append({
                "code": row.code,
                "name": row.name,
                "city_zh": row.city_zh if hasattr(row, 'city_zh') and row.city_zh else '未知城市',
                "country": country_code,
                "country_name": country_names.get(country_code, '未知國家')
            })
        
        cursor.close()
        conn.close()
        
        # 如果沒有找到任何資料，使用備用資料
        if not airports:
            logger.warning("資料庫中沒有找到機場城市資料，使用備用資料")
            return jsonify(fallback_airports)
        
        return jsonify(airports)
        
    except Exception as e:
        logger.error(f"獲取機場城市資料時出錯: {e}")
        # 發生錯誤時使用備用資料
        fallback_airports = [
            {"code": "TPE", "name": "台灣桃園國際機場", "city_zh": "桃園", "country": "TW", "country_name": "台灣"},
            {"code": "TSA", "name": "台北松山機場", "city_zh": "臺北", "country": "TW", "country_name": "台灣"},
            {"code": "KHH", "name": "高雄國際機場", "city_zh": "高雄", "country": "TW", "country_name": "台灣"},
            {"code": "RMQ", "name": "台中清泉崗機場", "city_zh": "台中", "country": "TW", "country_name": "台灣"},
            {"code": "HIJ", "name": "廣島機場", "city_zh": "廣島", "country": "JP", "country_name": "日本"},
            {"code": "SDJ", "name": "仙台機場", "city_zh": "仙台", "country": "JP", "country_name": "日本"},
            {"code": "KIJ", "name": "新潟機場", "city_zh": "新潟", "country": "JP", "country_name": "日本"},
            {"code": "ADL", "name": "阿德萊德機場", "city_zh": "阿德萊德", "country": "AU", "country_name": "澳洲"},
            {"code": "ANC", "name": "安克拉治機場", "city_zh": "安克拉治", "country": "US", "country_name": "美國"}
        ]
        return jsonify(fallback_airports)

# 航空公司列表端點
@flight_blueprint.route('/airlines', methods=['GET'])
def get_airlines():
    """獲取所有航空公司列表"""
    try:
        conn = get_db_connection()
        if not conn:
            # 如果無法連接到資料庫，使用備用資料
            logger.warning("資料庫連接失敗，使用備用航空公司資料")
            fallback_airlines = [
                {"id": "CI", "name": "中華航空"},
                {"id": "BR", "name": "長榮航空"},
                {"id": "AE", "name": "華信航空"},
                {"id": "B7", "name": "立榮航空"},
                {"id": "DA", "name": "德安航空"}
            ]
            return jsonify(fallback_airlines)

        # 查詢資料庫中的航空公司資料
        cursor = conn.cursor()
        query = """
        SELECT airline_id as id, airline_name_zh as name 
        FROM Airlines 
        ORDER BY airline_name_zh
        """
        
        cursor.execute(query)
        
        # 將查詢結果轉換為字典列表
        airlines = []
        for row in cursor.fetchall():
            airlines.append({
                "id": row.id,
                "name": row.name
            })
        
        cursor.close()
        conn.close()
        
        # 如果沒有找到任何資料，使用備用資料
        if not airlines:
            logger.warning("資料庫中沒有找到航空公司資料，使用備用資料")
            airlines = [
                {"id": "CI", "name": "中華航空"},
                {"id": "BR", "name": "長榮航空"},
                {"id": "AE", "name": "華信航空"},
                {"id": "B7", "name": "立榮航空"},
                {"id": "DA", "name": "德安航空"}
            ]
        
        return jsonify(airlines)
        
    except Exception as e:
        logger.error(f"獲取航空公司資料時出錯: {e}")
        # 發生錯誤時使用備用資料
        fallback_airlines = [
            {"id": "CI", "name": "中華航空"},
            {"id": "BR", "name": "長榮航空"},
            {"id": "AE", "name": "華信航空"},
            {"id": "B7", "name": "立榮航空"},
            {"id": "DA", "name": "德安航空"}
        ]
        return jsonify(fallback_airlines)

# 航班搜尋端點
@flight_blueprint.route('/flights/search', methods=['GET'])
def search_flights():
    """
    搜尋航班
    參數:
    - departure: 出發機場代碼
    - arrival: 到達機場代碼
    - date: 日期 (YYYY-MM-DD)
    - airline: (可選) 航空公司ID
    """
    # 獲取查詢參數
    departure = request.args.get('departure')
    arrival = request.args.get('arrival')
    date_str = request.args.get('date')
    airline = request.args.get('airline')
    
    # 參數驗證
    if not departure or not arrival or not date_str:
        return jsonify({
            "status": "error",
            "message": "缺少必要的搜尋參數",
            "required": ["departure", "arrival", "date"]
        }), 400
    
    # 日期格式驗證
    try:
        search_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "日期格式錯誤，請使用YYYY-MM-DD格式"
        }), 400
    
    # 嘗試從資料庫查詢航班資料
    try:
        conn = get_db_connection()
        if not conn:
            # 如果無法連接到資料庫，使用模擬資料
            logger.warning("資料庫連接失敗，使用模擬航班資料")
            flights = generate_mock_flights(departure, arrival, date_str, airline)
        else:
            # 從資料庫查詢航班
            cursor = conn.cursor()
            
            # 建立基本查詢
            query = """
            SELECT 
                f.flight_number, 
                f.scheduled_departure, 
                f.scheduled_arrival, 
                f.departure_airport_code, 
                f.arrival_airport_code, 
                f.airline_id, 
                f.flight_status, 
                f.aircraft_type, 
                f.price, 
                f.booking_link
            FROM Flights f
            WHERE 
                f.departure_airport_code = ? 
                AND f.arrival_airport_code = ? 
                AND CONVERT(date, f.scheduled_departure) = ?
            """
            
            params = [departure, arrival, search_date.strftime('%Y-%m-%d')]
            
            # 如果指定了航空公司，加入航空公司條件
            if airline:
                query += " AND f.airline_id = ?"
                params.append(airline)
            
            cursor.execute(query, params)
            
            # 處理查詢結果
            flights = []
            for row in cursor.fetchall():
                flights.append({
                    "flight_number": row.flight_number,
                    "scheduled_departure": row.scheduled_departure.isoformat() if row.scheduled_departure else None,
                    "scheduled_arrival": row.scheduled_arrival.isoformat() if row.scheduled_arrival else None,
                    "departure_airport_code": row.departure_airport_code,
                    "arrival_airport_code": row.arrival_airport_code,
                    "airline_id": row.airline_id,
                    "flight_status": row.flight_status,
                    "aircraft_type": row.aircraft_type,
                    "price": row.price,
                    "booking_link": row.booking_link or "#"
                })
            
            cursor.close()
            conn.close()
            
            # 如果沒有查詢到航班，使用模擬資料
            if not flights:
                logger.info(f"沒有找到從 {departure} 到 {arrival} 於 {date_str} 的航班，使用模擬資料")
                flights = generate_mock_flights(departure, arrival, date_str, airline)
    
    except Exception as e:
        logger.error(f"查詢航班時出錯: {e}")
        # 發生錯誤時使用模擬資料
        flights = generate_mock_flights(departure, arrival, date_str, airline)
    
    return jsonify({
        "status": "success",
        "data": flights,
        "count": len(flights),
        "search_criteria": {
            "departure": departure,
            "arrival": arrival,
            "date": date_str,
            "airline": airline
        }
    })

# 航線資訊端點
@flight_blueprint.route('/routes', methods=['GET'])
def get_routes():
    """獲取可用的直飛航線"""
    try:
        # 提供直飛航線資訊
        # 主要是德安航空的離島航線和主要的國際航線
        available_routes = [
            # 德安航空航線
            {"departure": "TTT", "arrival": "GNI", "airline": "DA"},  # 台東 -> 綠島
            {"departure": "GNI", "arrival": "TTT", "airline": "DA"},  # 綠島 -> 台東
            {"departure": "TTT", "arrival": "KYD", "airline": "DA"},  # 台東 -> 蘭嶼
            {"departure": "KYD", "arrival": "TTT", "airline": "DA"},  # 蘭嶼 -> 台東
            {"departure": "KHH", "arrival": "CMJ", "airline": "DA"},  # 高雄 -> 七美
            {"departure": "CMJ", "arrival": "KHH", "airline": "DA"},  # 七美 -> 高雄
            {"departure": "KHH", "arrival": "WOT", "airline": "DA"},  # 高雄 -> 望安
            {"departure": "WOT", "arrival": "KHH", "airline": "DA"},  # 望安 -> 高雄
            {"departure": "MZG", "arrival": "CMJ", "airline": "DA"},  # 馬公 -> 七美
            {"departure": "CMJ", "arrival": "MZG", "airline": "DA"},  # 七美 -> 馬公
            
            # 主要國際航線 (範例)
            {"departure": "TPE", "arrival": "HKG"},  # 台北 -> 香港
            {"departure": "HKG", "arrival": "TPE"},  # 香港 -> 台北
            {"departure": "TPE", "arrival": "NRT"},  # 台北 -> 東京成田
            {"departure": "NRT", "arrival": "TPE"},  # 東京成田 -> 台北
            {"departure": "TPE", "arrival": "HND"},  # 台北 -> 東京羽田
            {"departure": "HND", "arrival": "TPE"},  # 東京羽田 -> 台北
            {"departure": "TPE", "arrival": "ICN"},  # 台北 -> 首爾仁川
            {"departure": "ICN", "arrival": "TPE"},  # 首爾仁川 -> 台北
            {"departure": "TPE", "arrival": "KIX"},  # 台北 -> 大阪關西
            {"departure": "KIX", "arrival": "TPE"},  # 大阪關西 -> 台北
            {"departure": "TPE", "arrival": "BKK"},  # 台北 -> 曼谷
            {"departure": "BKK", "arrival": "TPE"},  # 曼谷 -> 台北
            {"departure": "TPE", "arrival": "SIN"},  # 台北 -> 新加坡
            {"departure": "SIN", "arrival": "TPE"},  # 新加坡 -> 台北
            
            # 台灣國內主要航線
            {"departure": "TSA", "arrival": "KHH"},  # 台北松山 -> 高雄
            {"departure": "KHH", "arrival": "TSA"},  # 高雄 -> 台北松山
            {"departure": "TSA", "arrival": "MZG"},  # 台北松山 -> 澎湖
            {"departure": "MZG", "arrival": "TSA"},  # 澎湖 -> 台北松山
            {"departure": "TSA", "arrival": "KNH"},  # 台北松山 -> 金門
            {"departure": "KNH", "arrival": "TSA"},  # 金門 -> 台北松山
            {"departure": "TSA", "arrival": "TTT"},  # 台北松山 -> 台東
            {"departure": "TTT", "arrival": "TSA"},  # 台東 -> 台北松山
            {"departure": "TSA", "arrival": "HUN"},  # 台北松山 -> 花蓮
            {"departure": "HUN", "arrival": "TSA"},  # 花蓮 -> 台北松山
            {"departure": "TSA", "arrival": "RMQ"},  # 台北松山 -> 台中
            {"departure": "RMQ", "arrival": "TSA"},  # 台中 -> 台北松山
            {"departure": "KHH", "arrival": "HUN"},  # 高雄 -> 花蓮
            {"departure": "HUN", "arrival": "KHH"},  # 花蓮 -> 高雄
        ]
        
        return jsonify(available_routes)
        
    except Exception as e:
        logger.error(f"獲取航線資料時出錯: {e}")
        return jsonify({"status": "error", "message": f"獲取航線資料時出錯: {str(e)}"}), 500

# 以下保留原始的模擬數據產生函數作為備用
def generate_mock_flights(departure, arrival, date_str, airline=None):
    """生成模擬航班數據"""
    import random
    
    # 轉換日期為Date對象
    search_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    search_date = search_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 每個機場對生成1-5個航班
    num_flights = random.randint(1, 5)
    flights = []
    
    # 航空公司選項
    airline_options = ['CI', 'BR', 'AE', 'B7', 'DA'] if not airline else [airline]
    
    for i in range(num_flights):
        # 選擇一個航空公司
        random_airline = random.choice(airline_options)
        
        # 生成航班號
        flight_number = f"{random_airline}{random.randint(100, 999)}"
        
        # 生成出發時間 (當天6AM到8PM)
        departure_time = search_date.replace(
            hour=random.randint(6, 20),
            minute=random.randint(0, 59)
        )
        
        # 計算飛行時間 (根據機場距離而定)
        flight_duration = 0
        # 國內線
        domestic_airports = ['TPE', 'TSA', 'KHH', 'RMQ', 'TTT', 'KYD', 'KNH', 'MZG']
        if departure in domestic_airports and arrival in domestic_airports:
            # 國內航線 - 30-120分鐘
            flight_duration = random.randint(30, 120)
        else:
            # 國際航線 - 120-720分鐘 (2-12小時)
            flight_duration = random.randint(120, 720)
        
        # 計算抵達時間
        arrival_time = departure_time + datetime.timedelta(minutes=flight_duration)
        
        # 生成價格 (國內/國際)
        if flight_duration < 120:
            # 國內線 - NT$1,000到NT$5,000
            price = random.randint(1000, 5000)
        else:
            # 國際線 - NT$5,000到NT$30,000
            price = random.randint(5000, 30000)
        
        # 生成航班狀態 (大部分是已排定)
        status_options = ['scheduled'] * 4 + ['delayed', 'cancelled']
        status = random.choice(status_options)
        
        # 添加航班到結果
        flights.append({
            "flight_number": flight_number,
            "scheduled_departure": departure_time.isoformat(),
            "scheduled_arrival": arrival_time.isoformat(),
            "departure_airport_code": departure,
            "arrival_airport_code": arrival,
            "airline_id": random_airline,
            "flight_status": status,
            "aircraft_type": get_random_aircraft_type(random_airline),
            "price": price,
            "booking_link": "#"
        })
    
    return flights

def get_random_aircraft_type(airline_code):
    """根據航空公司獲取隨機機型"""
    import random
    
    aircraft_types = {
        'CI': ['A330-300', 'A350-900', 'B737-800', 'B777-300ER'],
        'BR': ['A330-300', 'B777-300ER', 'B787-9', 'B787-10'],
        'AE': ['A320-200', 'A321neo', 'ATR 72-600'],
        'B7': ['A320-200', 'A321-200', 'ATR 72-600'],
        'DA': ['Dornier 228-212', 'ATR 72-600']
    }
    
    airline_aircrafts = aircraft_types.get(airline_code, ['A320-200'])
    return random.choice(airline_aircrafts)