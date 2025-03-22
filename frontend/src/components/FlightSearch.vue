<template>
  <div class="flight-search">
    <div class="header">
      <h1>AerotwineX 航班查詢</h1>
      <p>簡單、快速地查詢您的航班</p>
    </div>
    
    <div class="search-container">
      <div class="search-form">
        <div class="form-group">
          <label>出發地</label>
          <select v-model="departureAirport" @change="filterDestinations">
            <option value="">請選擇出發機場</option>
            <option v-for="airport in taiwanAirports" :key="airport.code" :value="airport.code">
              {{ airport.city }} - {{ airport.name }} ({{ airport.code }})
            </option>
          </select>
        </div>
        
        <div class="form-group">
          <label>目的地機場</label>
          <select v-model="destinationAirport" :disabled="!departureAirport || isLoadingDestinations">
            <option value="">{{ isLoadingDestinations ? '載入中...' : '請選擇目的地機場' }}</option>
            <option v-for="airport in directFlightDestinations" :key="airport.code" :value="airport.code">
              {{ airport.city || '未知城市' }} - {{ airport.name }} ({{ airport.code }})
            </option>
          </select>
        </div>
        
        <div class="form-group">
          <label>日期</label>
          <input type="date" v-model="flightDate" :min="minDate" :max="maxDate">
        </div>
        
        <div class="form-group">
          <label>航空公司</label>
          <select v-model="selectedAirline" :disabled="!departureAirport || !destinationAirport || isLoadingAirlines">
            <option value="">{{ isLoadingAirlines ? '載入中...' : '全部航空公司' }}</option>
            <option v-for="airline in availableAirlines" :key="airline.id" :value="airline.id">
              {{ airline.name }}
            </option>
          </select>
        </div>
        
        <div class="action-buttons">
          <button class="search-button" @click="searchFlights" :disabled="!canSearch">
            搜尋航班
          </button>
          <button class="reset-button" @click="resetForm">
            重設
          </button>
        </div>
        
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
      </div>
    </div>
    
    <div class="search-results" v-if="searchComplete">
      <div v-if="isLoading" class="loading">
        <div class="loader"></div>
        <p>搜尋中，請稍候...</p>
      </div>
      
      <div v-else>
        <div class="results-header">
          <h2>搜尋結果</h2>
          <p v-if="flights.length === 0">沒有找到符合條件的航班</p>
          <p v-else>找到 {{ flights.length }} 個符合條件的航班</p>
        </div>
        
        <div v-if="flights.length > 0 && !selectedAirline" class="airline-summary">
          <div class="summary-header" @click="toggleAirlineSummary">
            <h3>航空公司航班分佈</h3>
            <div class="toggle-icon">{{ isAirlineSummaryExpanded ? '▲' : '▼' }}</div>
          </div>
          
          <div v-if="isAirlineSummaryExpanded" class="airline-list">
            <div v-for="airline in getAirlineSummary()" :key="airline.id" 
                 class="airline-item" 
                 @click="selectedAirline = airline.id">
              <div class="airline-info">
                <div class="airline-name">{{ airline.name || '未知航空公司' }}</div>
                <div class="airline-count">{{ airline.count }} 個航班</div>
              </div>
              <div class="airline-bar-container">
                <div class="airline-bar" :style="{ width: getPercentage(airline.count) }"></div>
              </div>
            </div>
          </div>
          
          <div class="filter-note" @click="toggleAirlineSummary">
            {{ isAirlineSummaryExpanded ? (getAirlineSummary().length > 0 ? "點擊航空公司可以篩選結果" : "無法獲取航空公司分佈數據") : "展開以篩選航空公司" }}
          </div>
        </div>
        
        <div class="flights-container" v-if="flights.length > 0">
          <div v-if="selectedAirline" class="selected-airline-info">
            <div class="airline-name">已選擇: {{ getAirlineName(selectedAirline) }}</div>
            <button class="clear-filter-button" @click="clearAirlineFilter">查看全部航班</button>
          </div>
          <flight-card 
            v-for="flight in flights" 
            :key="`${flight.flight_number}-${flight.scheduled_departure}`" 
            :flight="flight"
            :departureAirportName="getAirportName(flight.departure_airport_code)"
            :arrivalAirportName="getAirportName(flight.arrival_airport_code)"
            :airlineName="getAirlineName(flight.airline_id)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import FlightCard from './FlightCard.vue';
