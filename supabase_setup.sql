-- Drop views first (they depend on tables)
DROP VIEW IF EXISTS active_users;
DROP VIEW IF EXISTS channel_stats;
DROP VIEW IF EXISTS user_stats;
DROP VIEW IF EXISTS recent_searches;
DROP VIEW IF EXISTS top_searchers;

-- Drop tables (child first, parent last)
DROP TABLE IF EXISTS search_logs;
DROP TABLE IF EXISTS required_channels;
DROP TABLE IF EXISTS users;

-- Drop functions
DROP FUNCTION IF EXISTS update_last_active_timestamp;
DROP FUNCTION IF EXISTS increment_search_count;
DROP FUNCTION IF EXISTS get_bot_stats;
DROP FUNCTION IF EXISTS cleanup_old_search_logs;
DROP FUNCTION IF EXISTS toggle_user_ban;

-- ============================================
-- CREATE TABLES
-- ============================================

CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT NOT NULL DEFAULT 'Unknown',
    last_name TEXT,
    is_member BOOLEAN DEFAULT FALSE NOT NULL,
    is_banned BOOLEAN DEFAULT FALSE NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    search_count INTEGER DEFAULT 0 NOT NULL,
    total_searches INTEGER DEFAULT 0 NOT NULL
);

CREATE TABLE required_channels (
    id SERIAL PRIMARY KEY,
    channel_id TEXT UNIQUE NOT NULL,
    channel_name TEXT NOT NULL DEFAULT 'Channel',
    channel_username TEXT,
    channel_type TEXT DEFAULT 'public',
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    added_by BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE search_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    results_found BOOLEAN DEFAULT FALSE NOT NULL,
    result_count INTEGER DEFAULT 0,
    response_time_ms INTEGER
);

-- ============================================
-- CREATE INDEXES
-- ============================================

CREATE INDEX idx_users_is_member ON users(is_member);
CREATE INDEX idx_users_is_banned ON users(is_banned);
CREATE INDEX idx_users_last_active ON users(last_active DESC);
CREATE INDEX idx_users_search_count ON users(search_count DESC);
CREATE INDEX idx_channels_channel_id ON required_channels(channel_id);
CREATE INDEX idx_channels_username ON required_channels(channel_username);
CREATE INDEX idx_channels_is_active ON required_channels(is_active);
CREATE INDEX idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX idx_search_logs_searched_at ON search_logs(searched_at DESC);

-- ============================================
-- CREATE FUNCTIONS
-- ============================================

CREATE FUNCTION update_last_active_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_active = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION increment_search_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users 
    SET search_count = search_count + 1,
        total_searches = total_searches + 1
    WHERE user_id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION get_bot_stats()
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_users', (SELECT COUNT(*) FROM users),
        'active_members', (SELECT COUNT(*) FROM users WHERE is_member = TRUE),
        'banned_users', (SELECT COUNT(*) FROM users WHERE is_banned = TRUE),
        'total_channels', (SELECT COUNT(*) FROM required_channels WHERE is_active = TRUE),
        'total_searches', (SELECT COUNT(*) FROM search_logs),
        'searches_today', (SELECT COUNT(*) FROM search_logs WHERE searched_at > CURRENT_DATE)
    ) INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION cleanup_old_search_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM search_logs WHERE searched_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION toggle_user_ban(target_user_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    current_status BOOLEAN;
BEGIN
    SELECT is_banned INTO current_status FROM users WHERE user_id = target_user_id;
    IF current_status IS NULL THEN RETURN FALSE; END IF;
    UPDATE users SET is_banned = NOT current_status WHERE user_id = target_user_id;
    RETURN NOT current_status;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- CREATE TRIGGERS
-- ============================================

CREATE TRIGGER update_users_last_active
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_last_active_timestamp();

CREATE TRIGGER auto_increment_search_count
    AFTER INSERT ON search_logs
    FOR EACH ROW
    EXECUTE FUNCTION increment_search_count();

-- ============================================
-- CREATE VIEWS
-- ============================================

CREATE VIEW active_users AS
SELECT user_id, username, first_name, search_count, last_active, joined_at
FROM users
WHERE is_member = TRUE AND is_banned = FALSE
ORDER BY last_active DESC;

CREATE VIEW channel_stats AS
SELECT 
    COUNT(*) as total_channels,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_channels,
    COUNT(*) FILTER (WHERE channel_type = 'public') as public_channels,
    COUNT(*) FILTER (WHERE channel_type = 'private') as private_channels
FROM required_channels;

CREATE VIEW user_stats AS
SELECT 
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE is_member = TRUE) as active_members,
    COUNT(*) FILTER (WHERE is_banned = TRUE) as banned_users,
    SUM(search_count) as total_searches
FROM users;

CREATE VIEW recent_searches AS
SELECT sl.id, sl.user_id, u.username, u.first_name, sl.query, sl.searched_at, sl.results_found
FROM search_logs sl
JOIN users u ON sl.user_id = u.user_id
ORDER BY sl.searched_at DESC
LIMIT 100;

CREATE VIEW top_searchers AS
SELECT u.user_id, u.username, u.first_name, u.search_count, u.last_active
FROM users u
WHERE u.is_member = TRUE
ORDER BY u.search_count DESC
LIMIT 50;
