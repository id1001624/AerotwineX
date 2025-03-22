import pyodbc
import traceback
import sys

# 將輸出重定向到文件
original_stdout = sys.stdout
log_file = open('database_check.log', 'w', encoding='utf-8')
sys.stdout = log_file

def get_db_connection():
    try:
        print("嘗試連接資料庫...")
        conn_str = (
            'DRIVER={SQL Server};'
            'SERVER=LAPTOP-QJNCMBU4;'
            'DATABASE=FlightBookingDB;'
            'UID=sa;'
            'PWD=Id1001624;'
            'Trusted_Connection=yes;'
        )
        print(f"連接字串: {conn_str}")
        conn = pyodbc.connect(conn_str)
        print("資料庫連接成功！")
        return conn
    except Exception as e:
        print(f"資料庫連接錯誤: {str(e)}")
        print("錯誤詳情:")
        traceback.print_exc(file=log_file)
        return None

def check_airlines():
    conn = get_db_connection()
    if not conn:
        print("無法檢查航空公司資料 - 連接失敗")
        return
    
    try:
        cursor = conn.cursor()
        
        # 檢查表是否存在
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Airlines'")
        if cursor.fetchone()[0] == 0:
            print("Airlines 表不存在！")
            return
            
        # 獲取航空公司數量
        cursor.execute("SELECT COUNT(*) FROM Airlines")
        count = cursor.fetchone()[0]
        print(f"\n航空公司數量: {count}")
        
        if count > 0:
            # 獲取航空公司列表
            print("\n航空公司資料:")
            cursor.execute("SELECT * FROM Airlines")
            columns = [column[0] for column in cursor.description]
            print(f"資料表欄位: {columns}")
            
            print("\n前5筆航空公司資料:")
            cursor.execute("SELECT TOP 5 * FROM Airlines")
            for row in cursor:
                print(row)
        else:
            print("Airlines 表中沒有資料！")
            
    except Exception as e:
        print(f"檢查航空公司時發生錯誤: {str(e)}")
        traceback.print_exc(file=log_file)
    finally:
        conn.close()
        print("資料庫連接已關閉")

def check_flights():
    conn = get_db_connection()
    if not conn:
        print("無法檢查航班資料 - 連接失敗")
        return
    
    try:
        cursor = conn.cursor()
        
        # 檢查表是否存在
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'Flights'")
        if cursor.fetchone()[0] == 0:
            print("Flights 表不存在！")
            return
        
        # 獲取航班數量
        cursor.execute("SELECT COUNT(*) FROM Flights")
        count = cursor.fetchone()[0]
        print(f"\n航班總數: {count}")
        
        if count > 0:
            # 獲取表結構
            print("\n航班表結構:")
            cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Flights'")
            for row in cursor:
                print(f"{row.COLUMN_NAME}: {row.DATA_TYPE}")
                
            # 獲取最近的航班
            print("\n最近5筆航班資料:")
            cursor.execute("SELECT TOP 5 * FROM Flights")
            columns = [column[0] for column in cursor.description]
            print(f"資料表欄位: {columns}")
            
            rows = cursor.fetchall()
            for row in rows:
                print(row)
                
            # 檢查特定路線
            print("\n檢查特定路線 (TPE -> HKG):")
            cursor.execute("SELECT COUNT(*) FROM Flights WHERE departure_airport_code = 'TPE' AND arrival_airport_code = 'HKG'")
            count = cursor.fetchone()[0]
            print(f"台北到香港的航班數量: {count}")
            
            if count > 0:
                print("路線航班詳情:")
                cursor.execute("SELECT * FROM Flights WHERE departure_airport_code = 'TPE' AND arrival_airport_code = 'HKG'")
                for row in cursor:
                    print(row)
        else:
            print("Flights 表中沒有資料！")
            
    except Exception as e:
        print(f"檢查航班時發生錯誤: {str(e)}")
        traceback.print_exc(file=log_file)
    finally:
        conn.close()
        print("資料庫連接已關閉")

if __name__ == "__main__":
    print("開始檢查資料庫...")
    print("Python ODBC 驅動程式列表:")
    print(pyodbc.drivers())
    
    check_airlines()
    check_flights()
    
    print("檢查完成！")
    
    # 恢復標準輸出
    sys.stdout = original_stdout
    log_file.close()
    print("資料庫檢查完成，結果已保存到 database_check.log")