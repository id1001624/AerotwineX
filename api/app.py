from flask import Flask, jsonify, request
from flask_cors import CORS
import pyodbc
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import traceback

load_dotenv()  # 載入 .env 檔案中的環境變數

app = Flask(__name__)
CORS(app)  # 啟用跨域資源共享

# 添加根路由
@app.route('/')
def index():
    """API 根路由，顯示 API 使用說明"""
    return jsonify({
        "message": "歡迎使用 AerotwineX 航班 API",
        "available_endpoints": {
            "GET /api/airports": "獲取機場列表",
            "GET /api/destinations?departure=AIRPORT_CODE": "獲取可直飛的目的地列表",
            "GET /api/airlines": "獲取航空公司列表",
            "GET /api/airlines?departure=AIRPORT_CODE&destination=AIRPORT_CODE": "獲取特定航線的航空公司",
            "GET /api/flights?departure=AIRPORT_CODE&destination=AIRPORT_CODE&date=YYYY-MM-DD&airline=AIRLINE_CODE": "搜尋航班"
        },
        "documentation": "請參閱 README.md 了解更多信息"
    })

# 資料庫連接設定
DB_CONFIG = {
    'driver': '{SQL Server}',
    'server': 'LAPTOP-QJNCMBU4',
    'database': 'FlightBookingDB',
    'uid': 'sa',
    'pwd': 'Id1001624',
    'trusted_connection': 'no'
}

def get_db_connection():
    """建立與 MSSQL 資料庫的連接"""
    try:
        connection_string = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['uid']};PWD={DB_CONFIG['pwd']}"
        print(f"嘗試連接資料庫，連接字串: {connection_string}")
        conn = pyodbc.connect(connection_string)
        print("成功連接到資料庫!")
        return conn
    except Exception as e:
        print(f"資料庫連接錯誤: {str(e)}")
        traceback.print_exc()
        raise e

