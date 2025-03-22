#!/usr/bin/env python
"""
從AviationStack API導入航班數據的命令行工具

使用方法:
    python import_aviation_stack_flights.py --date 2023-04-15 --limit 100

    參數:
        --date: 要導入的航班日期 (YYYY-MM-DD格式)
        --days: 要導入的天數 (默認為1)
        --limit: 每天導入的最大記錄數
        --api-calls: 每天最大API調用次數 (默認為10)
        --no-cache: 禁用緩存
        --no-mock: 禁用模擬數據
"""
import os
import sys
import logging
import argparse
import datetime
from pathlib import Path

# 添加專案根目錄到路徑以便導入模組
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from api.services.aviation_stack_importer import (
    bulk_import_flights,
    import_multiple_days,
    get_import_statistics
)

# 設置日誌
def setup_logging():
    """設置日誌配置"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"import_flights_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('import_aviation_stack')

def main():
    """主函數，處理命令行參數並運行導入操作"""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='從AviationStack API導入航班數據')
    parser.add_argument('--date', help='航班日期 (YYYY-MM-DD格式)', default=None)
    parser.add_argument('--days', type=int, help='要導入的天數', default=1)
    parser.add_argument('--limit', type=int, help='每天最大導入記錄數', default=50)
    parser.add_argument('--api-calls', type=int, help='每天最大API調用次數', default=10)
    parser.add_argument('--no-cache', action='store_true', help='禁用緩存')
    parser.add_argument('--no-mock', action='store_true', help='禁用模擬數據')
    parser.add_argument('--stats', action='store_true', help='顯示導入統計資訊')
    
    args = parser.parse_args()
    
    # 設置日期，如果未指定則使用當天日期
    start_date = args.date or datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 解析日期以驗證格式
    try:
        datetime.datetime.strptime(start_date, '%Y-%m-%d')
    except ValueError:
        logger.error(f"無效的日期格式: {start_date}，應為 YYYY-MM-DD")
        return 1
    
    # 如果只請求統計資訊
    if args.stats:
        logger.info("獲取導入統計資訊...")
        stats = get_import_statistics()
        if stats:
            logger.info(f"資料庫中共有 {stats['total_flights']} 個航班")
            
            # 顯示前5個最多航班的日期
            dates = sorted(stats['dates'].items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("前5個最多航班的日期:")
            for date, count in dates:
                logger.info(f"  {date}: {count}個航班")
            
            # 顯示前5個最多航班的航空公司
            airlines = sorted(stats['airlines'].items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("前5個最多航班的航空公司:")
            for airline, count in airlines:
                logger.info(f"  {airline}: {count}個航班")
            
            # 顯示前5個最多航班的航線
            routes = sorted(stats['routes'].items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info("前5個最熱門航線:")
            for route, count in routes:
                logger.info(f"  {route}: {count}個航班")
        else:
            logger.error("無法獲取統計資訊")
        return 0
    
    # 導入多天數據
    if args.days > 1:
        logger.info(f"開始從 {start_date} 導入 {args.days} 天的航班數據...")
        results = import_multiple_days(
            start_date=start_date,
            days=args.days,
            flights_per_day=args.limit,
            max_api_calls_per_day=args.api_calls,
            use_cache=not args.no_cache,
            use_mock_data=not args.no_mock
        )
        
        # 顯示每天的導入結果
        total_successful = 0
        total_records = 0
        for date, (successful, total) in results.items():
            success_rate = (successful / total * 100) if total > 0 else 0
            logger.info(f"日期 {date}: {successful}/{total} 成功率: {success_rate:.2f}%")
            total_successful += successful
            total_records += total
        
        # 顯示總體結果
        overall_success_rate = (total_successful / total_records * 100) if total_records > 0 else 0
        logger.info(f"總計: {total_successful}/{total_records} 總成功率: {overall_success_rate:.2f}%")
    
    # 導入單天數據
    else:
        logger.info(f"開始導入 {start_date} 的航班數據...")
        successful, total = bulk_import_flights(
            flight_date=start_date,
            limit=args.limit,
            max_api_calls=args.api_calls,
            use_cache=not args.no_cache,
            use_mock_data=not args.no_mock
        )
        
        success_rate = (successful / total * 100) if total > 0 else 0
        logger.info(f"完成導入: {successful}/{total} 成功率: {success_rate:.2f}%")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 