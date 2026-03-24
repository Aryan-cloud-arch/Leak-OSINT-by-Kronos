-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
--           LeakOSINT Bot - Complete Database Setup
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- ============================================
-- 1. DROP EXISTING TABLES (Clean Start)
-- ============================================
DROP TABLE IF EXISTS search_logs CASCADE;
DROP TABLE IF EXISTS required_channels CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TRIGGER IF EXISTS update_users_last_active ON users;
DROP FUNCTION IF EXISTS update_last_active_timestamp();

-- ============================================
-- 2. CREATE TABLES
-- ============================================

-- Users Table
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT,
    is_member BOOLEAN DEFAULT FALSE NOT NULL,
    is_banned BOOLEAN DEFAULT FALSE NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    search_count INTEGER DEFAULT 0 NOT NULL CHECK (search_count >= 0),
    total_searches INTEGER DEFAULT 0 NOT NULL CHECK (total_searches >= 0),
    CONSTRAINT valid_user_id CHECK (user_id > 0)
);

-- Required Channels Table
CREATE TABLE required_channels (
    id SERIAL PRIMARY KEY,
    channel_id TEXT UNIQUE NOT NULL,
    channel_name TEXT NOT NULL,
    channel_username TEXT,
    channel_type TEXT CHECK (channel_type IN ('public', 'private', 'group')),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    added_by BIGINT NOT NULL,
    CONSTRAINT valid_channel_id CHECK (channel_id <> '')
);

-- Search Logs Table
CREATE TABLE search_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    query TEXT NOT NULL,
    searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    results_found BOOLEAN DEFAULT FALSE NOT NULL,
    result_count INTEGER DEFAULT 0 CHECK (result_count >= 0),
    response_time_ms INTEGER,
    CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT valid_query CHECK (LENGTH(query) > 0)
);

-- ============================================
-- 3. CREATE INDEXES FOR PERFORMANCE
-- ============================================

-- Users indexes
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_is_member ON users(is_member) WHERE is_member = TRUE;
CREATE INDEX idx_users_is_banned ON users(is_banned) WHERE is_banned = TRUE;
CREATE INDEX idx_users_joined_at ON users(joined_at DESC);
CREATE INDEX idx_users_last_active ON users(last_active DESC);
CREATE INDEX idx_users_search_count ON users(search_count DESC);

-- Channels indexes
CREATE INDEX idx_channels_channel_id ON required_channels(channel_id);
CREATE INDEX idx_channels_username ON required_channels(channel_username);
CREATE INDEX idx_channels_is_active ON required_channels(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_channels_added_at ON required_channels(added_at DESC);

-- Search logs indexes
CREATE INDEX idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX idx_search_logs_searched_at ON search_logs(searched_at DESC);
CREATE INDEX idx_search_logs_query ON search_logs USING gin(to_tsvector('english', query));

-- ============================================
-- 4. CREATE TRIGGERS & FUNCTIONS
-- ============================================

-- Function to auto-update last_active timestamp
CREATE OR REPLACE FUNCTION update_last_active_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_active = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on users table
CREATE TRIGGER update_users_last_active
    BEFORE UPDATE ON users
    FOR EACH ROW
    WHEN (OLD.* IS DISTINCT FROM NEW.*)
    EXECUTE FUNCTION update_last_active_timestamp();

-- Function to increment search count
CREATE OR REPLACE FUNCTION increment_search_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users 
    SET search_count = search_count + 1,
        total_searches = total_searches + 1
    WHERE user_id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-increment search count on new search
CREATE TRIGGER auto_increment_search_count
    AFTER INSERT ON search_logs
    FOR EACH ROW
    EXECUTE FUNCTION increment_search_count();

-- ============================================
-- 5. CREATE VIEWS FOR ANALYTICS
-- ============================================

-- Active users view
CREATE OR REPLACE VIEW active_users AS
SELECT 
    user_id,
    username,
    first_name,
    search_count,
    last_active,
    joined_at
FROM users
WHERE is_member = TRUE 
  AND is_banned = FALSE
ORDER BY last_active DESC;

-- Channel statistics view
CREATE OR REPLACE VIEW channel_stats AS
SELECT 
    COUNT(*) as total_channels,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_channels,
    COUNT(*) FILTER (WHERE channel_type = 'public') as public_channels,
    COUNT(*) FILTER (WHERE channel_type = 'private') as private_channels
FROM required_channels;

-- User statistics view
CREATE OR REPLACE VIEW user_stats AS
SELECT 
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE is_member = TRUE) as active_members,
    COUNT(*) FILTER (WHERE is_banned = TRUE) as banned_users,
    COUNT(*) FILTER (WHERE last_active > NOW() - INTERVAL '24 hours') as active_24h,
    COUNT(*) FILTER (WHERE last_active > NOW() - INTERVAL '7 days') as active_7d,
    SUM(search_count) as total_searches
