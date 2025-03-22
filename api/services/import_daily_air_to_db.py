#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import pyodbc
import json
from datetime import datetime
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ImportDailyAirToDB')

# 加载环境变量
load_dotenv()

def import_flights_to_db(json_file):
    """将航班数据从JSON文件导入到数据库"""
    logger.info(f"开始从 {json_file} 导入航班数据到数据库...")
    
    try:
        # 读取JSON文件
        with open(json_file, 'r', encoding='utf-8') as f:
            flights = json.load(f)
        
        logger.info(f"从JSON文件读取了 {len(flights)} 个航班")
        
        # 获取数据库连接字符串
        connection_string = os.getenv('DB_CONNECTION_STRING')
        if not connection_string:
            logger.error("未设置数据库连接字符串")
            return
        
        # 连接到数据库
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # 准备导入
        inserted_count = 0
        updated_count = 0
        
        # 先将航班信息插入到TempFlights表
        for flight in flights:
            # 检查是否已存在相同航班
            check_query = """
            SELECT COUNT(*) FROM TempFlights 
            WHERE flight_number = ? AND scheduled_departure = ?
            """
            cursor.execute(check_query, 
                        (flight["flight_number"], flight["scheduled_departure"]))
            count = cursor.fetchone()[0]
            
            if count == 0:
                # 插入新航班
                insert_query = """
                INSERT INTO TempFlights (
                    flight_number, airline_id, departure_airport_code, 
                    arrival_airport_code, scheduled_departure, scheduled_arrival, 
                    aircraft_type, scrape_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_query, 
                            (flight["flight_number"], flight["airline_id"],
                            flight["departure_airport_code"], flight["arrival_airport_code"],
                            flight["scheduled_departure"], flight["scheduled_arrival"],
                            flight["aircraft_type"], flight.get("scrape_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
                inserted_count += 1
            else:
                # 更新已存在航班
                update_query = """
                UPDATE TempFlights SET
                    scheduled_arrival = ?,
                    scrape_date = ?
                WHERE flight_number = ? AND scheduled_departure = ?
                """
                cursor.execute(update_query, 
                            (flight["scheduled_arrival"], 
                            flight.get("scrape_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                            flight["flight_number"], flight["scheduled_departure"]))
                updated_count += 1
        
        # 提交事务
        conn.commit()
        logger.info(f"临时表导入完成: 插入 {inserted_count} 条记录, 更新 {updated_count} 条记录")
        
        # 从TempFlights合并到Flights表
        logger.info("开始从TempFlights合并到Flights表...")
        
        # 获取当前时间作为更新时间标记
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 合并数据到Flights表，如果存在则更新，不存在则插入
        merge_query = """
        MERGE INTO Flights AS target
        USING (
            SELECT 
                flight_number, 
                airline_id, 
                departure_airport_code, 
                arrival_airport_code, 
                scheduled_departure, 
                scheduled_arrival, 
                aircraft_type,
                scrape_date
            FROM TempFlights
            WHERE airline_id = 'DAC'  -- 仅处理德安航空的数据
        ) AS source
        ON (
            target.flight_number = source.flight_number AND 
            target.scheduled_departure = source.scheduled_departure
        )
        WHEN MATCHED THEN
            UPDATE SET 
                target.scheduled_arrival = source.scheduled_arrival,
                target.updated_at = ?
        WHEN NOT MATCHED THEN
            INSERT (
                flight_number, 
                airline_id, 
                departure_airport_code, 
                arrival_airport_code, 
                scheduled_departure, 
                scheduled_arrival, 
                aircraft_type,
                flight_status,
                created_at,
                updated_at,
                scrape_date
            )
            VALUES (
                source.flight_number, 
                source.airline_id, 
                source.departure_airport_code, 
                source.arrival_airport_code, 
                source.scheduled_departure, 
                source.scheduled_arrival, 
                source.aircraft_type,
                'Scheduled',
                ?,
                ?,
                source.scrape_date
            );
        """
        
        try:
            cursor.execute(merge_query, (now, now, now))
            conn.commit()
            
            # 获取操作影响的行数
            cursor.execute("SELECT @@ROWCOUNT")
            affected_rows = cursor.fetchone()[0]
            
            logger.info(f"Flights表合并完成: 共影响 {affected_rows} 条记录")
        except Exception as e:
            logger.error(f"合并到Flights表时出错: {str(e)}")
            conn.rollback()
        
        # 清理临时表（可选）
        # cursor.execute("DELETE FROM TempFlights WHERE airline_id = 'DAC'")
        # conn.commit()
        # logger.info("临时表清理完成")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        logger.info("数据导入完成")
        
    except Exception as e:
        logger.error(f"导入数据时出错: {str(e)}")

def run_import():
    """运行导入流程"""
    logger.info("开始德安航空数据导入流程")
    
    # 查找最新的JSON文件
    json_files = [f for f in os.listdir('.') if f.startswith('daily_air_flights_') and f.endswith('.json')]
    
    if not json_files:
        logger.error("未找到德安航空航班数据文件")
        return
    
    # 按照文件修改时间排序，获取最新的
    latest_file = max(json_files, key=lambda f: os.path.getmtime(f))
    logger.info(f"找到最新的数据文件: {latest_file}")
    
    # 导入数据
    import_flights_to_db(latest_file)
    
    logger.info("导入流程完成")

if __name__ == "__main__":
    run_import()