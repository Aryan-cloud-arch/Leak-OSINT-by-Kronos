"""
core/__init__.py — Core Module Exports
"""
from core.config import config, BotConfig
from core.cache import (
    TTLCache,
    channel_cache,
    membership_cache,
    report_cache,
    cooldown_cache,
    rate_limit_cache,
    global_report_cache
)
from core.database import (
    supabase,
    db_add_user,
    db_get_user,
    db_is_banned,
    db_set_verified,
    db_get_all_users,
    db_get_active_users,
    db_toggle_ban,
    db_update_user_activity,
    db_get_channels,
    db_add_channel,
    db_update_channel_invite_link,
    db_remove_channel,
    db_delete_channel,
    db_get_channel_by_id,
    db_log_search,
    db_get_user_search_count,
    db_get_stats
)

__all__ = [
    # Config
    "config",
    "BotConfig",
    
    # Cache
    "TTLCache",
    "channel_cache",
    "membership_cache",
    "report_cache",
    "cooldown_cache",
    "rate_limit_cache",
    "global_report_cache",
    
    # Database - Users
    "supabase",
    "db_add_user",
    "db_get_user",
    "db_is_banned",
    "db_set_verified",
    "db_get_all_users",
    "db_get_active_users",
    "db_toggle_ban",
    "db_update_user_activity",
    
    # Database - Channels
    "db_get_channels",
    "db_add_channel",
    "db_update_channel_invite_link",
    "db_remove_channel",
    "db_delete_channel",
    "db_get_channel_by_id",
    
    # Database - Search & Stats
    "db_log_search",
    "db_get_user_search_count",
    "db_get_stats",
]