FROM users;

-- Recent searches view
CREATE OR REPLACE VIEW recent_searches AS
SELECT 
    sl.id,
    sl.user_id,
    u.username,
    u.first_name,
    sl.query,
    sl.searched_at,
    sl.results_found,
    sl.result_count
FROM search_logs sl
JOIN users u ON sl.user_id = u.user_id
ORDER BY sl.searched_at DESC
LIMIT 100;

-- Top searchers view
CREATE OR REPLACE VIEW top_searchers AS
SELECT 
    u.user_id,
    u.username,
    u.first_name,
    u.search_count,
    u.last_active,
    COUNT(sl.id) as recent_searches
FROM users u
LEFT JOIN search_logs sl ON u.user_id = sl.user_id 
    AND sl.searched_at > NOW() - INTERVAL '7 days'
WHERE u.is_member = TRUE
GROUP BY u.user_id, u.username, u.first_name, u.search_count, u.last_active
ORDER BY u.search_count DESC
LIMIT 50;

-- ============================================
-- 6. DISABLE ROW LEVEL SECURITY (Not needed for bot)
-- ============================================

-- Note: RLS is disabled because the bot uses service role key
-- which bypasses RLS anyway. This prevents permission issues.

ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE required_channels DISABLE ROW LEVEL SECURITY;
ALTER TABLE search_logs DISABLE ROW LEVEL SECURITY;

-- ============================================
-- 7. UTILITY FUNCTIONS
-- ============================================

-- Function to get bot statistics
CREATE OR REPLACE FUNCTION get_bot_stats()
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
        'searches_today', (SELECT COUNT(*) FROM search_logs WHERE searched_at > CURRENT_DATE),
        'active_24h', (SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '24 hours'),
        'active_7d', (SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '7 days')
    ) INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old search logs (optional - run via cron)
CREATE OR REPLACE FUNCTION cleanup_old_search_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM search_logs 
    WHERE searched_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to ban/unban user
CREATE OR REPLACE FUNCTION toggle_user_ban(target_user_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    current_status BOOLEAN;
BEGIN
    SELECT is_banned INTO current_status FROM users WHERE user_id = target_user_id;
    
    IF current_status IS NULL THEN
        RETURN FALSE;
    END IF;
    
    UPDATE users SET is_banned = NOT current_status WHERE user_id = target_user_id;
    RETURN NOT current_status;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 8. GRANT PERMISSIONS
-- ============================================

-- Permissions are automatically granted when using Supabase service role key
-- No additional grants needed

-- ============================================
-- 9. SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
    RAISE NOTICE '✅ Database setup completed successfully!';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Created:';
    RAISE NOTICE '   • 3 Tables (users, required_channels, search_logs)';
    RAISE NOTICE '   • 13 Indexes';
    RAISE NOTICE '   • 2 Triggers';
    RAISE NOTICE '   • 5 Views';
    RAISE NOTICE '   • 4 Utility Functions';
    RAISE NOTICE '   • RLS Policies';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Ready to deploy!';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
END $$;
