import os
import json
import pyodbc
import logging
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyAirDatabaseImport")

def load_flight_data(date_str):
    """加载指定日期的航班数据"""
    try:
        file_path = os.path.join("flight_data", f"dailyair_direct_flights_{date_str}.json")
        if not os.path.exists(file_path):
            logger.error(f"找不到航班数据文件: {file_path}")
            return []
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"从 {file_path} 加载了 {len(data)} 个航班数据")
        return data
    except Exception as e:
        logger.error(f"加载航班数据时出错: {str(e)}")
        return []

def connect_to_database():
    """连接到数据库"""
    try:
        # 尝试使用系统命令读取.env文件内容
        try:
            result = subprocess.run(["type", ".env"], capture_output=True, text=True, shell=True)
            env_content = result.stdout
            logger.info(f"读取.env文件成功，内容长度: {len(env_content)} 字符")
            
            # 从内容中提取连接字符串
            connection_string = None
            for line in env_content.splitlines():
                if line.startswith("DB_CONNECTION_STRING="):
                    connection_string = line[len("DB_CONNECTION_STRING="):].strip()
                    break
        except Exception as e:
            logger.error(f"使用系统命令读取.env文件时出错: {str(e)}")
            connection_string = None
        
        # 如果上面的方法失败，尝试使用硬编码的连接字符串
        if not connection_string:
            logger.warning("未能从.env文件读取连接字符串，使用硬编码值")
            connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=FlightBookingDB;Trusted_Connection=yes;"
        
        logger.info(f"数据库连接字符串: {connection_string[:20]}...")
        
        # 检查连接字符串是否有效
        if not connection_string or len(connection_string) < 10:
            logger.error("数据库连接字符串无效")
            return None
        
        # 创建数据库连接
        logger.info("尝试连接到数据库...")
        conn = pyodbc.connect(connection_string)
        logger.info("成功连接到数据库")
        
        # 检查并添加德安航空记录
        ensure_airline_exists(conn)
        
        return conn
    except Exception as e:
        logger.error(f"连接数据库时出错: {str(e)}")
        return None

def ensure_airline_exists(conn):
    """确保德安航空记录存在于Airlines表中"""
    try:
        cursor = conn.cursor()
        
        # 检查德安航空是否存在
        check_sql = "SELECT COUNT(*) FROM Airlines WHERE airline_code = 'DA'"
        cursor.execute(check_sql)
        exists = cursor.fetchone()[0] > 0
        
        # 如果不存在，添加记录
        if not exists:
            logger.info("德安航空记录不存在，正在添加...")
            insert_sql = """
            INSERT INTO Airlines (airline_id, airline_code, airline_name, country, created_at, updated_at)
            VALUES (3, 'DA', '德安航空', 'TW', GETDATE(), GETDATE())
            """
            cursor.execute(insert_sql)
            conn.commit()
            logger.info("成功添加德安航空记录")
        else:
            logger.info("德安航空记录已存在")
            
        cursor.close()
    except Exception as e:
        logger.error(f"检查或添加航空公司记录时出错: {str(e)}")
        # 错误不应终止程序，所以不抛出异常

def import_flight_data(conn, flights):
    """将航班数据导入到数据库"""
    if not conn or not flights:
        logger.warning("数据库连接无效或没有航班数据，无法导入")
        return 0, 0
    
    cursor = conn.cursor()
    insert_count = 0
    update_count = 0
    error_count = 0
    
    try:
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
                        airline_id = ?,
                        departure_airport_code = ?,
                        arrival_airport_code = ?,
                        scheduled_arrival = ?,
                        updated_at = GETDATE()
                    WHERE flight_number = ? AND scheduled_departure = ?
                    """
                    
                    cursor.execute(update_sql, (
                        3,  # 德安航空的airline_id改为3
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
                        3,  # 德安航空的airline_id改为3
                        flight["origin_airport"],
                        flight["destination_airport"],
                        arrival_time,
                        "on_time"  # 默认状态
                    ))
                    insert_count += 1
                
                # 每100条提交一次，避免大事务
                if (insert_count + update_count) % 100 == 0:
                    conn.commit()
                    logger.info(f"已处理 {insert_count + update_count} 条记录")
            
            except Exception as e:
                logger.error(f"处理航班 {flight.get('flight_number')} 时出错: {str(e)}")
                error_count += 1
                
        # 提交剩余事务
        conn.commit()
        
        # 计算耗时
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        logger.info(f"数据导入完成: 新增 {insert_count} 条, 更新 {update_count} 条, 失败 {error_count} 条, 耗时 {elapsed:.2f} 秒")
        
        return insert_count, update_count
    
    except Exception as e:
        logger.error(f"导入数据时出错: {str(e)}")
        # 回滚事务
        conn.rollback()
        return 0, 0
    
    finally:
        cursor.close()

def main():
    # 加载最近7天的数据
    date_strs = [
        "2025-03-22", "2025-03-23", "2025-03-24", 
        "2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28"
    ]
    
    # 连接数据库
    conn = connect_to_database()
    if not conn:
        logger.error("无法连接到数据库，程序终止")
        return
    
    total_insert = 0
    total_update = 0
    
    try:
        for date_str in date_strs:
            # 加载数据
            flights = load_flight_data(date_str)
            if not flights:
                logger.warning(f"日期 {date_str} 没有可用的航班数据，跳过")
                continue
            
            # 导入数据
            insert_count, update_count = import_flight_data(conn, flights)
            total_insert += insert_count
            total_update += update_count
            
            logger.info(f"日期 {date_str} 处理完成")
        
        logger.info(f"所有数据导入完成: 共新增 {total_insert} 条, 更新 {total_update} 条")
    
    finally:
        # 关闭数据库连接
        if conn:
            conn.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    logger.info("开始执行德安航空数据导入")
    main()
    logger.info("德安航空数据导入完成") 