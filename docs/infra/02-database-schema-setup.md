# 02. データベーススキーマ作成手順書

## 概要

RDS PostgreSQL インスタンスに国際データ収集システム用のテーブルスキーマを作成します。
実際の API レスポンス構造に対応した詳細なテーブル設計を実装します。

## 前提条件

- RDS PostgreSQL インスタンスが作成済み
- PostgreSQL クライアント（psql）がインストール済み
- データベースへの接続が確認済み

## 接続準備

### Step 1: データベースへの接続

CloudShell(AmazonLinux)から実行する

```bash
# PostgreSQLクライアントのインストール
# dnfを使用
sudo dnf install -y postgresql15

# または
sudo dnf install -y postgresql

# インストール確認
psql --version

```

```bash
# 環境変数設定
export RDS_WRITER_ENDPOINT="whisperplanet-international-data-aurora-dev.cluster-xxxxxx.us-west-2.rds.amazonaws.com"
export RDS_READER_ENDPOINT="whisperplanet-international-data-aurora-dev.cluster-ro-xxxxxx.us-west-2.rds.amazonaws.com"
export RDS_DATABASE="whisperplanet-international-data-aurora-dev"
export RDS_USERNAME="postgres"
export RDS_PORT="5432"

# データベース接続
psql -h $RDS_ENDPOINT -U $RDS_USERNAME -d $RDS_DATABASE -p $RDS_PORT
```

### Step 2: 接続確認

```sql
-- 現在の接続情報確認
\conninfo

-- データベース一覧確認
\l

-- 現在のスキーマ確認
\dn
```

## テーブル作成

### Step 3: 国マスタテーブルの作成

```sql
-- ==============================================
-- 1. 国マスタテーブル
-- ==============================================
CREATE TABLE IF NOT EXISTS public.insights_country (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(3) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_local VARCHAR(100),
    capital_city VARCHAR(64),
    timezone VARCHAR(32),
    coordinates JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- テーブル作成確認
\d public.insights_country
```

**テーブル設計説明**:

- `id`: 自動増分の主キー
- `code`: ISO 3166-1 alpha-3 国コード (JPN, USA, CHN)
- `name`: 英語国名
- `name_local`: 現地語国名
- `capital_city`: 首都名
- `timezone`: タイムゾーン (Asia/Tokyo 等)
- `coordinates`: 座標情報 (JSONB 形式)

### Step 4: API リクエスト設定テーブルの作成

```sql
-- ==============================================
-- 2. APIリクエスト設定テーブル（実パラメータ対応）
-- ==============================================
CREATE TABLE IF NOT EXISTS public.config_api_settings (
    id BIGSERIAL PRIMARY KEY,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id) ON DELETE CASCADE,
    api_type VARCHAR(32) NOT NULL,              -- 'news_api', 'weather_api', 'worldbank', 'imf', 'google_trends'

    -- NewsAPI設定
    news_country_code VARCHAR(2),               -- "us", "jp" (NewsAPI country parameter)
    news_page_size INTEGER DEFAULT 10,         -- pageSize parameter
    news_category VARCHAR(32),                  -- category parameter

    -- OpenWeatherMap設定
    weather_city_query VARCHAR(128),            -- "Tokyo,JP" (q parameter)
    weather_units VARCHAR(16) DEFAULT 'metric', -- units parameter
    weather_lang VARCHAR(8) DEFAULT 'en',      -- lang parameter

    -- World Bank設定
    wb_country_code VARCHAR(3),                 -- "JP" (country code)
    wb_indicators JSONB,                        -- ["NY.GDP.PCAP.CD"] (indicator list)
    wb_date_range VARCHAR(32),                  -- "2020:2023" (date parameter)
    wb_per_page INTEGER DEFAULT 10,            -- per_page parameter

    -- IMF設定
    imf_country_code VARCHAR(3),                -- "JPN" (country code)
    imf_indicators JSONB,                       -- ["NGDP_RPCH"] (indicator list)

    -- Google Trends設定
    trends_geo VARCHAR(8),                      -- "JP" (geo parameter)
    trends_timeframe VARCHAR(32) DEFAULT 'today 3-m', -- timeframe parameter
    trends_category INTEGER DEFAULT 0,         -- cat parameter
    trends_keywords JSONB,                      -- ["経済", "政治", "コロナ"] (keywords)
    trends_hl VARCHAR(8) DEFAULT 'ja-JP',      -- hl parameter
    trends_tz INTEGER DEFAULT 540,             -- tz parameter

    -- 共通設定
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1,
    secret_name VARCHAR(128),                   -- Secrets Manager reference

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(country_id, api_type)
);

-- テーブル作成確認
\d public.config_api_settings
```

