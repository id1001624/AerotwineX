"""
臨時腳本，用於導入模擬航班數據到資料庫
修復了模塊導入問題
"""
import os
import sys
import datetime
import random
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
import pyodbc
from dotenv import load_dotenv

# 設定路徑以便正確導入模塊
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

# 從當前目錄直接導入模塊，而不是通過 api.services 路徑
import external_apis

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('flight_importer')

# 載入環境變數
env_path = os.path.join(project_root, '.env')
print(f"嘗試加載環境變數文件: {env_path}")
load_dotenv(env_path)

# 資料庫連接
DB_CONNECTION_STRING = os.getenv('DB_CONNECTION_STRING')
print(f"資料庫連接字串: {DB_CONNECTION_STRING}")

def get_db_connection():
    """獲取資料庫連接"""
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        return conn
    except Exception as e:
        logger.error(f"資料庫連接失敗: {e}")
        return None

def import_flight(flight_data: Dict) -> bool:
    """
    將單一航班資料導入資料庫

    參數:
        flight_data: 航班資料字典

    返回:
        是否成功導入
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 檢查資料是否已存在
        check_sql = """
        SELECT COUNT(*) FROM Flights 
        WHERE flight_number = ? AND departure_airport_code = ? 
        AND arrival_airport_code = ? AND CAST(scheduled_departure AS DATE) = CAST(? AS DATE)
        """
        
        # 準備查詢參數
        departure_date = flight_data.get('scheduled_departure')
        if isinstance(departure_date, datetime.datetime):
            departure_date_str = departure_date.strftime('%Y-%m-%d')
        else:
            departure_date_str = str(departure_date)
        
        cursor.execute(
            check_sql, 
            (
                flight_data.get('flight_number'), 
                flight_data.get('departure_airport_code'), 
                flight_data.get('arrival_airport_code'),
                departure_date_str
            )
        )
        
        if cursor.fetchval() > 0:
            logger.info(f"航班已存在: {flight_data.get('flight_number')} ({departure_date_str})")
            conn.close()
            return True
        
        # 插入新記錄
        insert_sql = """
        INSERT INTO Flights (
            flight_number, scheduled_departure, airline_id, departure_airport_code, 
            arrival_airport_code, scheduled_arrival, flight_status, aircraft_type, 
            price, booking_link, scrape_date, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
        """
        
        # 處理可能的空值
        scheduled_departure = flight_data.get('scheduled_departure')
        scheduled_arrival = flight_data.get('scheduled_arrival')
        
        cursor.execute(
            insert_sql, 
            (
                flight_data.get('flight_number'), 
                scheduled_departure,
                flight_data.get('airline_id'), 
                flight_data.get('departure_airport_code'), 
                flight_data.get('arrival_airport_code'), 
                scheduled_arrival, 
                flight_data.get('flight_status'), 
                flight_data.get('aircraft_type'), 
                flight_data.get('price'), 
                flight_data.get('booking_link'),
                datetime.datetime.now()
            )
        )
        
        conn.commit()
        logger.info(f"成功導入航班: {flight_data.get('flight_number')} ({departure_date_str})")
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"導入航班失敗: {e}")
        if conn:
            conn.close()
        return False

def generate_and_import_mock_flights(days=3, flights_per_day=20):
    """
    生成並導入模擬航班數據

    參數:
        days: 要生成的天數
        flights_per_day: 每天生成的航班數
    """
    print("開始生成並導入模擬航班數據...")
    today = datetime.datetime.now().date()
    
    # 定義常用機場和航空公司代碼
    airports = ['TPE', 'KHH', 'TSA', 'RMQ', 'HKG', 'NRT', 'ICN', 'HND', 'BKK', 'SIN']
    airlines = ['CI', 'BR', 'AE', 'CX', 'JL', 'KE', 'TG', 'SQ', 'MH', 'VN']
    
    # 優先處理的航線
    priority_routes = [
        ('TPE', 'HKG'), ('TPE', 'NRT'), ('TPE', 'HND'),
        ('TPE', 'ICN'), ('TPE', 'BKK'), ('TPE', 'SIN'),
        ('KHH', 'HKG'), ('TSA', 'HND')
    ]
    
    # 對於每一天生成數據
    for day_offset in range(days):
        flight_date = today + datetime.timedelta(days=day_offset)
        flight_date_str = flight_date.strftime('%Y-%m-%d')
        print(f"正在生成 {flight_date_str} 的航班數據...")
        
        # 生成模擬數據
        mock_flights = external_apis.generate_mock_flight_data(
            flight_date=flight_date_str,
            airlines=airlines,
            airports=airports,
            priority_routes=priority_routes
        )
        
        # 調整生成的航班數量
        if len(mock_flights) > flights_per_day:
            mock_flights = mock_flights[:flights_per_day]
        
        successful = 0
        for flight in mock_flights:
            if import_flight(flight):
                successful += 1
                
            # 添加小延遲避免太快寫入數據庫
            time.sleep(0.1)
        
        print(f"日期 {flight_date_str}: 成功導入 {successful}/{len(mock_flights)} 航班")
    
    print("模擬數據導入完成！")

if __name__ == "__main__":
    generate_and_import_mock_flights(days=3, flights_per_day=20)