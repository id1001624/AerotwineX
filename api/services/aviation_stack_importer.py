"""
AviationStack航班數據導入模組
用於將API獲取的航班資料導入數據庫
"""
import os
import datetime
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any
import pyodbc
from dotenv import load_dotenv

from api.services.external_apis import get_flights_for_configured_airlines_airports

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/aviation_stack_importer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('aviation_stack_importer')

# 載入環境變數
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# 資料庫連接
DB_CONNECTION_STRING = os.getenv('DB_CONNECTION_STRING')

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
            logger.debug(f"航班已存在: {flight_data.get('flight_number')} ({departure_date_str})")
            conn.close()
            return True
        
        # 插入新記錄 - 移除actual_departure, actual_arrival, data_source欄位
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
        logger.debug(f"成功導入航班: {flight_data.get('flight_number')} ({departure_date_str})")
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"導入航班失敗: {e}")
        if conn:
            conn.close()
        return False

def bulk_import_flights(
    flight_date: Optional[str] = None,
    limit: int = 100,
    max_api_calls: int = 20,
    use_cache: bool = True,
    use_mock_data: bool = False,
    priority_routes: Optional[List[Tuple[str, str]]] = None
) -> Tuple[int, int]:
    """
    批量導入航班資料

    參數:
        flight_date: 航班日期 (YYYY-MM-DD)
        limit: 最大導入數量
        max_api_calls: 最大API調用次數
        use_cache: 是否使用緩存
        use_mock_data: 是否在API不可用時使用模擬數據
        priority_routes: 優先航線列表

    返回:
        (成功導入數量, 總嘗試數量)
    """
    try:
        # 獲取航班數據
        flights = get_flights_for_configured_airlines_airports(
            flight_date=flight_date,
            max_api_calls=max_api_calls,
            use_cache=use_cache,
            use_mock_data=use_mock_data,
            priority_routes=priority_routes
        )
        
        # 限制數量
        if limit > 0 and len(flights) > limit:
            flights = flights[:limit]
        
        successful = 0
        total = len(flights)
        
        logger.info(f"開始批量導入 {total} 個航班...")
        
        # 按優先級排序航班，將真實API數據優先導入
        flights.sort(key=lambda x: 0 if x.get('data_source', '') == 'api' else 1)
        
        for i, flight in enumerate(flights):
            if import_flight(flight):
                successful += 1
            
            # 每導入10個航班顯示進度
            if (i + 1) % 10 == 0 or i == total - 1:
                logger.info(f"進度: {i+1}/{total} ({successful} 成功)")
            
            # 隨機延遲，避免過快寫入
            time.sleep(random.uniform(0.1, 0.3))
        
        success_rate = (successful / total * 100) if total > 0 else 0
        logger.info(f"導入完成: {successful}/{total} 成功率: {success_rate:.2f}%")
        
        return successful, total
    
    except Exception as e:
        logger.error(f"批量導入出錯: {e}")
        return 0, 0

def import_multiple_days(
    start_date: str,
    days: int = 1,
    flights_per_day: int = 50,
    max_api_calls_per_day: int = 10,
    use_cache: bool = True,
    use_mock_data: bool = True
) -> Dict[str, Tuple[int, int]]:
    """
    導入多天的航班資料

    參數:
        start_date: 開始日期 (YYYY-MM-DD)
        days: 天數
        flights_per_day: 每天最大導入航班數
        max_api_calls_per_day: 每天最大API調用次數
        use_cache: 是否使用緩存
        use_mock_data: 是否使用模擬數據

    返回:
        包含每天導入結果的字典 {日期: (成功數, 總數)}
    """
    results = {}
    
    try:
        start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        
        for day in range(days):
            current_date = start_date_obj + datetime.timedelta(days=day)
            date_str = current_date.strftime('%Y-%m-%d')
            
            logger.info(f"導入日期 {date_str} 的航班...")
            
            # 優先航線隨機變化以獲取不同航線的數據
            priority_routes = [
                ('TPE', 'HKG'), ('TPE', 'NRT'), ('TPE', 'HND'),
                ('TPE', 'ICN'), ('TPE', 'BKK'), ('TPE', 'SIN'),
                ('KHH', 'HKG'), ('TSA', 'HND')
            ]
            random.shuffle(priority_routes)
            priority_routes = priority_routes[:5]  # 每天只處理5個優先航線
            
            successful, total = bulk_import_flights(
                flight_date=date_str,
                limit=flights_per_day,
                max_api_calls=max_api_calls_per_day,
                use_cache=use_cache,
                use_mock_data=use_mock_data,
                priority_routes=priority_routes
            )
            
            results[date_str] = (successful, total)
            
            # 日期之間的間隔，避免API過載
            if day < days - 1:
                logger.info(f"等待5秒後處理下一天...")
                time.sleep(5)
        
        return results
        
    except Exception as e:
        logger.error(f"多日導入出錯: {e}")
        return results

