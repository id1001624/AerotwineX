import os
import pyodbc
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_table_structure():
    """检查Flights表的结构"""
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
        
        # 检查FlightBookingDB数据库中的表
        print("\n获取数据库中的所有表:")
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")
        
        # 特别检查Flights表
        table_name = "Flights"
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
                
                # 尝试找出所有包含"flight"的表
                print("\n尝试查找包含'flight'的表:")
                cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_NAME LIKE '%flight%'")
                flight_tables = cursor.fetchall()
                for table in flight_tables:
                    print(f"  - {table[0]}")
                    
                    # 输出这些表的结构
                    print(f"\n表 {table[0]} 的结构:")
                    cursor.execute(f"SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table[0]}'")
                    flight_columns = cursor.fetchall()
                    for col in flight_columns:
                        print(f"  - 名称: {col.COLUMN_NAME}, 类型: {col.DATA_TYPE}({col.CHARACTER_MAXIMUM_LENGTH if col.CHARACTER_MAXIMUM_LENGTH else ''}), 允许NULL: {col.IS_NULLABLE}")
        except Exception as e:
            print(f"查询{table_name}表结构时出错: {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"连接数据库或执行查询时出错: {e}")
        print(f"连接字符串: {connection_string}")

if __name__ == "__main__":
    check_table_structure() 