**テーブル設計説明**:

- 各 API（NewsAPI、OpenWeatherMap 等）の実際のパラメータに対応
- JSONB 型で配列データ（indicators、keywords）を効率的に保存
- 国別・API 別の設定を一元管理

### Step 5: ニュースデータテーブルの作成

```sql
-- ==============================================
-- 3. ニュースデータテーブル（NewsAPI実データ対応）
-- ==============================================
CREATE TABLE IF NOT EXISTS public.insights_countrynewsitem (
    id BIGSERIAL PRIMARY KEY,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id) ON DELETE CASCADE,

    -- NewsAPI source object完全対応
    source_id VARCHAR(128),                     -- source.id (nullable)
    source_name VARCHAR(128) NOT NULL,          -- source.name

    -- Article content（実データ長に対応）
    author VARCHAR(255),                        -- author (nullable)
    title VARCHAR(500) NOT NULL,                -- title (長いタイトル対応)
    description TEXT,                           -- description
    content TEXT,                               -- content (truncated with [+XX chars])
    url VARCHAR(1000) NOT NULL,                 -- url (長いURL対応)
    url_to_image VARCHAR(1000),                 -- urlToImage

    -- Timestamps（ISO 8601対応）
    published_at TIMESTAMP,                     -- publishedAt ('2025-09-26T06:29:18Z')
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 分析メタデータ
    category VARCHAR(64),                       -- 自動分類結果
    tone VARCHAR(16),                           -- sentiment analysis
    fake_news_score DECIMAL(3,2),              -- 0.00-1.00
    importance_score DECIMAL(3,2),              -- 0.00-1.00

    -- 検索最適化
    search_vector tsvector,                     -- 全文検索用

    -- Raw data preservation
    raw_response JSONB                          -- 完全なAPIレスポンス保存
);

-- テーブル作成確認
\d public.insights_countrynewsitem
```

**テーブル設計説明**:

- NewsAPI の実際のレスポンス構造に完全対応
- 長い URL・タイトルに対応した十分な文字数
- 全文検索用の tsvector カラム
- 生データを JSONB で保存してデバッグ・拡張に対応

### Step 6: 天気データテーブルの作成

```sql
-- ==============================================
-- 4. 天気データテーブル（OpenWeatherMap実データ対応）
-- ==============================================
CREATE TABLE IF NOT EXISTS public.insights_countryweather (
    id BIGSERIAL PRIMARY KEY,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id) ON DELETE CASCADE,

    -- Location data（実レスポンス対応）
    city_name VARCHAR(64) NOT NULL,             -- name: "Tokyo"
    city_id INTEGER,                            -- id: 1850144
    coordinates_lat DECIMAL(8,6),               -- coord.lat: 35.6895
    coordinates_lon DECIMAL(9,6),               -- coord.lon: 139.6917
    timezone_offset INTEGER,                    -- timezone: 32400

    -- Weather condition（weather配列の最初の要素）
    weather_id INTEGER,                         -- weather[0].id: 803
    weather_main VARCHAR(32) NOT NULL,          -- weather[0].main: "Clouds"
    weather_description VARCHAR(128) NOT NULL,  -- weather[0].description: "cloudy"
    weather_icon VARCHAR(8),                    -- weather[0].icon: "04d"

    -- Temperature data（精度保持のため×10）
    temperature SMALLINT NOT NULL,              -- main.temp: 26.3 → 263
    feels_like SMALLINT NOT NULL,               -- main.feels_like: 26.3 → 263
    temp_min SMALLINT,                          -- main.temp_min: 26.3 → 263
    temp_max SMALLINT,                          -- main.temp_max: 26.3 → 263

    -- Atmospheric data
    pressure SMALLINT,                          -- main.pressure: 1015
    humidity SMALLINT NOT NULL,                 -- main.humidity: 47
    sea_level_pressure SMALLINT,                -- main.sea_level: 1015
    ground_level_pressure SMALLINT,             -- main.grnd_level: 1014

    -- Visibility and clouds
    visibility INTEGER,                         -- visibility: 10000
    cloudiness SMALLINT,                        -- clouds.all: 65

    -- Wind data
    wind_speed DECIMAL(4,2),                    -- wind.speed: 4.81
    wind_direction SMALLINT,                    -- wind.deg: 125
    wind_gust DECIMAL(4,2),                     -- wind.gust: 3.47

    -- Sun data（Unix timestamp変換）
    sunrise_time TIMESTAMP,                     -- sys.sunrise: 1758918760 → timestamp
    sunset_time TIMESTAMP,                      -- sys.sunset: 1758961917 → timestamp

    -- Collection metadata
    api_timestamp TIMESTAMP,                    -- dt: 1758948965 → timestamp
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Raw data preservation
    raw_response JSONB                          -- 完全なAPIレスポンス保存
);

-- テーブル作成確認
\d public.insights_countryweather
```

