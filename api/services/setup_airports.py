import os
import pyodbc
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("setup_airports.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SetupAirports')

# 定义机场信息
airports = [
    {'iata': 'TPE', 'name_zh': '台灣桃園國際機場', 'name_en': 'Taiwan Taoyuan International Airport', 'city_zh': '桃園', 'city_en': 'Taoyuan', 'country': 'TW'},
    {'iata': 'TSA', 'name_zh': '臺北松山機場', 'name_en': 'Taipei Songshan Airport', 'city_zh': '臺北', 'city_en': 'Taipei', 'country': 'TW'},
    {'iata': 'RMQ', 'name_zh': '台中清泉崗機場', 'name_en': 'Taichung Airport', 'city_zh': '台中', 'city_en': 'Taichung', 'country': 'TW'},
    {'iata': 'KHH', 'name_zh': '高雄國際機場', 'name_en': 'Kaohsiung International Airport', 'city_zh': '高雄', 'city_en': 'Kaohsiung', 'country': 'TW'},
    {'iata': 'HUN', 'name_zh': '花蓮機場', 'name_en': 'Hualien Airport', 'city_zh': '花蓮', 'city_en': 'Hualien', 'country': 'TW'},
    {'iata': 'TTT', 'name_zh': '臺東機場', 'name_en': 'Taitung Airport', 'city_zh': '臺東', 'city_en': 'Taitung', 'country': 'TW'},
    {'iata': 'KNH', 'name_zh': '金門機場', 'name_en': 'Kinmen Airport', 'city_zh': '金門', 'city_en': 'Kinmen', 'country': 'TW'},
    {'iata': 'MZG', 'name_zh': '澎湖馬公機場', 'name_en': 'Penghu Magong Airport', 'city_zh': '澎湖', 'city_en': 'Penghu', 'country': 'TW'},
    {'iata': 'LZN', 'name_zh': '南竿機場', 'name_en': 'Nangan Airport', 'city_zh': '連江', 'city_en': 'Lienchiang', 'country': 'TW'},
    {'iata': 'MFK', 'name_zh': '北竿機場', 'name_en': 'Beigan Airport', 'city_zh': '連江', 'city_en': 'Lienchiang', 'country': 'TW'},
    {'iata': 'KYD', 'name_zh': '蘭嶼機場', 'name_en': 'Lanyu Airport', 'city_zh': '臺東', 'city_en': 'Taitung', 'country': 'TW'},
    {'iata': 'GNI', 'name_zh': '綠島機場', 'name_en': 'Ludao Airport', 'city_zh': '臺東', 'city_en': 'Taitung', 'country': 'TW'},
    {'iata': 'WOT', 'name_zh': '望安機場', 'name_en': 'Wang-an Airport', 'city_zh': '澎湖', 'city_en': 'Penghu', 'country': 'TW'},
    {'iata': 'CMJ', 'name_zh': '七美機場', 'name_en': 'Qimei Airport', 'city_zh': '澎湖', 'city_en': 'Penghu', 'country': 'TW'}
]

# 航空公司信息
airlines = [
    {'id': 'DA', 'name_en': 'Daily Air', 'name_zh': '德安航空'},
    {'id': 'B7', 'name_en': 'Uni Air', 'name_zh': '立榮航空'},
    {'id': 'AE', 'name_en': 'Mandarin Airlines', 'name_zh': '華信航空'}
]

def check_airports():
    """检查德安航空使用的机场代码是否都存在于数据库中"""
    connection_string = os.getenv('DB_CONNECTION_STRING')
    
    if not connection_string:
        logger.error("缺少数据库连接字符串环境变量 DB_CONNECTION_STRING")
        return False
    
    try:
        # 连接数据库
        logger.info("正在连接数据库...")
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        logger.info("数据库连接成功！")
        
        # 获取德安航空运营的机场代码
        daily_air_airport_codes = set()
        for airport in airports:
            daily_air_airport_codes.add(airport['iata'])
        
        logger.info(f"德安航空使用的机场代码: {', '.join(sorted(daily_air_airport_codes))}")
        
        # 检查Airports表中是否存在这些机场
        cursor.execute("SELECT airport_id FROM Airports")
        existing_airports = set([row.airport_id for row in cursor.fetchall()])
        logger.info(f"数据库中已有 {len(existing_airports)} 个机场记录")
        
        # 找出缺失的机场
        missing_airports = daily_air_airport_codes - existing_airports
        if missing_airports:
            logger.warning(f"以下 {len(missing_airports)} 个机场代码在数据库中不存在: {', '.join(sorted(missing_airports))}")
            
            # 检查数据库中Airports表的列名
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Airports'")
            columns = [row.COLUMN_NAME for row in cursor.fetchall()]
            logger.info(f"Airports表的列名: {columns}")
            
            # 插入缺失的机场数据
            logger.info("开始导入缺失的机场数据")
            for airport in airports:
                if airport['iata'] in missing_airports:
                    try:
                        # 构建SQL语句，根据实际列名进行调整
                        columns_str = "airport_id, airport_name_zh, airport_name_en"
                        values_str = "?, ?, ?"
                        params = [airport['iata'], airport['name_zh'], airport['name_en']]
                        
                        if 'city_zh' in columns:
                            columns_str += ", city_zh"
                            values_str += ", ?"
                            params.append(airport['city_zh'])
                        
                        if 'city_en' in columns:
                            columns_str += ", city_en"
                            values_str += ", ?"
                            params.append(airport['city_en'])
                        
                        if 'country' in columns:
                            columns_str += ", country"
                            values_str += ", ?"
                            params.append(airport['country'])
                        
                        if 'created_at' in columns:
                            columns_str += ", created_at"
                            values_str += ", GETDATE()"
                        
                        if 'updated_at' in columns:
                            columns_str += ", updated_at"
                            values_str += ", GETDATE()"
                        
                        sql = f"INSERT INTO Airports ({columns_str}) VALUES ({values_str})"
                        cursor.execute(sql, params)
                        logger.info(f"已导入机场 {airport['iata']} - {airport['name_zh']}")
                    
                    except Exception as e:
                        logger.error(f"导入机场 {airport['iata']} 时出错: {e}")
                        conn.rollback()
                        continue
            
            conn.commit()
            logger.info("机场数据导入完成")
            
            # 重新检查以确认导入成功
            cursor.execute("SELECT airport_id FROM Airports")
            updated_airports = set([row.airport_id for row in cursor.fetchall()])
            still_missing = daily_air_airport_codes - updated_airports
            
            if still_missing:
                logger.error(f"导入后仍有 {len(still_missing)} 个机场代码缺失: {', '.join(sorted(still_missing))}")
                return False
            else:
                logger.info("所有德安航空使用的机场代码现已存在于数据库中")
                return True
        else:
            logger.info("所有德安航空使用的机场代码已存在于数据库中")
            return True
    
    except Exception as e:
        logger.error(f"检查机场数据时出错: {e}")
        return False
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

def check_airlines():
    """检查航空公司是否存在于数据库中"""
    connection_string = os.getenv('DB_CONNECTION_STRING')
    
    if not connection_string:
        logger.error("缺少数据库连接字符串环境变量 DB_CONNECTION_STRING")
        return False
    
    try:
        # 连接数据库
        logger.info("正在连接数据库...")
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        logger.info("数据库连接成功！")
        
        # 检查Airlines表中是否存在德安航空
        cursor.execute("SELECT airline_id FROM Airlines WHERE airline_id = 'DA'")
        result = cursor.fetchone()
        
        if not result:
            logger.warning("德安航空(DA)在数据库中不存在")
            
            # 插入德安航空数据
            try:
                cursor.execute("""
                INSERT INTO Airlines (airline_id, airline_name_en, airline_name_zh, created_at, updated_at)
                VALUES (?, ?, ?, GETDATE(), GETDATE())
                """, ('DA', 'Daily Air', '德安航空'))
                
                conn.commit()
                logger.info("已导入德安航空数据")
                return True
            except Exception as e:
                logger.error(f"导入德安航空数据时出错: {e}")
                conn.rollback()
                return False
        else:
            logger.info("德安航空(DA)已存在于数据库中")
            return True
    
    except Exception as e:
        logger.error(f"检查航空公司数据时出错: {e}")
        return False
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    print("开始检查德安航空使用的机场数据...")
    airports_result = check_airports()
    print(f"机场数据检查结果: {'成功' if airports_result else '失败'}")
    
    print("\n开始检查航空公司数据...")
    airlines_result = check_airlines()
    print(f"航空公司数据检查结果: {'成功' if airlines_result else '失败'}")
    
    if airports_result and airlines_result:
        print("\n✅ 所有数据检查和导入成功完成！")
    else:
        print("\n❌ 数据检查和导入过程中存在问题，请查看日志获取详情。")