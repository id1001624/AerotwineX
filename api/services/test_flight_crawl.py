import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TestFlightCrawler")

# 加载环境变量
load_dotenv()

def main():
    """简化版的测试函数"""
    # 获取明天的日期
    tomorrow = datetime.now() + timedelta(days=1)
    date = tomorrow.strftime("%Y-%m-%d")
    
    logger.info(f"测试爬虫脚本，日期为 {date}")
    logger.info(f"TEST_MODE: {os.getenv('TEST_MODE', 'Not set')}")
    logger.info(f"DB_CONNECTION_STRING: {os.getenv('DB_CONNECTION_STRING', 'Not set')}")
    
    # 定义一些测试航班数据
    test_flights = [
        {
            'flight_number': 'DA7603',
            'airline_id': 1,
            'origin_airport': 'TTT',
            'destination_airport': 'KYD',
            'departure_time': f"{date} 10:00:00",
            'arrival_time': f"{date} 10:30:00",
            'scrape_date': date
        },
        {
            'flight_number': 'B77312',
            'airline_id': 2,
            'origin_airport': 'TSA',
            'destination_airport': 'MZG',
            'departure_time': f"{date} 08:15:00",
            'arrival_time': f"{date} 09:05:00",
            'scrape_date': date
        },
        {
            'flight_number': 'AE8234',
            'airline_id': 3,
            'origin_airport': 'TSA',
            'destination_airport': 'LZN',
            'departure_time': f"{date} 13:45:00",
            'arrival_time': f"{date} 14:45:00",
            'scrape_date': date
        }
    ]
    
    # 显示结果统计
    logger.info("====== 测试结果统计 ======")
    daily_air_count = len([f for f in test_flights if f['airline_id'] == 1])
    uni_air_count = len([f for f in test_flights if f['airline_id'] == 2])
    mandarin_count = len([f for f in test_flights if f['airline_id'] == 3])
    
    logger.info(f"德安航空: {daily_air_count} 航班")
    logger.info(f"立榮航空: {uni_air_count} 航班")
    logger.info(f"華信航空: {mandarin_count} 航班")
    logger.info(f"总计: {len(test_flights)} 航班")
    logger.info("==========================")
    
    return test_flights

if __name__ == "__main__":
    flights = main()
    
    # 输出结果摘要
    if flights:
        print(f"\n成功测试，获取 {len(flights)} 个航班信息")
    else:
        print("\n测试失败，未获取到航班信息") 