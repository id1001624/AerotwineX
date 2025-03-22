#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import os
import json
from datetime import datetime, timedelta
import time
import random
import re
import pyodbc
from dotenv import load_dotenv
import traceback

# 加載環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DailyAirRealTimeUpdater')

# 嘗試導入數據庫模組
try:
    from database.flight_db import FlightDB
except ImportError:
    # 如果無法導入，創建一個模擬的DB類
    class FlightDB:
        def __init__(self):
            self.connected = False
            self.test_mode = True
            logging.warning("使用模擬的FlightDB類 - 資料不會實際寫入資料庫")
        
        def connect(self):
            self.connected = True
            return True
        
        def get_daily_flights(self):
            logging.info("模擬從資料庫獲取德安航空今日航班")
            return [
                {
                    'flight_no': 'DA7510', 
                    'departure': 'TTT', 
                    'arrival': 'KYD',
                    'scheduled_departure_time': '09:30',
                    'scheduled_arrival_time': '10:00'
                },
                {
                    'flight_no': 'DA7512', 
                    'departure': 'TTT', 
                    'arrival': 'KYD',
                    'scheduled_departure_time': '14:00',
                    'scheduled_arrival_time': '14:30'
                },
                {
                    'flight_no': 'DA7507', 
                    'departure': 'KYD', 
                    'arrival': 'TTT',
                    'scheduled_departure_time': '10:20',
                    'scheduled_arrival_time': '10:50'
                }
            ]
        
        def update_flight_status(self, flight_updates):
            logging.info(f"模擬更新 {len(flight_updates)} 個航班狀態到資料庫")
            return len(flight_updates)
        
        def close(self):
            self.connected = False