# 獲取已導入的航班統計
def get_import_statistics(start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    獲取已導入航班的統計資訊

    參數:
        start_date: 統計開始日期 (可選)
        end_date: 統計結束日期 (可選)

    返回:
        包含統計資料的字典
    """
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        
        # 構建日期過濾條件
        date_filter = ""
        params = []
        
        if start_date or end_date:
            if start_date and end_date:
                date_filter = "WHERE CAST(scheduled_departure AS DATE) BETWEEN ? AND ?"
                # 轉換日期為字符串格式
                params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
            elif start_date:
                date_filter = "WHERE CAST(scheduled_departure AS DATE) >= ?"
                params = [start_date.strftime('%Y-%m-%d')]
            elif end_date:
                date_filter = "WHERE CAST(scheduled_departure AS DATE) <= ?"
                params = [end_date.strftime('%Y-%m-%d')]
        
        # 總航班數
        total_flights_sql = f"SELECT COUNT(*) FROM Flights {date_filter}"
        cursor.execute(total_flights_sql, params)
        total_flights = cursor.fetchval()
        
        # 按日期統計
        dates_sql = f"""
            SELECT CAST(scheduled_departure AS DATE) as flight_date, COUNT(*) as count 
            FROM Flights 
            {date_filter}
            GROUP BY CAST(scheduled_departure AS DATE)
            ORDER BY flight_date DESC
        """
        cursor.execute(dates_sql, params)
        dates = {}
        for row in cursor.fetchall():
            # 確保日期是字符串而不是日期對象
            date_str = row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0])
            dates[date_str] = row[1]
        
        # 按航空公司統計
        airlines_sql = f"""
            SELECT airline_id, COUNT(*) as count 
            FROM Flights 
            {date_filter}
            GROUP BY airline_id
            ORDER BY count DESC
        """
        cursor.execute(airlines_sql, params)
        airlines = {}
        for row in cursor.fetchall():
            airlines[row[0] or 'Unknown'] = row[1]
        
        # 按航線統計
        routes_sql = f"""
            SELECT departure_airport_code, arrival_airport_code, COUNT(*) as count 
            FROM Flights 
            {date_filter}
            GROUP BY departure_airport_code, arrival_airport_code
            ORDER BY count DESC
        """
        cursor.execute(routes_sql, params)
        routes = {}
        for row in cursor.fetchall():
            route = f"{row[0]}-{row[1]}"
            routes[route] = row[2]
        
        conn.close()
        
        result = {
            'total_flights': total_flights,
            'dates': dates,
            'airlines': airlines,
            'routes': routes,
            'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 添加日期範圍信息
        if start_date or end_date:
            result['date_range'] = {}
            if start_date:
                result['date_range']['start'] = start_date.strftime('%Y-%m-%d')
            if end_date:
                result['date_range']['end'] = end_date.strftime('%Y-%m-%d')
        
        return result
        
    except Exception as e:
        logger.error(f"獲取統計資訊失敗: {e}")
        if conn:
            conn.close()
        return {}

if __name__ == "__main__":
    # 簡單測試
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    print(f"導入今天 ({today}) 的航班資料...")
    
    successful, total = bulk_import_flights(
        flight_date=today,
        limit=20,
        max_api_calls=5,
        use_cache=True,
        use_mock_data=True
    )
    
    print(f"導入結果: {successful}/{total} 成功")
    
    # 獲取統計資料
    stats = get_import_statistics()
    if stats:
        print(f"資料庫中共有 {stats['total_flights']} 個航班")
        print(f"來源分佈: {stats['routes']}") 