@app.route('/api/airports', methods=['GET'])
def get_airports():
    """獲取國內出發機場列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查詢國內機場
        print("執行機場查詢...")
        cursor.execute("""
            SELECT airport_id as code, airport_name_zh as name, city_zh as city 
            FROM Airports 
            WHERE airport_id IN ('TPE', 'TSA', 'KHH', 'RMQ', 'TNN', 'TTT', 'HUN')
        """)
        
        airports = []
        for row in cursor.fetchall():
            airports.append({
                'code': row.code,
                'name': row.name,
                'city': row.city
            })
        
        print(f"找到 {len(airports)} 個機場")
        conn.close()
        return jsonify(airports)
    
    except Exception as e:
        print(f"獲取機場時發生錯誤: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "error_details": traceback.format_exc()}), 500

@app.route('/api/destinations', methods=['GET'])
def get_destinations():
    """根據出發地獲取可直飛的目的地列表"""
    departure = request.args.get('departure')
    
    if not departure:
        return jsonify({"error": "需要提供出發機場代碼"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查詢可直飛的目的地
        print(f"查詢從 {departure} 出發的目的地...")
        cursor.execute("""
            SELECT DISTINCT f.arrival_airport_code as code, a.airport_name_zh as name, a.city_zh as city 
            FROM Flights f 
            JOIN Airports a ON f.arrival_airport_code = a.airport_id 
            WHERE f.departure_airport_code = ?
        """, (departure,))
        
        destinations = []
        for row in cursor.fetchall():
            destinations.append({
                'code': row.code,
                'name': row.name,
                'city': row.city
            })
        
        print(f"找到 {len(destinations)} 個從 {departure} 可直飛的目的地")
        conn.close()
        return jsonify(destinations)
    
    except Exception as e:
        print(f"Error getting destinations: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "error_details": traceback.format_exc()}), 500

@app.route('/api/airlines', methods=['GET'])
def get_airlines():
    """根據出發地和目的地獲取航空公司列表"""
    departure = request.args.get('departure')
    destination = request.args.get('destination')
    
    if not departure or not destination:
        # 如果沒有指定出發地和目的地，返回所有航空公司
        if not departure and not destination:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                print("獲取所有航空公司...")
                cursor.execute("SELECT airline_id as id, airline_name_zh as name FROM Airlines")
                
                airlines = []
                for row in cursor.fetchall():
                    airlines.append({
                        'id': row.id,
                        'name': row.name
                    })
                
                print(f"找到 {len(airlines)} 個航空公司")
                conn.close()
                return jsonify(airlines)
            
            except Exception as e:
                print(f"Error getting all airlines: {str(e)}")
                traceback.print_exc()
                return jsonify({"error": str(e), "error_details": traceback.format_exc()}), 500
        else:
            return jsonify({"error": "需要同時提供出發機場和目的地機場"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查詢特定航線的航空公司
        print(f"查詢 {departure} -> {destination} 航線的航空公司...")
        cursor.execute("""
            SELECT DISTINCT al.airline_id as id, al.airline_name_zh as name 
            FROM Flights f 
            JOIN Airlines al ON f.airline_id = al.airline_id 
            WHERE f.departure_airport_code = ? AND f.arrival_airport_code = ?
        """, (departure, destination))
        
        airlines = []
        for row in cursor.fetchall():
            airlines.append({
                'id': row.id,
                'name': row.name
            })
        
        print(f"找到 {len(airlines)} 個經營 {departure} -> {destination} 航線的航空公司")
        conn.close()
        return jsonify(airlines)
    
    except Exception as e:
        print(f"Error getting airlines: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "error_details": traceback.format_exc()}), 500

@app.route('/api/flights', methods=['GET'])
def get_flights():
    """獲取符合條件的航班"""
    departure = request.args.get('departure')
    destination = request.args.get('destination')
    date = request.args.get('date')
    airline = request.args.get('airline')
    
    if not departure or not destination:
        return jsonify({"error": "需要提供出發機場和目的地機場"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                f.flight_number,
                f.airline_id,
                f.departure_airport_code,
                f.arrival_airport_code,
                f.scheduled_departure,
                f.scheduled_arrival,
                f.flight_status,
                f.aircraft_type,
                f.price,
                a.airline_name_zh as airline_name
            FROM Flights f
            JOIN Airlines a ON f.airline_id = a.airline_id
            WHERE f.departure_airport_code = ?
            AND f.arrival_airport_code = ?
        """
        
        params = [departure, destination]
        
        # 增加日期條件（如果提供）
        if date:
            query += " AND CONVERT(date, f.scheduled_departure) = ?"
            params.append(date)
        
        # 增加航空公司條件（如果提供）
        if airline:
            query += " AND f.airline_id = ?"
            params.append(airline)
        
        # 按照起飛時間排序
        query += " ORDER BY f.scheduled_departure"
        
        print(f"執行航班查詢: {departure} -> {destination}" + (f", 日期: {date}" if date else "") + (f", 航空公司: {airline}" if airline else ""))
        print(f"SQL查詢: {query}")
        print(f"參數: {params}")
        
        cursor.execute(query, params)
        
        flights = []
        for row in cursor.fetchall():
            # 將 datetime 轉為 ISO 格式字符串
            try:
                # 檢查是否為字符串，如果是則已經格式化過了
                if isinstance(row.scheduled_departure, str):
                    scheduled_departure = row.scheduled_departure
                else:
                    scheduled_departure = row.scheduled_departure.isoformat() if row.scheduled_departure else None
                
                if isinstance(row.scheduled_arrival, str):
                    scheduled_arrival = row.scheduled_arrival
                else:
                    scheduled_arrival = row.scheduled_arrival.isoformat() if row.scheduled_arrival else None
            except Exception as e:
                print(f"日期格式轉換錯誤: {e}")
                # 如果格式化失敗，使用原值
                scheduled_departure = str(row.scheduled_departure) if row.scheduled_departure else None
                scheduled_arrival = str(row.scheduled_arrival) if row.scheduled_arrival else None
            
            flights.append({
                'flight_number': row.flight_number,
                'airline_id': row.airline_id,
                'airline_name': row.airline_name,
                'departure_airport_code': row.departure_airport_code,
                'arrival_airport_code': row.arrival_airport_code,
                'scheduled_departure': scheduled_departure,
                'scheduled_arrival': scheduled_arrival,
                'flight_status': row.flight_status,
                'aircraft_type': row.aircraft_type,
                'price': str(row.price) if row.price else None
            })
        
        print(f"找到 {len(flights)} 個符合條件的航班")
        conn.close()
        return jsonify(flights)
    
    except Exception as e:
        print(f"Error getting flights: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "error_details": traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)