"""
core/database.py — All Database Operations
Pro-Level: 
  ✅ Consistent field names throughout
  ✅ Proper error handling
  ✅ Returns proper types
  ✅ Logs errors properly
  ✅ Ban-aware
"""
import html
from datetime import datetime
from typing import List, Dict, Optional, Any

from supabase import create_client, Client

from core.config import config


# ══════════════════════════════════════════════════════════════
#                     SUPABASE CLIENT
# ══════════════════════════════════════════════════════════════

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


# ══════════════════════════════════════════════════════════════
#                     ERROR LOGGER
# ══════════════════════════════════════════════════════════════

def _log_db_error(operation: str, error: Exception, extra: str = "") -> None:
    """Centralized error logging for database operations."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] DB Error in '{operation}': {type(error).__name__}: {error}"
    if extra:
        msg += f" | Extra: {extra}"
    print(msg)


# ══════════════════════════════════════════════════════════════
#                     USER OPERATIONS
# ══════════════════════════════════════════════════════════════

def db_add_user(user_id: int, username: str = None, first_name: str = None) -> bool:
    """Add or update user in database."""
    try:
        data = {
            "user_id": user_id,
            "username": username or "",
            "first_name": html.escape(first_name or "Unknown"),
            "is_member": False,
            "is_banned": False,
            "last_active": datetime.now().isoformat(),
            "search_count": 0,
            "total_searches": 0
        }
        supabase.table("users").upsert(data, on_conflict="user_id").execute()
        return True
    except Exception as e:
        _log_db_error("add_user", e)
        return False


def db_get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user from database. Returns None if not found."""
    try:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        _log_db_error("get_user", e, f"user_id={user_id}")
        return None


def db_is_banned(user_id: int) -> bool:
    """Check if user is banned."""
    user = db_get_user(user_id)
    if user is None:
        return False  # New users aren't banned
    return bool(user.get("is_banned", False))


def db_set_verified(user_id: int, verified: bool) -> bool:
    """Set user membership/verification status."""
    try:
        supabase.table("users").update({
            "is_member": verified,
            "last_active": datetime.now().isoformat()
        }).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        _log_db_error("set_verified", e, f"user_id={user_id}")
        return False


