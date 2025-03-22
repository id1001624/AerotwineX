/**
 * 航班API服務
 * 處理與後端API的通信
 */

// 基本API URL
const API_BASE_URL = 'http://localhost:5000/api';

/**
 * 獲取所有機場列表
 * @returns {Promise<Array>} 機場列表
 */
export async function getAirports() {
  try {
    // 調用後端API獲取機場列表
    const response = await fetch(`${API_BASE_URL}/airports`);
    if (!response.ok) {
      throw new Error(`獲取機場資料失敗: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('獲取機場資料時出錯:', error);
    return [];
  }
}

/**
 * 獲取所有航空公司列表
 * @returns {Promise<Array>} 航空公司列表
 */
export async function getAirlines() {
  try {
    // 調用後端API獲取航空公司列表
    const response = await fetch(`${API_BASE_URL}/airlines`);
    if (!response.ok) {
      throw new Error(`獲取航空公司資料失敗: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('獲取航空公司資料時出錯:', error);
    return [];
  }
}

/**
 * 根據出發地獲取可直飛的目的地列表
 * @param {string} departureAirport 出發機場代碼
 * @returns {Promise<Array>} 目的地機場列表
 */
export async function fetchDestinations(departureAirport) {
  try {
    if (!departureAirport) {
      throw new Error('缺少出發機場代碼');
    }
    
    const response = await fetch(`${API_BASE_URL}/destinations?departure=${departureAirport}`);
    if (!response.ok) {
      throw new Error(`獲取目的地機場失敗: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('獲取目的地機場時出錯:', error);
    throw error;
  }
}

/**
 * 根據出發地和目的地獲取可用航空公司
 * @param {string} departureAirport 出發機場代碼
 * @param {string} destinationAirport 目的地機場代碼
 * @returns {Promise<Array>} 航空公司列表
 */
export async function fetchAirlines(departureAirport, destinationAirport) {
  try {
    if (!departureAirport || !destinationAirport) {
      throw new Error('缺少出發機場或目的地機場代碼');
    }
    
    const response = await fetch(`${API_BASE_URL}/airlines?departure=${departureAirport}&destination=${destinationAirport}`);
    if (!response.ok) {
      throw new Error(`獲取航空公司失敗: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('獲取航空公司時出錯:', error);
    throw error;
  }
}

/**
 * 獲取可用的直飛航線
 * @returns {Promise<Array>} 航線列表，包含出發地和目的地資訊
 */
export async function getAvailableRoutes() {
  try {
    // 調用後端API獲取可用的直飛航線
    const response = await fetch(`${API_BASE_URL}/routes`);
    if (!response.ok) {
      throw new Error(`獲取航線資料失敗: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('獲取航線資料時出錯:', error);
    // 返回空數組而不是拋出錯誤，以避免中斷應用程序流程
    return [];
  }
}

/**
 * 搜尋航班
 * @param {Object} params 搜尋參數
 * @param {string} params.departure 出發機場代碼
 * @param {string} params.destination 目的地機場代碼
 * @param {string} params.date 日期 (YYYY-MM-DD)
 * @param {string} [params.airline] 航空公司ID (可選)
 * @returns {Promise<Array>} 航班列表
 */
export async function searchFlights(params) {
  try {
    // 參數驗證
    if (!params.departure || !params.destination || !params.date) {
      throw new Error('缺少必要的搜尋參數');
    }
    
    // 構建查詢參數
    const queryParams = new URLSearchParams({
      departure: params.departure,
      destination: params.destination,
      date: params.date
    });
    
    // 添加可選參數
    if (params.airline) {
      queryParams.append('airline', params.airline);
    }
    
    // 調用後端API搜尋航班
    const response = await fetch(`${API_BASE_URL}/flights?${queryParams}`);
    if (!response.ok) {
      throw new Error(`搜尋航班失敗: ${response.statusText}`);
    }
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('搜尋航班時出錯:', error);
    throw error;
  }
}