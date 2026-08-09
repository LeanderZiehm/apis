CREATE TABLE pixel_tracker_events_v2 (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) NOT NULL,
    user_agent TEXT,
    ip_address VARCHAR(255),
    referrer TEXT,
    original_url TEXT,
    visitor_id VARCHAR(255),
    raw_request_url TEXT NOT NULL,
    query_parameters TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_pixel_tracker_events_slug
    ON pixel_tracker_events (slug);
CREATE INDEX idx_pixel_tracker_events_visitor_id
    ON pixel_tracker_events (visitor_id);
CREATE INDEX idx_pixel_tracker_events_timestamp
    ON pixel_tracker_events (timestamp);