class DailyAirRealTimeUpdater:
    """
    德安航空即時航班資訊更新工具
    用於從民航局網站獲取實際起降時間和航班狀態，並更新資料庫
    """
    
    def __init__(self):
        """初始化更新器"""
        self.name = "德安航空實時更新器"
        self.airline_id = "DA"  # 航空公司代碼
        
        # 民航局航班即時資訊網站 - 更新網址
        self.caa_base_url = "https://www.caa.gov.tw"
        self.immediate_flight_urls = {
            'TTT': "https://www.caa.gov.tw/Article.aspx?a=270&lang=1", # 臺東機場
            'GNI': "https://www.caa.gov.tw/Article.aspx?a=289&lang=1", # 綠島機場
            'KYD': "https://www.caa.gov.tw/Article.aspx?a=290&lang=1", # 蘭嶼機場
            'MZG': "https://www.caa.gov.tw/Article.aspx?a=291&lang=1", # 澎湖機場
            'WOT': "https://www.caa.gov.tw/Article.aspx?a=292&lang=1", # 望安機場
            'CMJ': "https://www.caa.gov.tw/Article.aspx?a=293&lang=1", # 七美機場
            'KHH': "https://www.caa.gov.tw/Article.aspx?a=258&lang=1", # 高雄國際機場
        }
        
        # 各機場官方網站航班資訊
        self.airport_websites = {
            'TTT': "https://www.tta.gov.tw/flight/daily", # 臺東機場
            'KHH': "https://www.kia.gov.tw/InstantScheduleC001120.aspx?ArrDep=1&AirLineDate=1&AirLineTime=all&AirCompany=DAC&All=1", # 高雄國際機場
            # 其他機場目前沒有獨立的網站或格式不一樣，需要進一步開發
            'GNI': None,
            'KYD': None,
            'MZG': None,
            'WOT': None,
            'CMJ': None,
        }
        
        self.session = requests.Session()
        # 設置請求頭，模擬瀏覽器訪問
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive'
        })
        
        # 航班狀態中英文映射
        self.status_mapping = {
            '準時': 'on_time',
            '正常': 'on_time',
            '延誤': 'delayed',
            '取消': 'cancelled',
            '已起飛': 'departed',
            '已降落': 'arrived',
            '已抵達': 'arrived',
            '': 'on_time'  # 默認值
        }
        
        # 獲取數據庫連接
        self.connection_string = os.getenv('DB_CONNECTION_STRING')
        self.test_mode = os.getenv('TEST_MODE', 'False').lower() in ('true', '1', 't')
        
        if self.test_mode:
            logger.info("運行在測試模式，不會連接數據庫")
            self.conn = None
            self.cursor = None
        else:
            if not self.connection_string:
                logger.error("缺少數據庫連接字符串環境變數 DB_CONNECTION_STRING")
                raise ValueError("缺少數據庫連接字符串環境變數 DB_CONNECTION_STRING")
            
            logger.info("初始化數據庫連接")
            try:
                self.conn = pyodbc.connect(self.connection_string, timeout=30)
                self.cursor = self.conn.cursor()
                logger.info("數據庫連接成功")
            except Exception as e:
                logger.error(f"數據庫連接失敗: {e}")
                raise
    
    def __del__(self):
        """清理資源"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
    
    def random_delay(self, min_seconds=1, max_seconds=3):
        """隨機延遲，避免請求過快"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"等待 {delay:.2f} 秒")
        time.sleep(delay)
    
    def get_flights_from_db(self):
        """從數據庫獲取需要更新的德安航空航班"""
        if self.test_mode:
            logger.info("測試模式: 跳過從數據庫獲取航班")
            return []
            
        logger.info("從數據庫獲取德安航空航班")
        try:
            # 獲取今天和明天的航班
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            
            self.cursor.execute("""
            SELECT flight_number, airline_id, departure_airport_code, arrival_airport_code,
                   scheduled_departure, scheduled_arrival, flight_status
            FROM Flights
            WHERE airline_id = 'DA'
            AND CONVERT(date, scheduled_departure) BETWEEN ? AND ?
            """, (today, tomorrow))
            
            flights = []
            for row in self.cursor.fetchall():
                flights.append({
                    'flight_number': row.flight_number,
                    'airline_id': row.airline_id,
                    'departure': row.departure_airport_code,
                    'arrival': row.arrival_airport_code,
                    'scheduled_departure': row.scheduled_departure,
                    'scheduled_arrival': row.scheduled_arrival,
                    'flight_status': row.flight_status,
                    'actual_departure': None,
                    'actual_arrival': None
                })
            
            logger.info(f"從數據庫獲取到 {len(flights)} 個德安航空航班")
            return flights
            
        except Exception as e:
            logger.error(f"從數據庫獲取航班時出錯: {e}")
            return []
    
    def parse_time(self, time_text, base_date=None):
        """解析時間文本為datetime對象"""
        if not time_text or time_text.strip() == '':
            return None
            
        if not base_date:
            base_date = datetime.now().date()
            
        # 清理和標準化時間文本
        time_text = time_text.strip()
        
        # 處理只有時間的情況 (例如: "14:30")
        if re.match(r'^\d{1,2}:\d{2}$', time_text):
            time_str = f"{base_date} {time_text}"
            try:
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                logger.warning(f"無法解析時間文本: {time_text}")
                return None
        
        # 處理帶有日期的情況 (例如: "2025-03-21 14:30")
        elif re.match(r'^\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}$', time_text):
            try:
                return datetime.strptime(time_text, '%Y-%m-%d %H:%M')
            except ValueError:
                logger.warning(f"無法解析時間文本: {time_text}")
                return None
        
        # 其他格式
        else:
            logger.warning(f"不支援的時間格式: {time_text}")
            return None
    
    def map_flight_status(self, status_text):
        """將中文航班狀態映射為英文狀態"""
        if not status_text:
            return 'on_time'
            
        # 預處理狀態文本
        status_text = status_text.strip()
        
        # 映射狀態
        for cn_status, en_status in self.status_mapping.items():
            if cn_status in status_text:
                return en_status
        
        # 默認返回準時
        return 'on_time'
    
    def get_flights_from_caa(self):
        """從民航局網站獲取航班資訊"""
        logger.info("從民航局網站獲取航班資訊...")
        
        all_flights = []
        
        for airport_code, url in self.immediate_flight_urls.items():
            logger.info(f"正在從民航局網站獲取 {airport_code} 機場航班資訊...")
            
            try:
                # 添加隨機延遲，避免快速連續請求
                delay_seconds = random.uniform(1.0, 3.0)
                logger.info(f"等待 {delay_seconds:.2f} 秒...")
                time.sleep(delay_seconds)
                
                response = self.session.get(url)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 在新的民航局網站結構中尋找航班資訊表格
                tables = soup.select('.flight-item')
                
                if not tables:
                    logger.warning(f"在 {airport_code} 機場網頁中找不到航班資訊表格")
                    continue
                
                flights_count = 0
                
                for table in tables:
                    # 檢查是否為德安航空航班
                    airline_info = table.select_one('.flight-carrier')
                    if not airline_info or ('德安' not in airline_info.get_text() and 'DA' not in airline_info.get_text()):
                        continue
                    
                    # 提取航班號
                    flight_elem = table.select_one('.flight-number')
                    if not flight_elem:
                        continue
                        
                    flight_number = flight_elem.get_text().strip()
                    # 提取純數字部分作為航班號
                    flight_match = re.search(r'(\d{4})', flight_number)
                    if not flight_match:
                        continue
                        
                    flight_number = flight_match.group(1)
                    
                    # 獲取航班狀態和時間信息
                    status_elem = table.select_one('.flight-status')
                    status_text = status_elem.get_text().strip() if status_elem else ""
                    
                    # 解析航班狀態
                    flight_status = 'on_time'  # 默認為準時
                    if '取消' in status_text:
                        flight_status = 'cancelled'
                    elif '延誤' in status_text:
                        flight_status = 'delayed'
                    elif '起飛' in status_text or '離站' in status_text:
                        flight_status = 'departed'
                    elif '抵達' in status_text or '到站' in status_text:
                        flight_status = 'arrived'
                    
                    # 獲取實際起飛/抵達時間
                    actual_time_elem = table.select_one('.flight-actualTime')
                    actual_time = actual_time_elem.get_text().strip() if actual_time_elem else None
                    
                    # 判斷航班方向（離站還是到站）
                    is_departure = False
                    is_arrival = False
                    
                    # 檢查出發地和目的地
                    origin_elem = table.select_one('.flight-origin')
                    dest_elem = table.select_one('.flight-destination')
                    
                    if origin_elem and dest_elem:
                        origin = origin_elem.get_text().strip()
                        destination = dest_elem.get_text().strip()
                        
                        # 根據當前機場代碼判斷方向
                        airport_name_mapping = {
                            'TTT': '台東',
                            'GNI': '綠島',
                            'KYD': '蘭嶼',
                            'MZG': '馬公',
                            'WOT': '望安',
                            'CMJ': '七美',
                            'KHH': '高雄'
                        }
                        
                        current_airport_name = airport_name_mapping.get(airport_code, '')
                        
                        if current_airport_name in origin:
                            is_departure = True
                        elif current_airport_name in destination:
                            is_arrival = True
                    
                    # 設置實際時間
                    actual_departure = None
                    actual_arrival = None
                    
                    if actual_time:
                        if is_departure and flight_status == 'departed':
                            actual_departure = self.parse_time(actual_time)
                        elif is_arrival and flight_status == 'arrived':
                            actual_arrival = self.parse_time(actual_time)
                    
                    # 創建航班資訊
                    flight_info = {
                        'flight_number': flight_number,
                        'flight_status': flight_status,
                        'actual_departure': actual_departure,
                        'actual_arrival': actual_arrival
                    }
                    
                    all_flights.append(flight_info)
                    flights_count += 1
                    logger.debug(f"航班: {flight_number}, 狀態: {flight_status}, 實際起飛: {actual_departure}, 實際抵達: {actual_arrival}")
                
                logger.info(f"從 {airport_code} 機場獲取了 {flights_count} 個航班信息")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"獲取 {airport_code} 機場資訊時發生錯誤: {str(e)}")
            except Exception as e:
                logger.error(f"處理 {airport_code} 機場資訊時發生錯誤: {str(e)}")
                logger.error(traceback.format_exc())
        
        logger.info(f"共從民航局網站獲取了 {len(all_flights)} 個航班信息")
        return all_flights
    
    def get_realtime_flight_info_from_airport(self, airport_code):
        """從機場網站獲取實時航班資訊"""
        url = self.airport_websites.get(airport_code)
        if not url:
            logger.warning(f"不支援的機場網站代碼: {airport_code}")
            return []
            
        logger.info(f"正在從 {airport_code} 機場網站獲取實時航班資訊...")
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 儲存航班資訊
            flights_info = []
            
            # 這裡需要根據不同機場網站的HTML結構進行特定的解析
            # 以台東機場為例 - 完全重寫解析邏輯
            if airport_code == 'TTT':
                # 直接針對表格內容定位
                departure_rows = []
                arrival_rows = []
                
                # 檢查所有表格結構，查找德安航空航班資訊 (先找頁面上所有可能包含航班資訊的表格)
                tables = soup.select('table')
                logger.info(f"找到 {len(tables)} 個表格")
                
                # 如果沒有找到表格，嘗試使用不同的選擇器
                if not tables:
                    tables = soup.select('.rwd-table')
                    logger.info(f"使用 .rwd-table 選擇器找到 {len(tables)} 個表格")
                
                if not tables:
                    tables = soup.select('div.table-responsive')
                    logger.info(f"使用 div.table-responsive 選擇器找到 {len(tables)} 個表格")
                
                # 嘗試獲取航班資訊 - 查看所有表格中的航空公司列
                for i, table in enumerate(tables):
                    rows = table.select('tr')
                    
                    if not rows:
                        continue
                    
                    # 檢查所有行，看是否包含德安航空信息
                    logger.info(f"表格 {i+1} 有 {len(rows)} 行")
                    
                    for row in rows:
                        row_text = row.get_text()
                        
                        # 檢查是否包含德安航空
                        if '德安' in row_text or 'DA' in row_text:
                            # 判斷是離站還是到站表格
                            if '離站' in row_text or 'DEPART' in row_text.upper():
                                departure_rows.append(row)
                                logger.info(f"找到離站航班: {row_text[:50]}...")
                            elif '抵達' in row_text or 'ARRIVED' in row_text.upper():
                                arrival_rows.append(row)
                                logger.info(f"找到到站航班: {row_text[:50]}...")
                
                # 處理離站航班
                logger.info(f"處理 {len(departure_rows)} 個離站航班行")
                for row in departure_rows:
                    cells = row.select('td')
                    if len(cells) < 4:
                        continue
                    
                    try:
                        # 嘗試提取離站航班信息 - 記錄所有單元格內容以便調試
                        cell_texts = [cell.get_text().strip() for cell in cells]
                        logger.info(f"離站航班單元格內容: {cell_texts}")
                        
                        # 從所有單元格中搜索航班號
                        flight_number = None
                        status = 'on_time'
                        actual_departure = None
                        
                        for cell_text in cell_texts:
                            # 提取航班號
                            if not flight_number:
                                flight_match = re.search(r'DA\s*(\d{4})', cell_text)
                                if flight_match:
                                    flight_number = flight_match.group(1)
                            
                            # 提取狀態
                            if '取消' in cell_text or 'CANCEL' in cell_text.upper():
                                status = 'cancelled'
                            elif '延誤' in cell_text or 'DELAY' in cell_text.upper():
                                status = 'delayed'
                            elif '離站' in cell_text or 'DEPART' in cell_text.upper():
                                status = 'departed'
                            
                            # 尋找時間格式 (HH:MM) 作為可能的實際時間
                            if status == 'departed':
                                time_match = re.search(r'(\d{1,2}:\d{2})', cell_text)
                                if time_match and len(time_match.group(1)) >= 4:  # 確保時間格式至少為 H:MM
                                    potential_time = time_match.group(1)
                                    # 如果時間出現在狀態列或實際時間列中，可能是實際時間
                                    if '預計' in cell_text or '實際' in cell_text or status == 'departed':
                                        actual_departure = self.parse_time(potential_time)
                        
                        if flight_number:
                            flight_info = {
                                'flight_number': flight_number,
                                'flight_status': status,
                                'actual_departure': actual_departure,
                                'actual_arrival': None
                            }
                            flights_info.append(flight_info)
                            logger.info(f"解析離站航班: {flight_number}, 狀態: {status}, 實際起飛: {actual_departure}")
                    
                    except Exception as e:
                        logger.error(f"處理離站航班行時出錯: {str(e)}")
                
                # 處理到站航班
                logger.info(f"處理 {len(arrival_rows)} 個到站航班行")
                for row in arrival_rows:
                    cells = row.select('td')
                    if len(cells) < 4:
                        continue
                    
                    try:
                        # 嘗試提取到站航班信息 - 記錄所有單元格內容以便調試
                        cell_texts = [cell.get_text().strip() for cell in cells]
                        logger.info(f"到站航班單元格內容: {cell_texts}")
                        
                        # 從所有單元格中搜索航班號
                        flight_number = None
                        status = 'on_time'
                        actual_arrival = None
                        
                        for cell_text in cell_texts:
                            # 提取航班號
                            if not flight_number:
                                flight_match = re.search(r'DA\s*(\d{4})', cell_text)
                                if flight_match:
                                    flight_number = flight_match.group(1)
                            
                            # 提取狀態
                            if '取消' in cell_text or 'CANCEL' in cell_text.upper():
                                status = 'cancelled'
                            elif '延誤' in cell_text or 'DELAY' in cell_text.upper():
                                status = 'delayed'
                            elif '抵達' in cell_text or 'ARRIVED' in cell_text.upper() or 'ARRIV' in cell_text.upper():
                                status = 'arrived'
                            
                            # 尋找時間格式 (HH:MM) 作為可能的實際時間
                            if status == 'arrived':
                                time_match = re.search(r'(\d{1,2}:\d{2})', cell_text)
                                if time_match and len(time_match.group(1)) >= 4:  # 確保時間格式至少為 H:MM
                                    potential_time = time_match.group(1)
                                    # 如果時間出現在狀態列或實際時間列中，可能是實際時間
                                    if '預計' in cell_text or '實際' in cell_text or status == 'arrived':
                                        actual_arrival = self.parse_time(potential_time)
                        
                        if flight_number:
                            # 檢查是否已有此航班資訊
                            existing_flight = next((f for f in flights_info if f['flight_number'] == flight_number), None)
                            
                            if existing_flight:
                                # 更新現有航班資訊
                                existing_flight['actual_arrival'] = actual_arrival
                                
                                # 更新狀態（如果需要）
                                if status == 'cancelled':
                                    existing_flight['flight_status'] = 'cancelled'
                                elif status == 'arrived' and existing_flight['flight_status'] not in ['cancelled', 'delayed']:
                                    existing_flight['flight_status'] = 'arrived'
                                
                                logger.info(f"更新航班: {flight_number}, 狀態: {existing_flight['flight_status']}, 實際抵達: {actual_arrival}")
                            else:
                                # 創建新航班資訊
                                flight_info = {
                                    'flight_number': flight_number,
                                    'flight_status': status,
                                    'actual_departure': None,
                                    'actual_arrival': actual_arrival
                                }
                                flights_info.append(flight_info)
                                logger.info(f"解析到站航班: {flight_number}, 狀態: {status}, 實際抵達: {actual_arrival}")
                    
                    except Exception as e:
                        logger.error(f"處理到站航班行時出錯: {str(e)}")
                
                # 如果沒有找到任何航班，使用更泛化的方法
                if not flights_info:
                    logger.info("透過行級搜索沒有找到航班，嘗試使用整頁搜索")
                    # 搜索網頁文本中的所有德安航班號
                    flight_matches = re.findall(r'(DA\s*(\d{4}))[^0-9]', soup.get_text())
                    logger.info(f"找到潛在的航班號: {flight_matches}")
                    
                    for match in flight_matches:
                        full_match, flight_number = match
                        
                        # 獲取航班號附近的文本來確定狀態
                        nearby_text = self.find_nearby_text(soup.get_text(), full_match, 100)
                        logger.info(f"航班 {flight_number} 附近文本: {nearby_text}")
                        
                        # 解析狀態
                        status = 'on_time'
                        if '取消' in nearby_text or 'CANCEL' in nearby_text.upper():
                            status = 'cancelled'
                        elif '延誤' in nearby_text or 'DELAY' in nearby_text.upper():
                            status = 'delayed'
                        elif '離站' in nearby_text or 'DEPART' in nearby_text.upper():
                            status = 'departed'
                        elif '抵達' in nearby_text or 'ARRIV' in nearby_text.upper():
                            status = 'arrived'
                        
                        # 尋找實際時間
                        actual_departure = None
                        actual_arrival = None
                        time_matches = re.findall(r'(\d{1,2}:\d{2})', nearby_text)
                        
                        if time_matches and (status == 'departed' or status == 'arrived'):
                            # 假設第一個時間為排定時間，第二個時間為實際時間
                            if len(time_matches) > 1:
                                actual_time = time_matches[1]
                                if status == 'departed':
                                    actual_departure = self.parse_time(actual_time)
                                elif status == 'arrived':
                                    actual_arrival = self.parse_time(actual_time)
                        
                        # 根據上下文判斷是離站還是到站
                        is_departure = '離站' in nearby_text or 'DEPART' in nearby_text.upper()
                        is_arrival = '抵達' in nearby_text or 'ARRIV' in nearby_text.upper() or '到站' in nearby_text
                        
                        flight_info = {
                            'flight_number': flight_number,
                            'flight_status': status,
                            'actual_departure': actual_departure if is_departure else None,
                            'actual_arrival': actual_arrival if is_arrival else None
                        }
                        
                        # 檢查是否已有此航班資訊
                        existing_flight = next((f for f in flights_info if f['flight_number'] == flight_number), None)
                        
                        if existing_flight:
                            # 合併資訊
                            if flight_info['actual_departure']:
                                existing_flight['actual_departure'] = flight_info['actual_departure']
                            if flight_info['actual_arrival']:
                                existing_flight['actual_arrival'] = flight_info['actual_arrival']
                                
                            # 更新狀態（如果需要）
                            if status == 'cancelled':
                                existing_flight['flight_status'] = 'cancelled'
                        else:
                            flights_info.append(flight_info)
                            logger.info(f"通過文本解析航班: {flight_number}, 狀態: {status}, 實際起飛: {actual_departure}, 實際抵達: {actual_arrival}")
            
            # 高雄國際機場的特定解析邏輯
            elif airport_code == 'KHH':
                # 這裡需要實現高雄機場特定的解析邏輯
                # 更新: 向高雄機場API發送請求獲取航班信息
                try:
                    # 德安航空代碼為DAC
                    url = "https://www.kia.gov.tw/InstantScheduleC001120.aspx?ArrDep=&AirLineDate=1&AirLineTime=all&AirCompany=DAC&All=1"
                    
                    response = self.session.get(url)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 尋找所有表格
                    tables = soup.select('table.table-b')
                    
                    for table in tables:
                        rows = table.select('tr')[1:]  # 跳過表頭
                        
                        for row in rows:
                            cells = row.select('td')
                            if len(cells) < 6:
                                continue
                                
                            try:
                                # 提取航班號 (第3列)
                                flight_text = cells[2].get_text().strip()
                                flight_match = re.search(r'DA\s*(\d{4})', flight_text)
                                if not flight_match:
                                    continue
                                    
                                flight_number = flight_match.group(1)
                                
                                # 確定是否為離站或到站信息
                                is_departure = 'InstantScheduleC001120.aspx?ArrDep=1' in url
                                is_arrival = 'InstantScheduleC001120.aspx?ArrDep=0' in url
                                
                                # 獲取預定時間 (第1列)
                                scheduled_time = cells[0].get_text().strip()
                                
                                # 獲取實際時間 (第4列)
                                actual_time = cells[3].get_text().strip()
                                
                                # 獲取狀態 (第6列)
                                status_text = cells[5].get_text().strip()
                                
                                # 映射狀態
                                flight_status = 'on_time'  # 默認為準時
                                if '取消' in status_text:
                                    flight_status = 'cancelled'
                                elif '延誤' in status_text:
                                    flight_status = 'delayed'
                                elif '已飛' in status_text:
                                    flight_status = 'departed'
                                elif '已降落' in status_text:
                                    flight_status = 'arrived'
                                
                                # 設置實際時間
                                actual_departure = None
                                actual_arrival = None
                                
                                if is_departure and flight_status == 'departed' and actual_time and actual_time != scheduled_time:
                                    actual_departure = self.parse_time(actual_time)
                                
                                if is_arrival and flight_status == 'arrived' and actual_time and actual_time != scheduled_time:
                                    actual_arrival = self.parse_time(actual_time)
                                
                                # 創建航班信息對象
                                flight_info = {
                                    'flight_number': flight_number,
                                    'flight_status': flight_status,
                                    'actual_departure': actual_departure,
                                    'actual_arrival': actual_arrival
                                }
                                
                                flights_info.append(flight_info)
                                
                            except Exception as e:
                                logger.error(f"解析高雄機場航班時出錯: {e}")
                    
                except Exception as e:
                    logger.error(f"獲取高雄機場航班資訊時出錯: {e}")
            
            logger.info(f"從 {airport_code} 機場網站獲取到 {len(flights_info)} 個航班資訊")
            return flights_info
            
        except requests.RequestException as e:
            logger.error(f"獲取 {airport_code} 機場網站資訊時出錯: {e}")
            return []
    
    def get_all_realtime_flight_info(self):
        """整合從所有來源獲取的實時航班資訊"""
        all_flights_info = {}
        
        # 從民航局網站獲取資訊
        caa_flights_info = self.get_flights_from_caa()
        self.random_delay(2, 5)  # 添加延遲避免請求過快
        
        for flight_info in caa_flights_info:
            flight_number = flight_info['flight_number']
            
            # 更新或添加航班資訊
            if flight_number in all_flights_info:
                # 合併資訊
                if flight_info['actual_departure']:
                    all_flights_info[flight_number]['actual_departure'] = flight_info['actual_departure']
                if flight_info['actual_arrival']:
                    all_flights_info[flight_number]['actual_arrival'] = flight_info['actual_arrival']
                
                # 更新航班狀態 (如果有更優先的狀態)
                current_status = all_flights_info[flight_number]['flight_status']
                new_status = flight_info['flight_status']
                
                # 狀態優先級: cancelled > delayed > departed > arrived > on_time
                status_priority = {
                    'cancelled': 5,
                    'delayed': 4,
                    'departed': 3,
                    'arrived': 2,
                    'on_time': 1
                }
                
                if status_priority.get(new_status, 0) > status_priority.get(current_status, 0):
                    all_flights_info[flight_number]['flight_status'] = new_status
            else:
                all_flights_info[flight_number] = flight_info
        
        # 從機場網站獲取額外資訊
        for airport_code in self.airport_websites.keys():
            flights_info = self.get_realtime_flight_info_from_airport(airport_code)
            self.random_delay(2, 5)  # 添加延遲避免請求過快
            
            for flight_info in flights_info:
                flight_number = flight_info['flight_number']
                
                # 更新或添加航班資訊
                if flight_number in all_flights_info:
                    # 合併資訊
                    if flight_info['actual_departure']:
                        all_flights_info[flight_number]['actual_departure'] = flight_info['actual_departure']
                    if flight_info['actual_arrival']:
                        all_flights_info[flight_number]['actual_arrival'] = flight_info['actual_arrival']
                    
                    # 更新航班狀態 (如果有更優先的狀態)
                    current_status = all_flights_info[flight_number]['flight_status']
                    new_status = flight_info['flight_status']
                    
                    # 狀態優先級: cancelled > delayed > departed > arrived > on_time
                    status_priority = {
                        'cancelled': 5,
                        'delayed': 4,
                        'departed': 3,
                        'arrived': 2,
                        'on_time': 1
                    }
                    
                    if status_priority.get(new_status, 0) > status_priority.get(current_status, 0):
                        all_flights_info[flight_number]['flight_status'] = new_status
                else:
                    all_flights_info[flight_number] = flight_info
        
        # 將字典轉為列表
        flights_list = list(all_flights_info.values())
        logger.info(f"總共獲取到 {len(flights_list)} 個實時航班資訊")
        
        return flights_list
    
    def update_flights_in_db(self, flights_info):
        """更新數據庫中的航班資訊"""
        if self.test_mode:
            logger.info("測試模式: 跳過更新數據庫")
            return True
            
        if not flights_info:
            logger.warning("沒有航班資訊可更新")
            return False
            
        logger.info(f"正在更新 {len(flights_info)} 個航班的實時資訊...")
        
        try:
            # 獲取當前時間
            update_time = datetime.now()
            
            # 執行更新
            for flight_info in flights_info:
                flight_number = flight_info['flight_number']
                flight_status = flight_info['flight_status']
                actual_departure = flight_info['actual_departure']
                actual_arrival = flight_info['actual_arrival']
                
                # 添加前綴確保是德安航空航班
                if len(flight_number) == 4:
                    flight_number = flight_number
                
                # 更新數據庫
                self.cursor.execute("""
                UPDATE Flights
                SET flight_status = ?,
                    actual_departure = ?,
                    actual_arrival = ?,
                    updated_at = ?
                WHERE flight_number = ?
                AND airline_id = 'DA'
                AND CONVERT(date, scheduled_departure) = CONVERT(date, GETDATE())
                """, (
                    flight_status,
                    actual_departure,
                    actual_arrival,
                    update_time,
                    flight_number
                ))
            
            # 提交更新
            self.conn.commit()
            logger.info(f"成功更新了 {self.cursor.rowcount} 個航班的實時資訊")
            
            return True
            
        except Exception as e:
            logger.error(f"更新數據庫時出錯: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def save_to_json(self, data, filename='daily_air_realtime_info.json'):
        """保存數據為JSON文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"daily_air_realtime_info_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4, default=str)
            logger.info(f"數據已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存數據時出錯: {e}")
    
    def update_realtime_info(self):
        """執行實時資訊更新流程"""
        logger.info("開始更新德安航空實時航班資訊")
        
        # 獲取實時航班資訊
        realtime_info = self.get_all_realtime_flight_info()
        
        if realtime_info:
            # 保存為JSON (用於調試或備份)
            self.save_to_json(realtime_info)
            
            # 更新數據庫
            self.update_flights_in_db(realtime_info)
            
            logger.info(f"實時資訊更新完成，共處理 {len(realtime_info)} 個航班")
        else:
            logger.warning("未獲取到任何實時航班資訊")
        
        return realtime_info

    def run(self):
        """執行實時更新流程"""
        try:
            logger.info(f"{self.name} 開始執行...")
            
            # 初始化連接
            self.db.connect()
            logger.info("數據庫連接成功...")
            
            # 取得今日德安航空航班
            daily_flights = self.db.get_daily_flights(self.airline_id)
            logger.info(f"今日德安航空共有 {len(daily_flights)} 個航班")
            
            # 從民航局網站獲取航班資訊
            caa_flights_info = self.get_flights_from_caa()
            logger.info(f"從民航局網站獲取了 {len(caa_flights_info)} 個航班資訊")
            
            # 儲存所有實時資訊
            all_realtime_info = []
            all_realtime_info.extend(caa_flights_info)
            
            # 從各機場網站獲取航班資訊 (備用方法)
            for airport_code in ['TTT', 'GNI', 'KYD', 'MZG', 'WOT', 'CMJ', 'KHH']:
                try:
                    # 添加隨機延遲，避免快速連續請求
                    delay_seconds = random.uniform(2.0, 5.0)
                    logger.info(f"等待 {delay_seconds:.2f} 秒...")
                    time.sleep(delay_seconds)
                    
                    airport_flights = self.get_realtime_flight_info_from_airport(airport_code)
                    logger.info(f"從 {airport_code} 機場網站獲取了 {len(airport_flights)} 個航班資訊")
                    all_realtime_info.extend(airport_flights)
                except Exception as e:
                    logger.error(f"從 {airport_code} 機場網站獲取資訊時發生錯誤: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 如果沒有獲取到任何實時資訊，記錄警告並結束
            if not all_realtime_info:
                logger.warning("未獲取到任何實時航班資訊")
                return
            
            # 更新航班狀態和實際時間
            updated_count = 0
            for flight in daily_flights:
                flight_number = flight.get('flight_number')
                if not flight_number:
                    continue
                
                # 尋找對應的實時資訊
                realtime_info = next((info for info in all_realtime_info if info['flight_number'] == flight_number), None)
                if not realtime_info:
                    continue
                
                # 更新航班狀態
                flight_status = realtime_info.get('flight_status')
                if flight_status:
                    self.db.update_flight_status(flight_number, flight_status)
                
                # 更新實際起飛時間
                actual_departure = realtime_info.get('actual_departure')
                if actual_departure:
                    self.db.update_actual_departure_time(flight_number, actual_departure)
                
                # 更新實際到達時間
                actual_arrival = realtime_info.get('actual_arrival')
                if actual_arrival:
                    self.db.update_actual_arrival_time(flight_number, actual_arrival)
                
                updated_count += 1
            
            logger.info(f"更新了 {updated_count} 個航班的實時資訊")
            
            # 保存實時資訊到JSON文件
            self.save_to_json(all_realtime_info)
            
        except Exception as e:
            logger.error(f"執行實時更新器時發生錯誤: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # 關閉數據庫連接
            try:
                self.db.disconnect()
                logger.info("數據庫連接已關閉")
            except:
                pass

    def find_nearby_text(self, full_text, target, char_range=100):
        """尋找目標字符串附近的文本"""
        try:
            index = full_text.find(target)
            if index == -1:
                return ""
                
            start = max(0, index - char_range)
            end = min(len(full_text), index + len(target) + char_range)
            
            return full_text[start:end]
        except Exception as e:
            logger.error(f"尋找附近文本時出錯: {str(e)}")
            return ""

def main():
    """主函數"""
    updater = DailyAirRealTimeUpdater()
    realtime_info = updater.update_realtime_info()
    
    # 打印部分數據示例
    if realtime_info:
        logger.info("實時資訊示例:")
        for i, info in enumerate(realtime_info[:3]):
            logger.info(f"航班 {i+1}: {info}")
    
    return realtime_info

if __name__ == "__main__":
    main() 