import pyodbc
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DatabaseCheck")

# 硬编码连接字符串
conn_str = "Driver={SQL Server};SERVER=LAPTOP-QJNCMBU4;DATABASE=FlightBookingDB;UID=sa;PWD=Id1001624"
logger.info(f"连接字符串: {conn_str}")

try:
    # 连接到数据库
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # 查询表结构和数据
    def get_column_names(cursor, table_name):
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION")
        return [row[0] for row in cursor.fetchall()]
    
    # 获取Airlines表结构和数据
    logger.info("====== Airlines表结构 ======")
    airlines_columns = get_column_names(cursor, 'Airlines')
    logger.info(f"Airlines表列: {', '.join(airlines_columns)}")
    
    logger.info("\n====== Airlines表数据 ======")
    cursor.execute('SELECT * FROM Airlines')
    rows = cursor.fetchall()
    for row in rows:
        row_data = [f"{col}: {row[i]}" for i, col in enumerate(airlines_columns)]
        logger.info(", ".join(row_data))
    
    # 获取Airports表结构和数据
    logger.info("\n====== Airports表结构 ======")
    airports_columns = get_column_names(cursor, 'Airports')
    logger.info(f"Airports表列: {', '.join(airports_columns)}")
    
    logger.info("\n====== Airports表数据 ======")
    cursor.execute('SELECT * FROM Airports')
    rows = cursor.fetchall()
    for row in rows:
        row_data = [f"{col}: {row[i]}" for i, col in enumerate(airports_columns)]
        logger.info(", ".join(row_data))
    
    # 获取Flights表结构
    logger.info("\n====== Flights表结构 ======")
    flights_columns = get_column_names(cursor, 'flights')
    logger.info(f"Flights表列: {', '.join(flights_columns)}")
    
    # 查询Flights表数据量
    logger.info("\n====== Flights表数据量 ======")
    cursor.execute("SELECT COUNT(*) AS count FROM flights")
    count = cursor.fetchone()[0]
    logger.info(f"Flights表中共有 {count} 条记录")
    
    # 如果有数据，查看部分样例
    if count > 0:
        logger.info("\n====== Flights表样例数据 ======")
        cursor.execute("SELECT TOP 5 * FROM flights")
        rows = cursor.fetchall()
        for row in rows:
            row_data = [f"{col}: {row[i]}" for i, col in enumerate(flights_columns)]
            logger.info(", ".join(row_data))
    
    # 关闭连接
    cursor.close()
    conn.close()
    logger.info("数据库连接已关闭")

except Exception as e:
    logger.error(f"查询数据库时出错: {str(e)}") 