"""
AerotwineX API 啟動程序
用於啟動和設定Flask API服務
"""
import os
import sys
from pathlib import Path

# 加入當前目錄到路徑，以便能夠導入模組
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# 導入Flask應用
from app import app

if __name__ == '__main__':
    # 檢查是否為生產環境
    is_production = os.environ.get('PRODUCTION', 'false').lower() == 'true'
    
    # 根據環境設定啟動方式
    if is_production:
        # 生產環境 - 使用gunicorn或其他WSGI服務器（需另外安裝）
        print("API服務正在生產模式下啟動...")
        # 這裡可以添加生產環境的配置
    else:
        # 開發環境 - 使用Flask內建的開發伺服器
        print("API服務正在開發模式下啟動...")
        app.run(debug=True, host='0.0.0.0', port=5000)