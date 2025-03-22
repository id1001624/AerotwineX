
```python

def scrape_airline_promotions(airline_code):
    """爬取航空公司官網上的真實促銷信息"""
    
    # 各航空公司促銷頁面配置
    promo_configs = {
        'CI': {  # 中華航空
            'url': 'https://www.china-airlines.com/tw/zh/promotion',
            'item_selector': '.promotion-item',
            'title_selector': '.promotion-title',
            'details_selector': '.promotion-content',
            'date_selector': '.promotion-date'
        },
        'BR': {  # 長榮航空
            'url': 'https://www.evaair.com/zh-tw/promotions/promotions/',
            'item_selector': '.promo-item',
            'title_selector': '.promo-title',
            'details_selector': '.promo-desc',
            'date_selector': '.promo-period'
        }
        # 其他航空公司配置...
    }
    
    if airline_code not in promo_configs:
        print(f"不支持的航空公司代碼: {airline_code}")
        return []
    
    config = promo_configs[airline_code]
    promotions = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(config['url'], headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            promo_items = soup.select(config['item_selector'])
            
            for item in promo_items:
                try:
                    title = item.select_one(config['title_selector']).text.strip()
                    details = item.select_one(config['details_selector']).text.strip()
                    
                    # 提取日期範圍
                    date_text = item.select_one(config['date_selector']).text.strip()
                    import re
                    date_match = re.search(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})[^\d]*(\d{4}[/-]\d{1,2}[/-]\d{1,2})', date_text)
                    
                    start_date = end_date = None
                    if date_match:
                        start_date = date_match.group(1)
                        end_date = date_match.group(2)
                    
                    # 提取促銷代碼
                    promo_code = None
                    code_match = re.search(r'代碼[：:]\s*([A-Z0-9]+)', details)
                    if code_match:
                        promo_code = code_match.group(1)
                    
                    promotions.append({
                        'airline': airline_code,
                        'title': title,
                        'details': details,
                        'start_date': start_date,
                        'end_date': end_date,
                        'promo_code': promo_code,
                        'source_url': config['url'],
                        'crawl_date': datetime.now().strftime('%Y-%m-%d')
                    })
                    
                except Exception as e:
                    print(f"解析促銷項目時出錯: {str(e)}")
            
        return promotions
        
    except Exception as e:
        print(f"爬取 {airline_code} 促銷信息時出錯: {str(e)}")
        return []
```

   ```python
   def get_random_headers():
       """生成隨機請求頭防止被反爬"""
       user_agents = [
           'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
           'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
       ]
       return {
           'User-Agent': random.choice(user_agents),
           'Accept': 'text/html,application/xhtml+xml,application/json',
           'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8'
       }
   ```

   ```python
   import redis
   import json
   import hashlib

   # 使用Redis實現API響應緩存
   redis_client = redis.Redis(host='localhost', port=6379, db=0)

   def cached_api_request(url, params, cache_ttl=3600):
       """帶緩存的API請求"""
       # 生成緩存鍵
       cache_key = hashlib.md5(f"{url}_{json.dumps(params, sort_keys=True)}".encode()).hexdigest()
       
       # 檢查緩存
       cached_response = redis_client.get(cache_key)
       if cached_response:
           return json.loads(cached_response)
       
       # 發送請求
       response = requests.get(url, params=params)
       data = response.json()
       
       # 存入緩存
       redis_client.setex(cache_key, cache_ttl, json.dumps(data))
       
       return data
   ```

### 六、需要補充的關鍵資料

1. **各航空公司網站爬蟲詳細規則**
   - 需要: XPath/CSS選擇器、表單參數格式、動態加載處理方法
   - 優先級: 最高

2. **數據存儲方案**
   - 需要: 資料庫設計、索引優化、查詢模式
   - 優先級: 高

3. **LINE Bot 伺服器部署資訊**
   - 需要: 伺服器配置、webhook設置、安全性考量
   - 優先級: 中

#  使用Python Celery  處理爬大資料

# 先用cursor 寫html生成UI再給cursor寫前端、Vue.js的Element UI 生成前端UI優化
