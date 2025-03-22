import os
import json
import logging
from datetime import datetime
from collections import Counter, defaultdict

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FlightSummary")

class FlightSummary:
    """航班数据汇总类，用于分析和生成报告"""
    
    def __init__(self, data_dir="flight_data"):
        self.data_dir = data_dir
        self.flights = []
        self.dates = []
        self.airline_data = {}
        self.route_data = {}
        
        logger.info("初始化航班数据汇总工具")
    
    def load_flight_data(self, airline_prefix=None):
        """从JSON文件中加载航班数据
        
        Args:
            airline_prefix: 航空公司航班号前缀，如'DA'表示德安航空
        """
        if not os.path.exists(self.data_dir):
            logger.error(f"数据目录 {self.data_dir} 不存在")
            return False
        
        files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
        logger.info(f"在 {self.data_dir} 中找到 {len(files)} 个JSON文件")
        
        total_flights = 0
        for file in files:
            try:
                file_path = os.path.join(self.data_dir, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    flights = json.load(f)
                
                # 如果指定了航空公司前缀，则过滤数据
                if airline_prefix:
                    flights = [f for f in flights if f.get('flight_number', '').startswith(airline_prefix)]
                
                # 提取日期
                date_match = None
                for pattern in ["flights_", "direct_flights_"]:
                    if pattern in file:
                        date_str = file.split(pattern)[1].split('.')[0]
                        if len(date_str) == 10:  # YYYY-MM-DD
                            date_match = date_str
                            break
                
                if date_match and date_match not in self.dates:
                    self.dates.append(date_match)
                
                self.flights.extend(flights)
                total_flights += len(flights)
                logger.info(f"从 {file} 加载了 {len(flights)} 个航班数据")
            
            except Exception as e:
                logger.error(f"加载文件 {file} 时出错: {str(e)}")
        
        logger.info(f"总共加载了 {total_flights} 个航班数据，覆盖 {len(self.dates)} 个日期")
        return total_flights > 0
    
    def analyze_data(self):
        """分析航班数据"""
        if not self.flights:
            logger.warning("没有航班数据可分析")
            return False
        
        logger.info("开始分析航班数据...")
        
        # 按航空公司分组
        airlines = Counter()
        airline_routes = defaultdict(Counter)
        route_counts = Counter()
        airport_counts = Counter()
        time_distribution = defaultdict(int)
        
        for flight in self.flights:
            # 航空公司统计
            airline = flight.get('airline', 'Unknown')
            airlines[airline] += 1
            
            # 航线统计
            origin = flight.get('origin_airport', '')
            destination = flight.get('destination_airport', '')
            route = f"{origin}-{destination}"
            
            if origin and destination:
                airline_routes[airline][route] += 1
                route_counts[route] += 1
                airport_counts[origin] += 1
                airport_counts[destination] += 1
            
            # 时间分布统计
            dep_time = flight.get('departure_time', '')
            if dep_time and len(dep_time) >= 13:  # 确保有时间部分
                hour = dep_time[11:13]  # 提取小时部分
                if hour.isdigit():
                    time_distribution[int(hour)] += 1
        
        # 保存分析结果
        self.airline_data = {
            'flight_counts': dict(airlines),
            'routes': {airline: dict(routes) for airline, routes in airline_routes.items()}
        }
        
        self.route_data = {
            'route_counts': dict(route_counts),
            'airport_counts': dict(airport_counts),
            'time_distribution': dict(time_distribution)
        }
        
        logger.info("航班数据分析完成")
        return True
    
    def generate_report(self, output_file=None):
        """生成航班数据汇总报告
        
        Args:
            output_file: 报告输出文件路径，如果为None则打印到控制台
        """
        if not self.flights:
            logger.warning("没有航班数据可生成报告")
            return False
        
        if not self.airline_data or not self.route_data:
            logger.info("先进行数据分析...")
            self.analyze_data()
        
        # 生成报告内容
        report = []
        report.append("# 航班数据汇总报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"数据日期范围: {', '.join(sorted(self.dates))}")
        report.append(f"总航班数: {len(self.flights)}")
        report.append("\n## 航空公司统计")
        
        # 航空公司航班数量
        for airline, count in sorted(self.airline_data['flight_counts'].items(), key=lambda x: x[1], reverse=True):
            report.append(f"- {airline}: {count} 班次")
        
        # 热门航线
        report.append("\n## 热门航线")
        for route, count in sorted(self.route_data['route_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            origin, destination = route.split('-')
            report.append(f"- {origin} -> {destination}: {count} 班次")
        
        # 机场繁忙度
        report.append("\n## 机场繁忙度")
        for airport, count in sorted(self.route_data['airport_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
            report.append(f"- {airport}: {count} 班次")
        
        # 时间分布
        report.append("\n## 起飞时间分布")
        for hour in range(24):
            count = self.route_data['time_distribution'].get(hour, 0)
            bar = "#" * (count // 5 + 1) if count > 0 else ""
            report.append(f"- {hour:02d}:00-{hour:02d}:59: {count} 班次 {bar}")
        
        # 德安航空特定航线统计
        if '德安航空' in self.airline_data['routes']:
            report.append("\n## 德安航空航线详情")
            for route, count in sorted(self.airline_data['routes']['德安航空'].items(), key=lambda x: x[1], reverse=True):
                origin, destination = route.split('-')
                report.append(f"- {origin} -> {destination}: {count} 班次")
        
        # 保存或打印报告
        report_text = "\n".join(report)
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                logger.info(f"报告已保存至 {output_file}")
            except Exception as e:
                logger.error(f"保存报告时出错: {str(e)}")
                return False
        else:
            print("\n" + report_text)
        
        return True

def main():
    # 创建汇总工具
    summary = FlightSummary()
    
    # 加载德安航空数据
    summary.load_flight_data(airline_prefix="DA")
    
    # 分析数据
    summary.analyze_data()
    
    # 生成报告
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    report_file = os.path.join(reports_dir, f"dailyair_summary_{datetime.now().strftime('%Y%m%d')}.md")
    summary.generate_report(report_file)
    
    # 同时打印到控制台
    summary.generate_report()

if __name__ == "__main__":
    main() 