**テーブル設計説明**:

- OpenWeatherMap の全フィールドに対応
- 温度データは精度保持のため ×10 で保存（26.3℃ → 263）
- Unix timestamp を TIMESTAMP 型に変換して保存
- 気象データの詳細な分析に対応

### Step 7: 経済データテーブルの作成

```sql
-- ==============================================
-- 5. 経済データテーブル（World Bank + IMF実データ対応）
-- ==============================================
CREATE TABLE IF NOT EXISTS public.insights_countryeconomic (
    id BIGSERIAL PRIMARY KEY,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id) ON DELETE CASCADE,

    -- Indicator identification
    indicator_code VARCHAR(32) NOT NULL,        -- "NY.GDP.PCAP.CD", "NGDP_RPCH"
    indicator_name VARCHAR(256),                -- "GDP per capita (current US$)"

    -- Time dimension
    year SMALLINT NOT NULL,                     -- 2023, 2024, etc.
    quarter SMALLINT,                           -- 1-4 (if applicable)
    month SMALLINT,                             -- 1-12 (if applicable)

    -- Value data
    value DECIMAL(15,4),                        -- 33836.1756271617, 3.2, etc.
    unit VARCHAR(64),                           -- "current US$", "percent", etc.

    -- Source information
    data_source VARCHAR(32) NOT NULL,           -- 'worldbank', 'imf'
    source_id VARCHAR(16),                      -- World Bank: "2", IMF: specific ID

    -- World Bank specific fields
    wb_countryiso3code VARCHAR(3),              -- "JPN"
    wb_obs_status VARCHAR(16),                  -- observation status
    wb_decimal SMALLINT,                        -- decimal places: 1

    -- Collection metadata
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_by_source TIMESTAMP,           -- "lastupdated": "2025-07-01"

    -- Raw data preservation
    raw_response JSONB
);

-- テーブル作成確認
\d public.insights_countryeconomic
```

### Step 8: トレンドデータテーブルの作成

```sql
-- ==============================================
-- 6. トレンドデータテーブル（Google Trends実データ対応）
-- ==============================================
CREATE TABLE IF NOT EXISTS public.insights_countrytrends (
    id BIGSERIAL PRIMARY KEY,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id) ON DELETE CASCADE,

    -- Keyword and time
    keyword VARCHAR(64) NOT NULL,               -- "経済", "政治", "コロナ"
    date DATE NOT NULL,                         -- 2025-06-27, 2025-06-28, etc.

    -- Interest data
    interest_value SMALLINT,                    -- 26, 17, 19, etc. (0-100 scale)
    is_partial BOOLEAN DEFAULT false,           -- isPartial column

    -- Geographic data (for regional breakdown)
    region VARCHAR(64),                         -- "三重県", "京都府", etc.
    geo_name VARCHAR(64),                       -- geoName from regional data

    -- Data type specification
    data_type VARCHAR(16) NOT NULL,             -- 'time_series', 'regional'
    timeframe VARCHAR(32),                      -- 'today 3-m'

    -- Collection metadata
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Raw data preservation
    raw_response JSONB
);

-- テーブル作成確認
\d public.insights_countrytrends
```

