import logging
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimplifiedFlightCrawler")

# 加载环境变量
load_dotenv()

# 定义简化版的UniAirScraper类
class UniAirScraper:
    def __init__(self):
        self.name = "立榮航空"
        self.airline_id = 2
        self.base_url = "https://www.uniair.com.tw/"
        self.schedule_url = "https://www.uniair.com.tw/schedule/"
        self.api_url = "https://www.uniair.com.tw/api/schedule/query"
    
    def get_api_data(self, date, origin, destination):
        """测试API请求结构"""
        logger.info(f"测试立榮航空API请求 {origin}-{destination} 日期:{date}")
        
        # 构建API请求
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.schedule_url,
            'Origin': 'https://www.uniair.com.tw'
        }
        
        data = {
            'departureDate': date,
            'originStation': origin,
            'destinationStation': destination,
            'tripType': 'OneWay',
            'isLCC': False
        }
        
        # 在测试模式下，只打印请求信息
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Data: {json.dumps(data, indent=2)}")
        
        # 返回模拟数据
        return [
            {
                'flight_number': 'B77312',
                'airline_id': self.airline_id,
                'origin_airport': origin,
                'destination_airport': destination,
                'departure_time': f"{date} 08:15:00",
                'arrival_time': f"{date} 09:05:00",
                'scrape_date': date
            }
        ]


# 简化版主函数
def main(date=None):
    """简化版的主函数，测试关键功能"""
    # 如果未指定日期，使用明天的日期
    if not date:
        tomorrow = datetime.now() + timedelta(days=1)
        date = tomorrow.strftime("%Y-%m-%d")
    
    logger.info(f"测试爬虫脚本，日期为 {date}")
    logger.info(f"TEST_MODE: {os.getenv('TEST_MODE', 'Not set')}")
    
    # 测试UniAirScraper
    scraper = UniAirScraper()
    routes = [
        {'origin': 'TSA', 'destination': 'MZG'},  # 松山-澎湖
        {'origin': 'TSA', 'destination': 'KNH'}   # 松山-金门
    ]
    
    all_flights = []
    
    # 测试API数据
    logger.info("测试立榮航空API数据获取...")
    for route in routes:
        origin = route['origin']
        destination = route['destination']
        flights = scraper.get_api_data(date, origin, destination)
        if flights:
            all_flights.extend(flights)
    
    # 显示结果统计
    logger.info("====== 测试结果统计 ======")
    logger.info(f"立榮航空: {len(all_flights)} 航班")
    logger.info("==========================")
    
    return all_flights


if __name__ == "__main__":
    flights = main()
    
    # 输出结果摘要
    if flights:
        print(f"\n成功测试，获取 {len(flights)} 个航班信息")
    else:
        print("\n测试失败，未获取到航班信息") 