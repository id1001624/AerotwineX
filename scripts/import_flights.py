#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
統一航班數據導入命令行工具

支援從多個數據源導入航班資料到資料庫

使用方法:
    python import_flights.py --source aviation_stack --date 2023-04-15 --limit 100
    python import_flights.py --source daily_air
    python import_flights.py --source all --date 2023-04-15 --limit 50
    python import_flights.py --stats
    python import_flights.py --stats --start-date 2025-03-25 --end-date 2025-03-30

    參數:
        --source: 資料來源 [aviation_stack, daily_air, all]
        --date: 要導入的航班日期 (YYYY-MM-DD格式)
        --days: 要導入的天數 (默認為1)
        --limit: 每個來源每天導入的最大記錄數
        --api-calls: 每天最大API調用次數 (僅適用於AviationStack)
        --no-cache: 禁用緩存
        --no-mock: 禁用模擬數據
        --stats: 顯示導入統計資訊
        --start-date: 統計起始日期 (YYYY-MM-DD格式，僅與--stats一起使用)
        --end-date: 統計結束日期 (YYYY-MM-DD格式，僅與--stats一起使用)
"""

import os
import sys
import logging
import argparse
import datetime
import time
from pathlib import Path

# 添加專案根目錄到路徑以便導入模組
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from api.services.flight_import_service import get_service

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
    
    return logging.getLogger('import_flights')

def main():
    """主函數，處理命令行參數並運行導入操作"""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='統一航班數據導入工具')
    parser.add_argument('--source', choices=['aviation_stack', 'daily_air', 'all'], 
                      default='all', help='數據來源')
    parser.add_argument('--date', help='航班日期 (YYYY-MM-DD格式)', default=None)
    parser.add_argument('--days', type=int, help='要導入的天數', default=1)
    parser.add_argument('--limit', type=int, help='每個來源每天最大導入記錄數', default=50)
    parser.add_argument('--api-calls', type=int, help='每天最大API調用次數 (僅適用於AviationStack)', default=10)
    parser.add_argument('--no-cache', action='store_true', help='禁用緩存')
    parser.add_argument('--no-mock', action='store_true', help='禁用模擬數據')
    parser.add_argument('--stats', action='store_true', help='顯示導入統計資訊')
    parser.add_argument('--start-date', help='統計起始日期 (YYYY-MM-DD格式)', default=None)
    parser.add_argument('--end-date', help='統計結束日期 (YYYY-MM-DD格式)', default=None)
    
    args = parser.parse_args()
    
    # 獲取導入服務實例
    service = get_service()
    
    # 設置日期，如果未指定則使用當天日期
    start_date = args.date or datetime.datetime.now().strftime('%Y-%m-%d')
    
    # 解析日期以驗證格式
    try:
        datetime.datetime.strptime(start_date, '%Y-%m-%d')
    except ValueError:
        logger.error(f"無效的日期格式: {start_date}，應為 YYYY-MM-DD")
        return 1
    
    # 確定要使用的提供者
    providers = []
    if args.source == 'all':
        providers = service.list_providers()
    else:
        providers = [args.source]
    
    # 如果只請求統計資訊
    if args.stats:
        logger.info("獲取導入統計資訊...")
        
        # 驗證日期範圍參數格式
        stats_start_date = None
        stats_end_date = None
        
        if args.start_date:
            try:
                stats_start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').date()
            except ValueError:
                logger.error(f"無效的起始日期格式: {args.start_date}，應為 YYYY-MM-DD")
                return 1
                
        if args.end_date:
            try:
                stats_end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d').date()
            except ValueError:
                logger.error(f"無效的結束日期格式: {args.end_date}，應為 YYYY-MM-DD")
                return 1
        
        # 如果提供了日期範圍參數，顯示日期範圍信息
        if stats_start_date or stats_end_date:
            date_range_msg = "日期範圍: "
            if stats_start_date:
                date_range_msg += f"從 {stats_start_date} "
            if stats_end_date:
                date_range_msg += f"到 {stats_end_date} "
            logger.info(date_range_msg)
        
        stats = service.get_statistics(start_date=stats_start_date, end_date=stats_end_date)
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
    
    # 設置共同的參數
    kwargs = {
        'use_cache': not args.no_cache,
        'use_mock_data': not args.no_mock
    }
    
    # 為AviationStack提供者設置特定參數
    aviation_stack_kwargs = {
        **kwargs,
        'max_api_calls': args.api_calls
    }
    
    # 顯示導入配置
    logger.info(f"開始導入航班資料")
    logger.info(f"數據來源: {', '.join(providers)}")
    logger.info(f"開始日期: {start_date}")
    logger.info(f"天數: {args.days}")
    logger.info(f"每個來源每天限制: {args.limit}")
    logger.info(f"使用緩存: {not args.no_cache}")
    logger.info(f"使用模擬數據: {not args.no_mock}")
    
    # 導入多天數據
    all_results = {}
    
    for provider in providers:
        logger.info(f"從 {provider} 導入資料...")
        
        # 為不同提供者設置不同參數
        provider_kwargs = aviation_stack_kwargs if provider == 'aviation_stack' else kwargs
        
        if args.days > 1:
            results = service.import_multiple_days(
                provider_name=provider,
                start_date=start_date,
                days=args.days,
                limit_per_day=args.limit,
                **provider_kwargs
            )
            
            # 顯示每天的導入結果
            for date, (successful, total) in results.items():
                success_rate = (successful / total * 100) if total > 0 else 0
                logger.info(f"{provider} - 日期 {date}: {successful}/{total} 成功率: {success_rate:.2f}%")
                
                # 累加到全部結果中
                if date not in all_results:
                    all_results[date] = {}
                all_results[date][provider] = (successful, total)
        else:
            # 導入單天數據
            successful, total = service.import_flights(
                provider_name=provider,
                flight_date=start_date,
                limit=args.limit,
                **provider_kwargs
            )
            
            success_rate = (successful / total * 100) if total > 0 else 0
            logger.info(f"{provider} - {start_date}: {successful}/{total} 成功率: {success_rate:.2f}%")
            
            # 將結果添加到全部結果中
            if start_date not in all_results:
                all_results[start_date] = {}
            all_results[start_date][provider] = (successful, total)
    
    # 顯示總體結果
    logger.info("全部導入完成，總結果:")
    total_successful = 0
    total_records = 0
    
    for date in sorted(all_results.keys()):
        date_successful = 0
        date_total = 0
        
        for provider, (successful, total) in all_results[date].items():
            date_successful += successful
            date_total += total
        
        date_success_rate = (date_successful / date_total * 100) if date_total > 0 else 0
        logger.info(f"日期 {date}: {date_successful}/{date_total} 成功率: {date_success_rate:.2f}%")
        
        total_successful += date_successful
        total_records += date_total
    
    overall_success_rate = (total_successful / total_records * 100) if total_records > 0 else 0
    logger.info(f"總計: {total_successful}/{total_records} 總成功率: {overall_success_rate:.2f}%")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())