### Step 9: データ収集履歴テーブルの作成

```sql
-- ==============================================
-- 7. データ収集履歴テーブル（統合監視）
-- ==============================================
CREATE TABLE IF NOT EXISTS public.collection_history (
    id BIGSERIAL PRIMARY KEY,
    execution_id VARCHAR(64) NOT NULL,
    country_id BIGINT NOT NULL REFERENCES public.insights_country(id),
    api_type VARCHAR(32) NOT NULL,

    -- Execution info
    execution_date DATE NOT NULL,
    execution_timestamp TIMESTAMP NOT NULL,

    -- Results
    status VARCHAR(16) NOT NULL,                -- 'success', 'failed', 'partial'
    records_collected INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_stored INTEGER DEFAULT 0,

    -- Error info
    error_message TEXT,
    error_code VARCHAR(32),
    retry_count INTEGER DEFAULT 0,

    -- Performance metrics
    execution_duration_ms INTEGER,
    api_response_time_ms INTEGER,
    data_size_bytes INTEGER,

    -- Request details
    request_parameters JSONB,                   -- 実際に使用されたパラメータ
    response_metadata JSONB,                    -- APIレスポンスのメタデータ

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- テーブル作成確認
\d public.collection_history
```

## インデックス作成

### Step 10: パフォーマンス最適化インデックスの作成

```sql
-- ==============================================
-- Web UI最適化インデックス
-- ==============================================

-- 国マスタ用
CREATE INDEX IF NOT EXISTS idx_country_code ON public.insights_country(code);

-- API設定用
CREATE INDEX IF NOT EXISTS idx_api_settings_country_type ON public.config_api_settings(country_id, api_type);
CREATE INDEX IF NOT EXISTS idx_api_settings_enabled ON public.config_api_settings(enabled, priority);

-- ニュースデータ用（Web UI頻出クエリ）
CREATE INDEX IF NOT EXISTS idx_news_country_collected ON public.insights_countrynewsitem(country_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_country_published ON public.insights_countrynewsitem(country_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_source_time ON public.insights_countrynewsitem(source_name, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_date_range ON public.insights_countrynewsitem(country_id, DATE(published_at));

-- 天気データ用（時系列表示最適化）
CREATE INDEX IF NOT EXISTS idx_weather_country_time ON public.insights_countryweather(country_id, api_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_weather_city_collected ON public.insights_countryweather(city_name, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_date_range ON public.insights_countryweather(country_id, DATE(api_timestamp));

-- 経済データ用（年次・指標別検索）
CREATE INDEX IF NOT EXISTS idx_economic_country_indicator_year ON public.insights_countryeconomic(country_id, indicator_code, year DESC);
CREATE INDEX IF NOT EXISTS idx_economic_source_time ON public.insights_countryeconomic(data_source, collected_at DESC);

-- トレンドデータ用（キーワード・日付検索）
CREATE INDEX IF NOT EXISTS idx_trends_country_keyword_date ON public.insights_countrytrends(country_id, keyword, date DESC);
CREATE INDEX IF NOT EXISTS idx_trends_date_range ON public.insights_countrytrends(country_id, date DESC);

-- 収集履歴用（監視・レポート）
CREATE INDEX IF NOT EXISTS idx_history_country_api_date ON public.collection_history(country_id, api_type, execution_date DESC);
CREATE INDEX IF NOT EXISTS idx_history_status_time ON public.collection_history(status, execution_timestamp DESC);

-- 全文検索インデックス（ニュース検索）
CREATE INDEX IF NOT EXISTS idx_news_fulltext ON public.insights_countrynewsitem
USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- 複合インデックス（Web UI頻出パターン）
CREATE INDEX IF NOT EXISTS idx_news_country_date_category ON public.insights_countrynewsitem(country_id, DATE(published_at), category);
CREATE INDEX IF NOT EXISTS idx_weather_country_date_main ON public.insights_countryweather(country_id, DATE(api_timestamp), weather_main);
```

