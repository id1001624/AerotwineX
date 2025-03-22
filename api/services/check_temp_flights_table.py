import os
import pyodbc
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_temp_table_structure():
    """检查TempFlights表的结构"""
    connection_string = os.getenv('DB_CONNECTION_STRING')
    
    if not connection_string:
        print("缺少数据库连接字符串环境变量 DB_CONNECTION_STRING")
        return
    
    try:
        # 连接数据库
        print("尝试连接数据库...")
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        print("数据库连接成功！")
        
        # 检查TempFlights表
        table_name = "TempFlights"
        print(f"\n检查{table_name}表的结构:")
        
        try:
            cursor.execute(f"SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
            columns = cursor.fetchall()
            
            if columns:
                print(f"{table_name}表的列:")
                for column in columns:
                    print(f"  - 名称: {column.COLUMN_NAME}, 类型: {column.DATA_TYPE}({column.CHARACTER_MAXIMUM_LENGTH if column.CHARACTER_MAXIMUM_LENGTH else ''}), 允许NULL: {column.IS_NULLABLE}")
            else:
                print(f"警告: 数据库中不存在{table_name}表")
        except Exception as e:
            print(f"查询{table_name}表结构时出错: {e}")
        
        # 尝试创建正确的临时表
        print("\n尝试创建正确的TempFlights表...")
        try:
            # 先删除已有的临时表
            cursor.execute("IF OBJECT_ID('TempFlights', 'U') IS NOT NULL DROP TABLE TempFlights")
            cursor.commit()
            
            # 创建新的临时表，与Flights表结构一致
            cursor.execute("""
            CREATE TABLE TempFlights (
                flight_number varchar(20) NOT NULL,
                airline_id varchar(20) NOT NULL,
                departure_airport_code varchar(10) NOT NULL,
                arrival_airport_code varchar(10) NOT NULL,
                scheduled_departure datetime2 NOT NULL,
                scheduled_arrival datetime2 NOT NULL,
                aircraft_type varchar(50) NULL,
                scrape_date datetime2 NULL
            )
            """)
            cursor.commit()
            print("临时表创建成功！")
            
            # 验证新创建的表结构
            cursor.execute(f"SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
            columns = cursor.fetchall()
            
            if columns:
                print(f"新的{table_name}表的列:")
                for column in columns:
                    print(f"  - 名称: {column.COLUMN_NAME}, 类型: {column.DATA_TYPE}({column.CHARACTER_MAXIMUM_LENGTH if column.CHARACTER_MAXIMUM_LENGTH else ''}), 允许NULL: {column.IS_NULLABLE}")
            
        except Exception as e:
            print(f"创建临时表时出错: {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"连接数据库或执行查询时出错: {e}")

if __name__ == "__main__":
    check_temp_table_structure() 