import os
import json
import pyodbc
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyAirTestImport")

# 硬编码连接字符串
conn_str = "Driver={SQL Server};SERVER=LAPTOP-QJNCMBU4;DATABASE=FlightBookingDB;UID=sa;PWD=Id1001624"

def load_sample_data():
    """加载示例德安航空数据"""
    try:
        # 假设有一个样本数据文件
        file_path = "flight_data/dailyair_direct_flights_2025-03-22.json"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"从 {file_path} 加载了 {len(data)} 个航班数据")
        return data
    except Exception as e:
        logger.error(f"加载航班数据时出错: {str(e)}")
        
        # 如果文件不存在，创建一些样本数据
        logger.info("创建样本数据...")
        sample_data = [
            {
                "flight_number": "DA7501",
                "airline_code": "DA",
                "origin_airport": "TSA",
                "destination_airport": "MZG",
                "departure_time": "2025-03-22 10:00:00",
                "arrival_time": "2025-03-22 11:00:00"
            },
            {
                "flight_number": "DA7502",
                "airline_code": "DA",
                "origin_airport": "MZG",
                "destination_airport": "TSA",
                "departure_time": "2025-03-22 12:00:00",
                "arrival_time": "2025-03-22 13:00:00"
            },
            {
                "flight_number": "DA7301",
                "airline_code": "DA",
                "origin_airport": "KHH",
                "destination_airport": "KNH",
                "departure_time": "2025-03-22 14:00:00",
                "arrival_time": "2025-03-22 15:00:00"
            }
        ]
        return sample_data

def import_flight_data(flights):
    """将航班数据导入到数据库"""
    if not flights:
        logger.warning("没有航班数据，无法导入")
        return 0, 0
    
    try:
        # 连接到数据库
        logger.info("连接到数据库...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        insert_count = 0
        update_count = 0
        error_count = 0
        
        # 开始计时
        start_time = datetime.now()
        logger.info(f"开始导入 {len(flights)} 个航班数据")
        
        for flight in flights:
            try:
                # 确保时间格式正确（处理中文冒号等情况）
                dep_time_str = flight["departure_time"].replace("：", ":")
                arr_time_str = flight["arrival_time"].replace("：", ":")
                
                # 解析时间
                departure_time = datetime.strptime(dep_time_str, "%Y-%m-%d %H:%M:%S")
                arrival_time = datetime.strptime(arr_time_str, "%Y-%m-%d %H:%M:%S")
                
                # 检查航班是否已存在
                check_sql = """
                SELECT COUNT(*) FROM flights 
                WHERE flight_number = ? AND scheduled_departure = ?
                """
                
                cursor.execute(check_sql, (flight["flight_number"], departure_time))
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    # 更新现有航班
                    update_sql = """
                    UPDATE flights SET
                        arrival_airport_code = ?,
                        scheduled_arrival = ?,
                        flight_status = ?,
                        updated_at = GETDATE()
                    WHERE flight_number = ? AND scheduled_departure = ?
                    """
                    
                    cursor.execute(update_sql, (
                        flight["destination_airport"],
                        arrival_time,
                        "on_time",
                        flight["flight_number"],
                        departure_time
                    ))
                    update_count += 1
                    logger.info(f"更新航班: {flight['flight_number']}, {departure_time}")
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
                        flight["airline_code"],  # 直接使用airline_code
                        flight["origin_airport"],
                        flight["destination_airport"],
                        arrival_time,
                        "on_time"  # 默认状态
                    ))
                    insert_count += 1
                    logger.info(f"插入新航班: {flight['flight_number']}, {departure_time}")
                
                # 每次提交，以便立即可见
                conn.commit()
            
            except Exception as e:
                logger.error(f"处理航班 {flight.get('flight_number')} 时出错: {str(e)}")
                error_count += 1
        
        # 计算耗时
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        logger.info(f"数据导入完成: 新增 {insert_count} 条, 更新 {update_count} 条, 失败 {error_count} 条, 耗时 {elapsed:.2f} 秒")
        
        # 关闭连接
        cursor.close()
        conn.close()
        logger.info("数据库连接已关闭")
        
        return insert_count, update_count
    
    except Exception as e:
        logger.error(f"导入数据时出错: {str(e)}")
        return 0, 0

def main():
    logger.info("开始执行德安航空数据导入测试")
    
    # 加载样本数据
    flights = load_sample_data()
    
    # 导入数据
    insert_count, update_count = import_flight_data(flights)
    
    # 输出结果
    logger.info(f"测试完成: 共新增 {insert_count} 条, 更新 {update_count} 条")
    
    # 验证导入结果
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # 查询刚导入的航班
        cursor.execute("SELECT * FROM flights WHERE flight_number LIKE 'DA%'")
        rows = cursor.fetchall()
        
        logger.info(f"验证结果: 数据库中共有 {len(rows)} 个德安航空航班")
        for row in rows:
            logger.info(f"航班: {row.flight_number}, 出发: {row.scheduled_departure}, 从 {row.departure_airport_code} 到 {row.arrival_airport_code}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"验证导入结果时出错: {str(e)}")

if __name__ == "__main__":
    main() 