import axios from 'axios';

export default {
  name: 'FlightSearch',
  components: {
    FlightCard
  },
  data() {
    return {
      departureAirport: '',
      destinationAirport: '',
      flightDate: this.getTodayDate(),
      selectedAirline: '',
      airports: [],
      airlines: [],
      availableAirlines: [], // 特定航線可用的航空公司
      flights: [],
      isLoading: false,
      isLoadingDestinations: false,
      isLoadingAirlines: false,
      searchComplete: false,
      errorMessage: '',
      popularAirports: [],
      airportsByCountry: {},
      availableRoutes: [], // 存儲可用的直飛航線
      debugInfo: {
        apiCallsStatus: {},
        dataLoaded: false
      },
      taiwanAirports: [], // 台灣機場列表
      directFlightDestinations: [], // 直飛目的地列表
      airportData: [],
      airportNames: {
        'TPE': '台灣桃園國際機場',
        'TSA': '台北松山機場',
        'KHH': '高雄國際機場',
        'RMQ': '台中國際機場',
        'TTT': '台東機場',
        'KYD': '蘭嶼機場',
        'KNH': '金門機場',
        'MZG': '馬公機場',
        'HUN': '花蓮機場',
        'GNI': '綠島機場',
        'MFK': '馬祖北竿機場',
        'LZN': '馬祖南竿機場',
        'TNN': '台南機場',
        'CMJ': '七美機場',
        'WOT': '望安機場',
        'HND': '東京羽田機場',
        'NRT': '東京成田國際機場',
        'KIX': '大阪關西國際機場',
        'FUK': '福岡機場',
        'CTS': '札幌新千歲機場',
        'NGO': '名古屋中部國際機場',
        'OKA': '沖繩那霸機場',
        'HKG': '香港國際機場',
        'ICN': '首爾仁川國際機場',
        'GMP': '首爾金浦國際機場',
        'PVG': '上海浦東國際機場',
        'PEK': '北京首都國際機場',
        'SIN': '新加坡樟宜機場',
        'BKK': '曼谷素萬那普機場',
        'MNL': '馬尼拉國際機場'
      },
      cityInfo: {
        'TPE': '桃園',
        'TSA': '臺北',
        'KHH': '高雄',
        'RMQ': '台中',
        'TTT': '臺東',
        'KYD': '臺東',
        'KNH': '金門',
        'MZG': '澎湖',
        'HUN': '花蓮',
        'GNI': '臺東',
        'MFK': '連江',
        'LZN': '連江',
        'TNN': '台南',
        'CMJ': '澎湖',
        'WOT': '澎湖',
        'HND': '東京',
        'NRT': '東京',
        'KIX': '大阪',
        'FUK': '福岡',
        'CTS': '札幌',
        'NGO': '名古屋',
        'OKA': '沖繩',
        'HKG': '香港',
        'ICN': '首爾',
        'GMP': '首爾',
        'PVG': '上海',
        'PEK': '北京',
        'SIN': '新加坡',
        'BKK': '曼谷',
        'MNL': '馬尼拉'
      },
      countryInfo: {
        'TPE': 'TW',
        'TSA': 'TW',
        'KHH': 'TW',
        'RMQ': 'TW',
        'TTT': 'TW',
        'KYD': 'TW',
        'KNH': 'TW',
        'MZG': 'TW',
        'HUN': 'TW',
        'GNI': 'TW',
        'MFK': 'TW',
        'LZN': 'TW',
        'TNN': 'TW',
        'CMJ': 'TW',
        'WOT': 'TW',
        'HND': 'JP',
        'NRT': 'JP',
        'KIX': 'JP',
        'FUK': 'JP',
        'CTS': 'JP',
        'NGO': 'JP',
        'OKA': 'JP',
        'HKG': 'HK',
        'ICN': 'KR',
        'GMP': 'KR',
        'PVG': 'CN',
        'PEK': 'CN',
        'SIN': 'SG',
        'BKK': 'TH',
        'MNL': 'PH'
      },
      isAirlineSummaryExpanded: false
    };
  },
  computed: {
    minDate() {
      // 設定最小日期為今天
      return this.getTodayDate();
    },
    maxDate() {
      // 設定最大日期為一年後
      const date = new Date();
      date.setFullYear(date.getFullYear() + 1);
      return date.toISOString().split('T')[0];
    },
    canSearch() {
      // 不需要選擇航空公司也可以搜尋
      return this.departureAirport && this.destinationAirport && this.flightDate;
    }
  },
  
  watch: {
    // 當目的地機場變更時，獲取可用航空公司
    destinationAirport() {
      if (this.destinationAirport) {
        this.filterAirlines();
      }
    }
  },
  async mounted() {
    console.log('[DEBUG] FlightSearch組件掛載...');
    this.isLoading = true;
    
    try {
      // 加載台灣國內機場數據
      const airportsResponse = await axios.get('http://localhost:5000/api/airports');
      this.taiwanAirports = airportsResponse.data;
      console.log('[DEBUG] 台灣機場數據載入成功:', this.taiwanAirports);
      
      // 將台灣機場添加到機場清單中
      this.airports = [...this.taiwanAirports];
      
      // 加載所有航空公司數據
      const airlinesResponse = await axios.get('http://localhost:5000/api/airlines');
      this.airlines = airlinesResponse.data;
      console.log('[DEBUG] 航空公司數據載入成功:', this.airlines);
    } catch (error) {
      console.error('[ERROR] 初始數據加載失敗:', error);
      this.errorMessage = '載入初始數據時出錯，請重新整理頁面。';
      await this.loadPopularAirports(); // 如果API失敗，嘗試加載本地數據
    } finally {
      this.isLoading = false;
    }
  },
  methods: {
    // 修改後的方法：根據選擇的出發機場從API獲取可直飛的目的地
    async filterDestinations() {
      console.log('[DEBUG] 根據出發機場獲取目的地，當前出發機場:', this.departureAirport);
      this.directFlightDestinations = [];
      this.destinationAirport = '';
      this.selectedAirline = '';
      this.availableAirlines = [];
      
      if (!this.departureAirport) {
        return;
      }
      
      // 從API獲取可直飛的目的地
      this.isLoadingDestinations = true;
      try {
        const response = await axios.get(`http://localhost:5000/api/destinations?departure=${this.departureAirport}`);
        this.directFlightDestinations = response.data;
        console.log('[DEBUG] 從API獲取的目的地機場:', this.directFlightDestinations);
      } catch (error) {
        console.error('[ERROR] 獲取目的地機場失敗:', error);
        this.errorMessage = '無法獲取目的地機場資訊，請稍後再試。';
      } finally {
        this.isLoadingDestinations = false;
      }
    },
    
    // 新增方法：根據出發地和目的地獲取可用航空公司
    async filterAirlines() {
      console.log('[DEBUG] 獲取可用航空公司，出發地:', this.departureAirport, '目的地:', this.destinationAirport);
      this.availableAirlines = [];
      this.selectedAirline = '';
      
      if (!this.departureAirport || !this.destinationAirport) {
        return;
      }
      
      // 從API獲取該航線的可用航空公司
      this.isLoadingAirlines = true;
      try {
        const response = await axios.get(`http://localhost:5000/api/airlines?departure=${this.departureAirport}&destination=${this.destinationAirport}`);
        this.availableAirlines = response.data;
        console.log('[DEBUG] 從API獲取的航空公司:', this.availableAirlines);
      } catch (error) {
        console.error('[ERROR] 獲取航空公司失敗:', error);
        this.errorMessage = '無法獲取航空公司資訊，請稍後再試。';
      } finally {
        this.isLoadingAirlines = false;
      }
    },
    
    async fetchInitialData() {
      this.isLoading = true;
      
      // 1. 獲取機場詳細資料，包含城市資訊
      axios.get('http://localhost:5000/api/airports/details')
        .then(response => {
          this.airportData = response.data;
          this.organizeAirportsByCountry();
          console.log('機場詳細資料載入成功:', this.airportData.length);
          this.isLoading = false;
        })
        .catch(error => {
          console.error('無法獲取機場資料:', error);
          this.isLoading = false;
        });
        
      // 2. 獲取可用路線
      axios.get('http://localhost:5000/api/routes')
        .then(response => {
          this.availableRoutes = response.data;
          console.log('可用路線載入成功:', this.availableRoutes.length);
        })
        .catch(error => {
          console.error('無法獲取路線資料:', error);
        });
    },
    
    processAirportsData(airportsData) {
      // 只有在API請求失敗或沒有返回城市資訊時才使用這個備用資料
      // 預設的機場資訊（含城市和國家）
      const airportInfo = {
        // 台灣機場
        'TPE': { city_zh: '桃園', country: 'TW', country_name: '台灣' },
        'TSA': { city_zh: '臺北', country: 'TW', country_name: '台灣' },
        'KHH': { city_zh: '高雄', country: 'TW', country_name: '台灣' },
        'RMQ': { city_zh: '台中', country: 'TW', country_name: '台灣' },
        'TTT': { city_zh: '臺東', country: 'TW', country_name: '台灣' },
        'KYD': { city_zh: '臺東', country: 'TW', country_name: '台灣' },
        'KNH': { city_zh: '金門', country: 'TW', country_name: '台灣' },
        'MZG': { city_zh: '澎湖', country: 'TW', country_name: '台灣' },
        'HUN': { city_zh: '花蓮', country: 'TW', country_name: '台灣' },
        'GNI': { city_zh: '臺東', country: 'TW', country_name: '台灣' },
        'MFK': { city_zh: '連江', country: 'TW', country_name: '台灣' },
        'LZN': { city_zh: '連江', country: 'TW', country_name: '台灣' },
        'TNN': { city_zh: '台南', country: 'TW', country_name: '台灣' },
        'CMJ': { city_zh: '澎湖', country: 'TW', country_name: '台灣' },
        'WOT': { city_zh: '澎湖', country: 'TW', country_name: '台灣' },
        
        // 日本機場
        'HND': { city_zh: '東京', country: 'JP', country_name: '日本' },
        'NRT': { city_zh: '東京', country: 'JP', country_name: '日本' },
        'KIX': { city_zh: '大阪', country: 'JP', country_name: '日本' },
        'FUK': { city_zh: '福岡', country: 'JP', country_name: '日本' },
        'CTS': { city_zh: '札幌', country: 'JP', country_name: '日本' },
        'NGO': { city_zh: '名古屋', country: 'JP', country_name: '日本' },
        'OKA': { city_zh: '沖繩', country: 'JP', country_name: '日本' },
        
        // 亞洲其他熱門機場
        'HKG': { city_zh: '香港', country: 'HK', country_name: '香港' },
        'ICN': { city_zh: '首爾', country: 'KR', country_name: '韓國' },
        'GMP': { city_zh: '首爾', country: 'KR', country_name: '韓國' },
        'PVG': { city_zh: '上海', country: 'CN', country_name: '中國大陸' },
        'PEK': { city_zh: '北京', country: 'CN', country_name: '中國大陸' },
        'SIN': { city_zh: '新加坡', country: 'SG', country_name: '新加坡' },
        'BKK': { city_zh: '曼谷', country: 'TH', country_name: '泰國' },
        'MNL': { city_zh: '馬尼拉', country: 'PH', country_name: '菲律賓' }
      };
      
      // 檢查airportsData是否已經包含完整資訊
      if (Array.isArray(airportsData) && airportsData.length > 0 && 
          typeof airportsData[0] === 'object' && airportsData[0].city_zh) {
        // 如果已經有完整資訊，直接使用
        this.airports = airportsData;
        return;
      }
      
      // 擴展機場數據
      this.airports = airportsData.map(airport => {
        // 如果是簡單字串，轉換為物件
        let code = typeof airport === 'string' ? airport : airport.code;
        
        const info = airportInfo[code] || { 
          city_zh: '未知城市', 
          country: 'XX', 
          country_name: '未知國家' 
        };
        
        // 如果已經是物件且有city_zh屬性，使用現有的，否則使用默認值
        return typeof airport === 'string' ? {
          code,
          name: `${code} 機場`,
          city: info.city_zh,
          country: info.country,
          country_name: info.country_name
        } : {
          ...airport,
          city: airport.city_zh || info.city_zh,
          country: airport.country || info.country,
          country_name: airport.country_name || info.country_name
        };
      });
      
      // 將機場按國家分類
      this.organizeAirportsByCountry();
    },
    
    organizeAirportsByCountry() {
      // 清空現有資料
      this.airportsByCountry = {};
      
      // 按國家組織機場
      this.airportData.forEach(airport => {
        const countryCode = airport.country || 'XX';
        
        if (!this.airportsByCountry[countryCode]) {
          this.airportsByCountry[countryCode] = [];
        }
        
        this.airportsByCountry[countryCode].push({
          code: airport.code,
          name: airport.name,
          city: airport.city_zh || '未知城市',
          country: countryCode,
          country_name: airport.country_name || '未知國家'
        });
      });
      
      // 初始化台灣機場列表
      this.filterTaiwanAirports();
    },
    
    filterTaiwanAirports() {
      // 篩選出台灣的機場
      this.taiwanAirports = this.airportData.filter(airport => airport.country === 'TW');
    },
    
    async loadPopularAirports() {
      console.log('[DEBUG] 加載熱門機場數據...');
      try {
        // 嘗試讀取熱門機場配置文件
        const response = await fetch('/config/airlines_airports.json');
        if (!response.ok) {
          throw new Error('無法獲取熱門機場數據');
        }
        
        const data = await response.json();
        console.log('[DEBUG] 熱門機場配置數據:', data);
        
        // 處理機場數據
        if (data && data.airports && Array.isArray(data.airports)) {
          this.popularAirports = data.airports;
          console.log('[DEBUG] 已加載熱門機場數量:', this.popularAirports.length);
          
          // 機場數據處理：優先使用API數據，如果API無數據則使用熱門機場列表
          if (this.airports.length === 0 && this.popularAirports.length > 0) {
            console.log('[DEBUG] API沒有返回機場數據，使用熱門機場數據...');
            
            // 為熱門機場創建下拉選單所需的格式
            const airportNames = {
              // 台灣機場
              'TPE': '台灣桃園國際機場',
              'TSA': '台北松山機場',
              'KHH': '高雄國際機場',
              'RMQ': '台中國際機場',
              'TTT': '台東機場',
              'KYD': '蘭嶼機場',
              'KNH': '金門機場',
              'MZG': '馬公機場',
              'HUN': '花蓮機場',
              'GNI': '綠島機場',
              'MFK': '馬祖北竿機場',
              'LZN': '馬祖南竿機場',
              'TNN': '台南機場',
              'CMJ': '七美機場',
              'WOT': '望安機場',
              
              // 日本熱門機場
              'HND': '東京羽田機場',
              'NRT': '東京成田國際機場',
              'KIX': '大阪關西國際機場',
              'FUK': '福岡機場',
              'CTS': '札幌新千歲機場',
              'NGO': '名古屋中部國際機場',
              'OKA': '沖繩那霸機場',
              
              // 亞洲其他熱門機場
              'HKG': '香港國際機場',
              'ICN': '首爾仁川國際機場',
              'GMP': '首爾金浦國際機場',
              'PVG': '上海浦東國際機場',
              'PEK': '北京首都國際機場',
              'SIN': '新加坡樟宜機場',
              'BKK': '曼谷素萬那普機場',
              'MNL': '馬尼拉國際機場'
            };
            
            const cityInfo = {
              'TPE': '桃園',
              'TSA': '臺北',
              'KHH': '高雄',
              'RMQ': '台中',
              'TTT': '臺東',
              'KYD': '臺東',
              'KNH': '金門',
              'MZG': '澎湖',
              'HUN': '花蓮',
              'GNI': '臺東',
              'MFK': '連江',
              'LZN': '連江',
              'TNN': '台南',
              'CMJ': '澎湖',
              'WOT': '澎湖',
              
              'HND': '東京',
              'NRT': '東京',
              'KIX': '大阪',
              'FUK': '福岡',
              'CTS': '札幌',
              'NGO': '名古屋',
              'OKA': '沖繩',
              
              'HKG': '香港',
              'ICN': '首爾',
              'GMP': '首爾',
              'PVG': '上海',
              'PEK': '北京',
              'SIN': '新加坡',
              'BKK': '曼谷',
              'MNL': '馬尼拉'
            };
            
            const countryInfo = {
              'TPE': 'TW',
              'TSA': 'TW',
              'KHH': 'TW',
              'RMQ': 'TW',
              'TTT': 'TW',
              'KYD': 'TW',
              'KNH': 'TW',
              'MZG': 'TW',
              'HUN': 'TW',
              'GNI': 'TW',
              'MFK': 'TW',
              'LZN': 'TW',
              'TNN': 'TW',
              'CMJ': 'TW',
              'WOT': 'TW',
              
              'HND': 'JP',
              'NRT': 'JP',
              'KIX': 'JP',
              'FUK': 'JP',
              'CTS': 'JP',
              'NGO': 'JP',
              'OKA': 'JP',
              
              'HKG': 'HK',
              'ICN': 'KR',
              'GMP': 'KR',
              'PVG': 'CN',
              'PEK': 'CN',
              'SIN': 'SG',
              'BKK': 'TH',
              'MNL': 'PH'
            };
            
            // 將熱門機場代碼轉換為標準格式，含名稱、城市和國家
            this.airports = this.popularAirports.map(code => ({
              code,
              name: airportNames[code] || `${code} 機場`,
              city: cityInfo[code] || '未知城市',
              country: countryInfo[code] || 'XX'
            }));
            
            console.log('[DEBUG] 轉換後的機場數據:', this.airports);
            
            // 初始化台灣機場列表
            this.filterTaiwanAirports();
          }
        }
        
        // 處理航空公司數據
        if (data && data.airlines && Array.isArray(data.airlines) && this.airlines.length === 0) {
          console.log('[DEBUG] API沒有返回航空公司數據，使用配置文件數據...');
          
          // 為航空公司創建下拉選單所需的格式
          const airlineNames = {
            'CI': '中華航空',
            'BR': '長榮航空',
            'AE': '華信航空',
            'B7': '立榮航空',
            'JX': '星宇航空',
            'DA': '德安航空',
            'JL': '日本航空',
            'CX': '國泰航空',
            'OZ': '韓亞航空'
          };
          
          // 將航空公司代碼轉換為標準格式，含名稱
          this.airlines = data.airlines.map(id => ({
            id,
            name: airlineNames[id] || id
          }));
          
          console.log('[DEBUG] 轉換後的航空公司數據:', this.airlines);
        }
      } catch (error) {
        console.error('[ERROR] 無法載入熱門機場數據:', error);
      }
    },
    
    async searchFlights() {
      this.isLoading = true;
      this.searchComplete = true;
      this.errorMessage = '';
      this.isAirlineSummaryExpanded = false; // 默認收起航空公司分佈區域
      
      try {
        // 調用API搜尋航班
        const params = {
          departure: this.departureAirport,
          destination: this.destinationAirport,
          date: this.flightDate
        };
        
        // 只有選擇了航空公司時才加入航空公司參數
        if (this.selectedAirline) {
          params.airline = this.selectedAirline;
        }
        
        const response = await axios.get('http://localhost:5000/api/flights', { params });
        
        // 確保API返回的是有效資料
        if (Array.isArray(response.data)) {
          // 過濾並處理每個航班資料，確保必要欄位都存在
          this.flights = response.data.filter(flight => {
            return flight && 
                   flight.flight_number && 
                   flight.departure_airport_code && 
                   flight.arrival_airport_code &&
                   flight.scheduled_departure &&
                   flight.scheduled_arrival;
          }).map(flight => {
            // 確保所有必要的欄位都有有效值
            return {
              ...flight,
              flight_status: flight.flight_status || 'scheduled',
              airline_id: flight.airline_id || '',
              price: flight.price || 0,
              aircraft_type: flight.aircraft_type || '未知機型'
            };
          });
        } else {
          this.flights = [];
          throw new Error('API返回資料格式無效');
        }
        
        console.log('[DEBUG] 搜尋結果:', this.flights);
      } catch (error) {
        console.error('搜尋航班時出錯:', error);
        this.errorMessage = '搜尋過程中發生錯誤，請稍後再試';
        this.flights = [];
      } finally {
        this.isLoading = false;
      }
    },
    resetForm() {
      this.departureAirport = '';
      this.destinationAirport = '';
      this.flightDate = this.getTodayDate();
      this.selectedAirline = '';
      this.flights = [];
      this.searchComplete = false;
      this.directFlightDestinations = [];
      this.availableAirlines = [];
      this.errorMessage = '';
      this.isLoading = false;
      this.isLoadingDestinations = false;
      this.isLoadingAirlines = false;
      this.isAirlineSummaryExpanded = false;
    },
    getTodayDate() {
      return new Date().toISOString().split('T')[0];
    },
    getAirportName(code) {
      if (!code) return '未知機場';
      const airport = this.airports.find(a => a.code === code);
      return airport ? airport.name : (this.airportNames[code] || `${code} 機場`);
    },
    getAirlineName(id) {
      if (!id) return '未知航空公司';
      const airline = this.airlines.find(a => a.id === id);
      return airline ? airline.name : id;
    },
    formatDateTime(dateTimeStr) {
      const date = new Date(dateTimeStr);
      return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    },
    getAirlineSummary() {
      const summary = [];
      const airlineCounts = {};
      const airlineNames = {};

      // 獲取所有航班中出現的航空公司，確保航班有效且airline_id存在
      this.flights.forEach(flight => {
        if (!flight || !flight.airline_id) return;
        
        const airlineId = flight.airline_id;
        if (!airlineCounts[airlineId]) {
          airlineCounts[airlineId] = 0;
          // 保存航空公司名稱，確保使用有效的名稱
          airlineNames[airlineId] = flight.airline_name || this.getAirlineName(airlineId) || `航空公司 ${airlineId}`;
        }
        airlineCounts[airlineId]++;
      });

      // 將統計數據轉換為數組
      Object.keys(airlineCounts).forEach(id => {
        if (id && airlineNames[id]) {
          summary.push({
            id,
            name: airlineNames[id],
            count: airlineCounts[id]
          });
        }
      });

      // 按照航班數量降序排序
      return summary.sort((a, b) => b.count - a.count);
    },
    
    // 計算航班數量的百分比
    getPercentage(count) {
      const total = this.flights.length;
      if (!total || !count) return '0%';
      return `${Math.round((count / total) * 100)}%`;
    },
    clearAirlineFilter() {
      this.selectedAirline = '';
      this.searchFlights();
    },
    toggleAirlineSummary() {
      this.isAirlineSummaryExpanded = !this.isAirlineSummaryExpanded;
    }
  }
};
</script>

