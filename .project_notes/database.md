```python
conn = pyodbc.connect(
    'DRIVER={SQL Server};'
    'SERVER=LAPTOP-QJNCMBU4;'
    'DATABASE=FlightBookingDB;'
    'UID=sa;'
    'PWD=Id1001624'
)
```
資料表:
```SQL
CREATE TABLE Airlines (
    airline_id VARCHAR(20) PRIMARY KEY,
    airline_name_zh NVARCHAR(50) NOT NULL,
    airline_name_en VARCHAR(50),
    logo_url VARCHAR(255),
    url VARCHAR(255),
    is_domestic BIT NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
);
CREATE TABLE Airports (
    airport_id VARCHAR(10) PRIMARY KEY,
    airport_name_zh NVARCHAR(100) NOT NULL,
    airport_name_en VARCHAR(100),
    city_zh NVARCHAR(50) NOT NULL,
    city_en VARCHAR(50),
    country VARCHAR(50) NOT NULL,
    timezone VARCHAR(50),
    contact_info VARCHAR(255),
    url VARCHAR(255),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
);
CREATE TABLE Flights (
    flight_number VARCHAR(20) NOT NULL,
    scheduled_departure DATETIME2 NOT NULL,
    airline_id VARCHAR(20) NOT NULL,
    departure_airport_code VARCHAR(10) NOT NULL,
    arrival_airport_code VARCHAR(10) NOT NULL,
    scheduled_arrival DATETIME2 NOT NULL,
    flight_status VARCHAR(20),
    aircraft_type VARCHAR(50),
    price DECIMAL(10, 2),
    booking_link VARCHAR(255),
    scrape_date DATETIME2 NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT pk_flights PRIMARY KEY (flight_number, scheduled_departure),
    CONSTRAINT fk_flights_airlines FOREIGN KEY (Airline_id) REFERENCES Airlines(airline_id),
    CONSTRAINT fk_flights_departure FOREIGN KEY (departure_airport_code) REFERENCES Airports(airport_id),
    CONSTRAINT fk_flights_arrival FOREIGN KEY (arrival_airport_code) REFERENCES Airports(airport_id),
    CONSTRAINT chk_flight_status CHECK (flight_status IN ('on_time', 'delayed', 'cancelled', 'departed', 'arrived'))
);
CREATE TABLE Users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    password VARBINARY(255),
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'basic', 'level1', 'level2')),
    line_id VARCHAR(50),  -- 新增欄位
    is_subscribed BIT,
    preferences NVARCHAR(MAX),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
);
CREATE TABLE Tickets (
    ticket_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    flight_number VARCHAR(20) NOT NULL,
    scheduled_departure DATETIME2 NOT NULL,
    booking_date DATETIME2 NOT NULL,
    status VARCHAR(20),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT fk_tickets_users FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_tickets_flights FOREIGN KEY (flight_number, scheduled_departure) REFERENCES flights(flight_number, scheduled_departure),
    CONSTRAINT chk_ticket_status CHECK (status IN ('confirmed', 'cancelled'))
);
CREATE TABLE Itineraries (
    itinerary_id VARCHAR(50) PRIMARY KEY,
    country VARCHAR(50) NOT NULL,
    title NVARCHAR(100) NOT NULL,
    description NVARCHAR(MAX),
    suggested_days INT,
    activities NVARCHAR(MAX),
    faq NVARCHAR(MAX),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
);
CREATE TABLE Price_History (
    flight_number VARCHAR(20) NOT NULL,
    scheduled_departure DATETIME2 NOT NULL,
    recorded_at DATETIME2 NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT pk_price_history PRIMARY KEY (flight_number, scheduled_departure, recorded_at),
    CONSTRAINT fk_price_history_flights FOREIGN KEY (flight_number, scheduled_departure) REFERENCES flights(flight_number, scheduled_departure)
);
CREATE TABLE Weather_Forecasts (
    airport_id VARCHAR(10) NOT NULL,
    forecast_date DATE NOT NULL,
    temperature DECIMAL(5, 2),
    precipitation DECIMAL(5, 2),
    wind_speed DECIMAL(5, 2),
    weather_condition VARCHAR(50),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT pk_weather_forecasts PRIMARY KEY (airport_id, forecast_date),
    CONSTRAINT fk_weather_forecasts_airports FOREIGN KEY (airport_id) REFERENCES Airports(airport_id)
);