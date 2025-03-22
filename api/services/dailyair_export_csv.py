import os
import json
import csv
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DailyAirCSVExport")

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

def export_to_csv(flights, output_file):
    """将航班数据导出为CSV文件"""
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # CSV表头
        fieldnames = [
            "航班号", "航空公司", "航空公司代码", "出发机场", "出发机场名称",
            "到达机场", "到达机场名称", "出发时间", "到达时间", "运营日期", "数据来源"
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for flight in flights:
                # 确保时间格式正确（处理中文冒号等情况）
                dep_time_str = flight["departure_time"].replace("：", ":")
                arr_time_str = flight["arrival_time"].replace("：", ":")
                
                # 写入CSV行
                writer.writerow({
                    "航班号": flight["flight_number"],
                    "航空公司": flight["airline"],
                    "航空公司代码": flight["airline_code"],
                    "出发机场": flight["origin_airport"],
                    "出发机场名称": flight["origin_name"],
                    "到达机场": flight["destination_airport"],
                    "到达机场名称": flight["destination_name"],
                    "出发时间": dep_time_str,
                    "到达时间": arr_time_str,
                    "运营日期": flight["days_operated"],
                    "数据来源": flight["source"]
                })
        
        logger.info(f"成功导出 {len(flights)} 条航班数据到 {output_file}")
        return True
    except Exception as e:
        logger.error(f"导出CSV文件时出错: {str(e)}")
        return False

def export_all_dates():
    """导出所有日期的航班数据"""
    # 要处理的日期列表
    date_strs = [
        "2025-03-22", "2025-03-23", "2025-03-24", 
        "2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28"
    ]
    
    # 创建CSV输出目录
    csv_dir = "csv_exports"
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)
        logger.info(f"创建CSV输出目录: {csv_dir}")
    
    # 所有航班的合并列表
    all_flights = []
    
    # 处理每个日期
    for date_str in date_strs:
        flights = load_flight_data(date_str)
        if not flights:
            logger.warning(f"日期 {date_str} 没有可用的航班数据，跳过")
            continue
        
        # 导出单个日期的CSV
        output_file = os.path.join(csv_dir, f"dailyair_flights_{date_str}.csv")
        export_to_csv(flights, output_file)
        
        # 添加到合并列表
        all_flights.extend(flights)
    
    # 导出所有日期的合并CSV
    if all_flights:
        output_file = os.path.join(csv_dir, "dailyair_flights_all.csv")
        export_to_csv(all_flights, output_file)
        logger.info(f"成功导出所有日期的合并数据，共 {len(all_flights)} 条记录")
    else:
        logger.warning("没有找到任何航班数据，无法导出合并CSV")

def main():
    logger.info("开始导出德安航空数据为CSV格式")
    export_all_dates()
    logger.info("CSV导出完成")

if __name__ == "__main__":
    main() 