-- Minimal table creation script for testing
-- Based on the full schema in docs/infra/02-database-schema-setup.md

-- Country master table
CREATE TABLE IF NOT EXISTS public.insights_country (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(3) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- News data table
CREATE TABLE IF NOT EXISTS public.insights_countrynewsitem (
    id BIGSERIAL PRIMARY KEY,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id) ON DELETE CASCADE,
    source_name VARCHAR(128) NOT NULL,
    author VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    content TEXT,
    url VARCHAR(1000) NOT NULL UNIQUE,
    published_at TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type SMALLINT NOT NULL DEFAULT 0, -- 0=API, 1=Browser
    category VARCHAR(64),
    fake_news_score DECIMAL(3,2), -- fake news confidence
    raw_response JSONB
);

-- Weather data table
CREATE TABLE IF NOT EXISTS public.insights_countryweather (
    id BIGSERIAL PRIMARY KEY,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id) ON DELETE CASCADE,
    city_name VARCHAR(64) NOT NULL,
    coordinates_lat DECIMAL(8,6),
    coordinates_lon DECIMAL(9,6),
    weather_main VARCHAR(32) NOT NULL,
    weather_description VARCHAR(128) NOT NULL,
    temperature SMALLINT NOT NULL,
    feels_like SMALLINT NOT NULL,
    temp_min SMALLINT,
    temp_max SMALLINT,
    pressure SMALLINT,
    humidity SMALLINT NOT NULL,
    wind_speed DECIMAL(4,2),
    wind_direction SMALLINT,
    cloudiness SMALLINT,
    visibility INTEGER,
    published_at TIMESTAMP, -- Original data timestamp from API
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type SMALLINT NOT NULL DEFAULT 0, -- 0=API, 1=Browser
    sunrise_time TIMESTAMP, -- sys.sunrise converted
    sunset_time TIMESTAMP, -- sys.sunset converted
    raw_response JSONB
);

-- Collection history table
CREATE TABLE IF NOT EXISTS public.collection_history (
    id BIGSERIAL PRIMARY KEY,
    execution_id VARCHAR(64) NOT NULL,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id),
    api_type VARCHAR(32) NOT NULL,
    execution_date DATE NOT NULL,
    execution_timestamp TIMESTAMP NOT NULL,
    status VARCHAR(16) NOT NULL,
    records_collected INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_stored INTEGER DEFAULT 0,
    error_message TEXT,
    execution_duration_ms INTEGER,
    request_parameters JSONB,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample countries for testing
INSERT INTO public.insights_country (code, name) VALUES 
    ('USA', 'United States'),
    ('JPN', 'Japan'),
    ('GBR', 'United Kingdom')
ON CONFLICT (code) DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_news_country_collected ON public.insights_countrynewsitem(country_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_source_type ON public.insights_countrynewsitem(source_type, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_country_time ON public.insights_countryweather(country_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_source_type ON public.insights_countryweather(source_type, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_country_api_date ON public.collection_history(country_id, api_type, execution_date DESC);