<style scoped>
.flight-search {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  color: #333;
  font-family: 'Arial', sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 2rem;
}

.header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  font-weight: 300;
  letter-spacing: 1px;
}

.header p {
  font-size: 1.2rem;
  color: #666;
}

.search-container {
  background-color: #f8f8f8;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  margin-bottom: 2rem;
}

.search-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

select, input {
  padding: 0.8rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  background-color: white;
  transition: border-color 0.3s;
}

select:focus, input:focus {
  border-color: #333;
  outline: none;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  grid-column: 1 / -1;
}

button {
  padding: 0.8rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.3s, transform 0.1s;
}

button:hover {
  transform: translateY(-2px);
}

.search-button {
  background-color: #333;
  color: white;
  flex: 2;
}

.search-button:hover {
  background-color: #222;
}

.search-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
  transform: none;
}

.reset-button {
  background-color: #e6e6e6;
  color: #333;
  flex: 1;
}

.reset-button:hover {
  background-color: #d9d9d9;
}

.error-message {
  color: #d32f2f;
  background-color: #ffebee;
  padding: 0.8rem;
  border-radius: 4px;
  margin-top: 1rem;
  text-align: center;
  font-weight: 500;
  grid-column: 1 / -1;
}

.search-results {
  margin-top: 2rem;
}