def db_get_all_users(limit: int = 1000) -> List[Dict[str, Any]]:
    """Get all users with optional limit."""
    try:
        result = (
            supabase.table("users")
            .select("user_id, username, first_name, is_member, is_banned, search_count, last_active")
            .order("last_active", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        _log_db_error("get_all_users", e)
        return []


def db_get_active_users() -> List[Dict[str, Any]]:
    """Get only verified, non-banned users for broadcasting."""
    try:
        result = (
            supabase.table("users")
            .select("user_id")
            .eq("is_member", True)
            .eq("is_banned", False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        _log_db_error("get_active_users", e)
        return []


def db_toggle_ban(user_id: int) -> Optional[bool]:
    """Toggle user ban status. Returns new status or None on error."""
    try:
        user = db_get_user(user_id)
        if not user:
            return None
        new_status = not bool(user.get("is_banned", False))
        supabase.table("users").update({"is_banned": new_status}).eq("user_id", user_id).execute()
        return new_status
    except Exception as e:
        _log_db_error("toggle_ban", e, f"user_id={user_id}")
        return None


def db_update_user_activity(user_id: int) -> bool:
    """Update user's last active timestamp."""
    try:
        supabase.table("users").update({
            "last_active": datetime.now().isoformat()
        }).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        _log_db_error("update_user_activity", e, f"user_id={user_id}")
        return False


# ══════════════════════════════════════════════════════════════
#                     CHANNEL OPERATIONS
# ══════════════════════════════════════════════════════════════

def db_get_channels(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    Get all required channels.
    
    Field normalization:
      - Always returns channel_id, channel_name, channel_username,
        channel_type, invite_link, is_active
    """
    try:
        query = supabase.table("required_channels").select("*")
        if not include_inactive:
            query = query.eq("is_active", True)
        result = query.execute()
        
        # Normalize fields to consistent names
        channels = []
        for ch in (result.data or []):
            channels.append({
                "channel_id": str(ch.get("channel_id", "")),
                "channel_name": ch.get("channel_name", ""),
                "channel_username": ch.get("channel_username") or None,
                "channel_type": ch.get("channel_type") or "public",
                "invite_link": ch.get("invite_link") or None,
                "is_active": ch.get("is_active", True),
                "added_at": ch.get("added_at", ""),
                "added_by": ch.get("added_by", 0),
                "description": ch.get("description") or None,
            })
        return channels
    
    except Exception as e:
        _log_db_error("get_channels", e)
        return []


def db_add_channel(
    channel_id: str,
    channel_name: str,
    channel_username: str = None,
    channel_type: str = "public",
    invite_link: str = None
) -> bool:
    """
    Add or update a required channel.
    
    Args:
        channel_id: Telegram channel ID (-1001234567890 or @username)
        channel_name: Display name
        channel_username: Telegram @username (for public channels)
        channel_type: public/private/supergroup/channel/joinrequest
        invite_link: Invite link (for private channels)
    """
    try:
        data = {
            "channel_id": str(channel_id),
            "channel_name": html.escape(channel_name),
            "channel_username": channel_username.lstrip("@") if channel_username else None,
            "channel_type": channel_type,
            "invite_link": invite_link or None,
            "is_active": True,
            "added_at": datetime.now().isoformat(),
            "added_by": config.OWNER_ID
        }
        supabase.table("required_channels").upsert(data, on_conflict="channel_id").execute()
        return True
    except Exception as e:
        _log_db_error("add_channel", e, f"channel_id={channel_id}")
        return False


def db_update_channel_invite_link(channel_id: str, invite_link: str) -> bool:
    """Update the invite link for a channel (for private channels)."""
    try:
        supabase.table("required_channels").update({
            "invite_link": invite_link
        }).eq("channel_id", str(channel_id)).execute()
        return True
    except Exception as e:
        _log_db_error("update_channel_invite_link", e, f"channel_id={channel_id}")
        return False


def db_remove_channel(channel_id: str) -> bool:
    """Soft-remove a channel (set is_active=False)."""
    try:
        supabase.table("required_channels").update({"is_active": False}).eq("channel_id", str(channel_id)).execute()
        return True
    except Exception as e:
        _log_db_error("remove_channel", e, f"channel_id={channel_id}")
        return False


def db_delete_channel(channel_id: str) -> bool:
    """Hard-delete a channel from database."""
    try:
        supabase.table("required_channels").delete().eq("channel_id", str(channel_id)).execute()
        return True
    except Exception as e:
        _log_db_error("delete_channel", e, f"channel_id={channel_id}")
        return False


def db_get_channel_by_id(channel_id: str) -> Optional[Dict[str, Any]]:
    """Get a single channel by ID."""
    try:
        result = supabase.table("required_channels").select("*").eq("channel_id", str(channel_id)).execute()
        if result.data:
            ch = result.data[0]
            return {
                "channel_id": str(ch.get("channel_id", "")),
                "channel_name": ch.get("channel_name", ""),
                "channel_username": ch.get("channel_username") or None,
                "channel_type": ch.get("channel_type") or "public",
                "invite_link": ch.get("invite_link") or None,
                "is_active": ch.get("is_active", True),
            }
        return None
    except Exception as e:
        _log_db_error("get_channel_by_id", e, f"channel_id={channel_id}")
        return None


# ══════════════════════════════════════════════════════════════
#                     SEARCH LOG OPERATIONS
# ══════════════════════════════════════════════════════════════

def db_log_search(
    user_id: int,
    query: str,
    results_count: int,
    response_time_ms: int = None
) -> bool:
    """Log a search query."""
    try:
        data = {
            "user_id": user_id,
            "query": query[:500],  # Truncate long queries
            "result_count": results_count,
            "results_found": results_count > 0,
            "response_time_ms": response_time_ms,
            "searched_at": datetime.now().isoformat()
        }
        supabase.table("search_logs").insert(data).execute()
        return True
    except Exception as e:
        _log_db_error("log_search", e)
        return False


def db_get_user_search_count(user_id: int) -> int:
    """Get total search count for a user."""
    try:
        user = db_get_user(user_id)
        return user.get("search_count", 0) if user else 0
    except Exception as e:
        _log_db_error("get_user_search_count", e, f"user_id={user_id}")
        return 0


# ══════════════════════════════════════════════════════════════
#                     STATISTICS
# ══════════════════════════════════════════════════════════════

def db_get_stats() -> Dict[str, Any]:
    """Get comprehensive bot statistics."""
    try:
        users = supabase.table("users").select("*", count="exact").execute()
        verified = supabase.table("users").select("*", count="exact").eq("is_member", True).eq("is_banned", False).execute()
        banned = supabase.table("users").select("*", count="exact").eq("is_banned", True).execute()
        channels = supabase.table("required_channels").select("*", count="exact").eq("is_active", True).execute()
        
        return {
            "total_users": users.count or 0,
            "verified_users": verified.count or 0,
            "banned_users": banned.count or 0,
            "total_channels": channels.count or 0,
            "active_channels": channels.count or 0
        }
    except Exception as e:
        _log_db_error("get_stats", e)
        return {
            "total_users": 0,
            "verified_users": 0,
            "banned_users": 0,
            "total_channels": 0,
            "active_channels": 0
        }