### Step 11: インデックス作成確認

```sql
-- インデックス一覧確認
\di

-- 特定テーブルのインデックス確認
\d public.insights_countrynewsitem
```

## 初期データ投入

### Step 12: 国マスタデータの投入

```sql
-- 日本のデータ投入
INSERT INTO public.insights_country (code, name, name_local, capital_city, timezone, coordinates)
VALUES (
    'JPN',
    'Japan',
    '日本',
    'Tokyo',
    'Asia/Tokyo',
    '{"lat": 35.6762, "lon": 139.6503}'::jsonb
);

-- アメリカのデータ投入
INSERT INTO public.insights_country (code, name, name_local, capital_city, timezone, coordinates)
VALUES (
    'USA',
    'United States',
    'United States',
    'Washington',
    'America/New_York',
    '{"lat": 38.9072, "lon": -77.0369}'::jsonb
);

-- 中国のデータ投入
INSERT INTO public.insights_country (code, name, name_local, capital_city, timezone, coordinates)
VALUES (
    'CHN',
    'China',
    '中国',
    'Beijing',
    'Asia/Shanghai',
    '{"lat": 39.9042, "lon": 116.4074}'::jsonb
);

-- データ投入確認
SELECT * FROM public.insights_country;
```

### Step 13: API 設定データの投入

```sql
-- 日本のNewsAPI設定
INSERT INTO public.config_api_settings (
    country_id, api_type, news_country_code, news_page_size, news_category,
    enabled, priority, secret_name
)
SELECT
    id, 'news_api', 'jp', 20, 'general',
    true, 1, 'newsapi-credentials'
FROM public.insights_country WHERE code = 'JPN';

-- 日本のOpenWeatherMap設定
INSERT INTO public.config_api_settings (
    country_id, api_type, weather_city_query, weather_units, weather_lang,
    enabled, priority, secret_name
)
SELECT
    id, 'weather_api', 'Tokyo,JP', 'metric', 'en',
    true, 1, 'openweathermap-credentials'
FROM public.insights_country WHERE code = 'JPN';

-- アメリカのNewsAPI設定
INSERT INTO public.config_api_settings (
    country_id, api_type, news_country_code, news_page_size, news_category,
    enabled, priority, secret_name
)
SELECT
    id, 'news_api', 'us', 20, 'general',
    true, 2, 'newsapi-credentials'
FROM public.insights_country WHERE code = 'USA';

-- アメリカのOpenWeatherMap設定
INSERT INTO public.config_api_settings (
    country_id, api_type, weather_city_query, weather_units, weather_lang,
    enabled, priority, secret_name
)
SELECT
    id, 'weather_api', 'Washington,US', 'metric', 'en',
    true, 2, 'openweathermap-credentials'
FROM public.insights_country WHERE code = 'USA';

-- 中国のNewsAPI設定
INSERT INTO public.config_api_settings (
    country_id, api_type, news_country_code, news_page_size, news_category,
    enabled, priority, secret_name
)
SELECT
    id, 'news_api', 'cn', 20, 'general',
    true, 3, 'newsapi-credentials'
FROM public.insights_country WHERE code = 'CHN';

-- 中国のOpenWeatherMap設定
INSERT INTO public.config_api_settings (
    country_id, api_type, weather_city_query, weather_units, weather_lang,
    enabled, priority, secret_name
)
SELECT
    id, 'weather_api', 'Beijing,CN', 'metric', 'en',
    true, 3, 'openweathermap-credentials'
FROM public.insights_country WHERE code = 'CHN';

-- 設定データ確認
SELECT c.name, a.api_type, a.enabled, a.priority
FROM public.config_api_settings a
JOIN public.insights_country c ON a.country_id = c.id
ORDER BY c.name, a.api_type;
```

## 動作確認

### Step 14: テーブル構造の最終確認

```sql
-- 全テーブル一覧
\dt

-- 各テーブルの構造確認
\d public.insights_country
\d public.config_api_settings
\d public.insights_countrynewsitem
\d public.insights_countryweather
\d public.insights_countryeconomic
\d public.insights_countrytrends
\d public.collection_history
```