.results-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.results-header h2 {
  font-size: 1.8rem;
  font-weight: 300;
  margin-bottom: 0.5rem;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem 0;
}

.loader {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #333;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.flights-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.airline-summary {
  margin-bottom: 2rem;
  background-color: #f8f8f8;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  margin-bottom: 1rem;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.summary-header:hover {
  background-color: rgba(0, 0, 0, 0.03);
}

.summary-header h3 {
  font-size: 1.2rem;
  font-weight: 500;
  margin: 0;
  color: #333;
}

.toggle-icon {
  font-size: 1rem;
  color: #666;
  transition: transform 0.3s;
}

.airline-list {
  list-style: none;
  padding: 0;
  margin-top: 1rem;
  max-height: 300px;
  overflow-y: auto;
  animation: fadeIn 0.3s ease;
}

.airline-item {
  margin-bottom: 0.8rem;
  padding: 0.8rem;
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.2s;
}

.airline-item:hover {
  background-color: #f3f9ff;
  transform: translateY(-2px);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.08);
}

.airline-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.airline-name {
  font-weight: 500;
}

.airline-count {
  color: #666;
}

.airline-bar-container {
  width: 100%;
  background-color: #eee;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
}

.airline-bar {
  height: 100%;
  background-color: #4CAF50;
  border-radius: 3px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.filter-note {
  margin-top: 1rem;
  font-size: 0.9rem;
  color: #666;
  text-align: center;
  font-style: italic;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.filter-note:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #333;
}

.selected-airline-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.8rem;
  background-color: #f8f8f8;
  border-radius: 4px;
}

.clear-filter-button {
  background-color: #333;
  color: white;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.clear-filter-button:hover {
  background-color: #222;
}

@media (max-width: 768px) {
  .search-form {
    grid-template-columns: 1fr;
  }
  
  .flights-container {
    grid-template-columns: 1fr;
  }
  
  .flight-search {
    padding: 1rem;
  }
}
</style>