<template>
  <div class="flight-card">
    <div class="flight-header">
      <div class="airline">
        <span class="airline-name">{{ airlineName }}</span>
        <span class="flight-number">{{ flight.flight_number }}</span>
      </div>
      <div class="flight-status" :class="statusClass">
        {{ getStatusText(flight.flight_status) }}
      </div>
    </div>
    
    <div class="flight-content">
      <div class="flight-route">
        <div class="departure">
          <div class="time">{{ formatTime(flight.scheduled_departure) }}</div>
          <div class="airport-code">{{ flight.departure_airport_code }}</div>
          <div class="airport-name">{{ departureAirportName }}</div>
          <div class="date">{{ formatDate(flight.scheduled_departure) }}</div>
        </div>
        
        <div class="flight-details">
          <div class="duration">{{ calculateDuration(flight.scheduled_departure, flight.scheduled_arrival) }}</div>
          <div class="direction-line">
            <div class="line"></div>
            <div class="plane-icon">✈</div>
          </div>
          <div class="aircraft">{{ flight.aircraft_type }}</div>
        </div>
        
        <div class="arrival">
          <div class="time">{{ formatTime(flight.scheduled_arrival) }}</div>
          <div class="airport-code">{{ flight.arrival_airport_code }}</div>
          <div class="airport-name">{{ arrivalAirportName }}</div>
          <div class="date">{{ formatDate(flight.scheduled_arrival) }}</div>
        </div>
      </div>
      
      <div class="flight-details-bottom">
        <div class="price">
          <span class="price-label">票價</span>
          <span class="price-amount">NT${{ formatPrice(flight.price) }}</span>
        </div>
        
        <a :href="flight.booking_link" class="booking-button">
          預訂此航班
        </a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FlightCard',
  props: {
    flight: {
      type: Object,
      required: true,
      default: () => ({
        flight_number: '',
        flight_status: 'scheduled',
        scheduled_departure: new Date().toISOString(),
        scheduled_arrival: new Date().toISOString(),
        departure_airport_code: '',
        arrival_airport_code: '',
        aircraft_type: '',
        price: 0,
        booking_link: '#'
      })
    },
    departureAirportName: {
      type: String,
      default: '未知機場'
    },
    arrivalAirportName: {
      type: String,
      default: '未知機場'
    },
    airlineName: {
      type: String,
      default: '未知航空公司'
    }
  },
  computed: {
    statusClass() {
      const status = (this.flight.flight_status || 'scheduled').toLowerCase();
      return {
        'status-scheduled': status === 'scheduled',
        'status-active': status === 'active',
        'status-landed': status === 'landed',
        'status-delayed': status === 'delayed',
        'status-cancelled': status === 'cancelled'
      };
    }
  },
  methods: {
    formatTime(dateTimeStr) {
      if (!dateTimeStr) return '--:--';
      try {
        const date = new Date(dateTimeStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } catch (e) {
        console.error('無效的日期格式:', dateTimeStr);
        return '--:--';
      }
    },
    formatDate(dateTimeStr) {
      if (!dateTimeStr) return '--/--';
      try {
        const date = new Date(dateTimeStr);
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
      } catch (e) {
        console.error('無效的日期格式:', dateTimeStr);
        return '--/--';
      }
    },
    calculateDuration(departureTimeStr, arrivalTimeStr) {
      if (!departureTimeStr || !arrivalTimeStr) return '未知時間';
      try {
        const departureTime = new Date(departureTimeStr);
        const arrivalTime = new Date(arrivalTimeStr);
        const durationMs = arrivalTime - departureTime;
        
        if (isNaN(durationMs) || durationMs < 0) return '未知時間';
        
        const hours = Math.floor(durationMs / (1000 * 60 * 60));
        const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
        
        return `${hours}小時 ${minutes}分鐘`;
      } catch (e) {
        console.error('計算航班時間錯誤:', e);
        return '未知時間';
      }
    },
    getStatusText(status) {
      if (!status) return '未知狀態';
      
      const statusMap = {
        'scheduled': '已排程',
        'active': '飛行中',
        'landed': '已降落',
        'delayed': '延誤',
        'cancelled': '已取消'
      };
      
      return statusMap[status.toLowerCase()] || status;
    },
    formatPrice(price) {
      if (price === undefined || price === null) return '0';
      try {
        return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
      } catch (e) {
        return '0';
      }
    }
  }
};
</script>

<style scoped>
.flight-card {
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.flight-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.flight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #f8f8f8;
  border-bottom: 1px solid #eee;
}

.airline {
  display: flex;
  flex-direction: column;
}

.airline-name {
  font-weight: bold;
  font-size: 1rem;
}

.flight-number {
  color: #777;
  font-size: 0.9rem;
}

.flight-status {
  padding: 0.3rem 0.8rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-scheduled {
  background-color: #e3f2fd;
  color: #1976d2;
}

.status-active {
  background-color: #e8f5e9;
  color: #388e3c;
}

.status-landed {
  background-color: #e8f5e9;
  color: #388e3c;
}

.status-delayed {
  background-color: #fff8e1;
  color: #ffa000;
}

.status-cancelled {
  background-color: #ffebee;
  color: #d32f2f;
}

.flight-content {
  padding: 1rem;
}

.flight-route {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.departure, .arrival {
  text-align: center;
  flex: 1;
}

.time {
  font-size: 1.5rem;
  font-weight: 300;
  margin-bottom: 0.2rem;
}

.airport-code {
  font-weight: bold;
  font-size: 1.2rem;
  margin-bottom: 0.2rem;
}

.airport-name {
  font-size: 0.85rem;
  color: #555;
  margin-bottom: 0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.date {
  font-size: 0.8rem;
  color: #777;
}

.flight-details {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  flex: 2;
}

.duration {
  text-align: center;
  font-size: 0.85rem;
  color: #555;
  margin-bottom: 0.5rem;
}

.direction-line {
  position: relative;
  width: 80%;
  margin: 0.5rem 0;
}

.line {
  height: 1px;
  background-color: #ddd;
  width: 100%;
}

.plane-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: white;
  padding: 0.2rem;
  font-size: 1rem;
  color: #555;
}

.aircraft {
  font-size: 0.75rem;
  color: #777;
  margin-top: 0.5rem;
}

.flight-details-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.price {
  display: flex;
  flex-direction: column;
}

.price-label {
  font-size: 0.8rem;
  color: #777;
}

.price-amount {
  font-size: 1.3rem;
  font-weight: bold;
}

.booking-button {
  background-color: #333;
  color: white;
  padding: 0.7rem 1.2rem;
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.9rem;
  transition: background-color 0.3s;
}

.booking-button:hover {
  background-color: #222;
}

@media (max-width: 768px) {
  .flight-route {
    flex-direction: column;
    gap: 1rem;
  }
  
  .departure, .arrival {
    display: flex;
    justify-content: space-between;
    align-items: center;
    text-align: left;
  }
  
  .departure > div, .arrival > div {
    margin-right: 1rem;
  }
  
  .flight-details {
    flex-direction: row;
    justify-content: space-between;
  }
  
  .direction-line {
    transform: rotate(90deg);
    width: 40%;
  }
}
</style>