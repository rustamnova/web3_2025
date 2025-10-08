CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.events (
    id UUID DEFAULT generateUUIDv4(),
    timestamp DateTime DEFAULT now(),
    user_id String,
    event_type String,
    payload String
)
ENGINE = MergeTree()
ORDER BY (timestamp);

CREATE TABLE IF NOT EXISTS analytics.metrics (
    date Date DEFAULT today(),
    metric String,
    value Float64,
    tags Map(String, String)
)
ENGINE = SummingMergeTree()
ORDER BY (date, metric);