### Step 15: 外部キー制約の確認

```sql
-- 外部キー制約一覧
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM
    information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public';
```

### Step 16: サンプルクエリテスト

```sql
-- 国別API設定の取得テスト
SELECT
    c.name as country_name,
    c.code,
    a.api_type,
    a.enabled,
    CASE
        WHEN a.api_type = 'news_api' THEN a.news_country_code
        WHEN a.api_type = 'weather_api' THEN a.weather_city_query
    END as api_parameter
FROM public.insights_country c
LEFT JOIN public.config_api_settings a ON c.id = a.country_id
WHERE a.enabled = true
ORDER BY c.name, a.priority;

-- Web UI用クエリテスト（空のテーブルでも構文確認）
SELECT
    c.name as country_name,
    COUNT(n.id) as news_count,
    COUNT(w.id) as weather_count
FROM public.insights_country c
LEFT JOIN public.insights_countrynewsitem n ON c.id = n.country_id
LEFT JOIN public.insights_countryweather w ON c.id = w.country_id
GROUP BY c.id, c.name
ORDER BY c.name;
```

## 設定パラメータ一覧

### テーブル設計パラメータ

| テーブル名               | 主な用途       | 主キー         | 外部キー   | 特徴                    |
| ------------------------ | -------------- | -------------- | ---------- | ----------------------- |
| insights_country         | 国マスタ       | id (BIGSERIAL) | なし       | 基本的な国情報          |
| config_api_settings      | API 設定       | id (BIGSERIAL) | country_id | 各 API 実パラメータ対応 |
| insights_countrynewsitem | ニュースデータ | id (BIGSERIAL) | country_id | NewsAPI 完全対応        |
| insights_countryweather  | 天気データ     | id (BIGSERIAL) | country_id | OpenWeatherMap 完全対応 |
| insights_countryeconomic | 経済データ     | id (BIGSERIAL) | country_id | World Bank/IMF 対応     |
| insights_countrytrends   | トレンドデータ | id (BIGSERIAL) | country_id | Google Trends 対応      |
| collection_history       | 収集履歴       | id (BIGSERIAL) | country_id | 統合監視用              |

### インデックス設計パラメータ

| インデックス名             | 対象テーブル             | 対象カラム                     | 用途             |
| -------------------------- | ------------------------ | ------------------------------ | ---------------- |
| idx_country_code           | insights_country         | code                           | 国コード検索     |
| idx_news_country_collected | insights_countrynewsitem | country_id, collected_at DESC  | 国別最新ニュース |
| idx_weather_country_time   | insights_countryweather  | country_id, api_timestamp DESC | 国別最新天気     |
| idx_news_fulltext          | insights_countrynewsitem | tsvector(title, description)   | 全文検索         |

## トラブルシューティング

### テーブル作成エラー

1. **権限エラー**

   ```sql
   -- 現在のユーザー権限確認
   \du

   -- スキーマ権限確認
   \dn+
   ```

2. **外部キー制約エラー**
   ```sql
   -- 参照先テーブルの存在確認
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public';
   ```

### インデックス作成エラー

1. **重複インデックス**

   ```sql
   -- 既存インデックス確認
   \di public.*
   ```

2. **GIN インデックスエラー**

   ```sql
   -- 拡張機能確認
   \dx

   -- 必要に応じて拡張機能追加
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   ```

### データ投入エラー

1. **JSONB 形式エラー**

   ```sql
   -- JSONB形式確認
   SELECT '{"lat": 35.6762, "lon": 139.6503}'::jsonb;
   ```

2. **外部キー制約違反**
   ```sql
   -- 参照先データ確認
   SELECT * FROM public.insights_country;
   ```

## 次のステップ

1. AWS Secrets Manager 設定 (03-secrets-manager-setup.md)
2. Lambda 実行用 IAM ロール作成 (04-iam-role-setup.md)
3. Python 開発環境構築とデータベース接続テスト

## 注意事項

- テーブル作成は順序が重要（外部キー制約のため）
- インデックス作成は大量データ投入前に実行する
- JSONB 型のデータは適切な形式で投入する
- 本番環境では適切なバックアップ戦略を実装する
