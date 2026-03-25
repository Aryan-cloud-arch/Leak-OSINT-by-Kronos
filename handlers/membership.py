"""
handlers/membership.py — Membership Verification + Smart Link Builder
Pro-Level:
  ✅ ALL channel types handled (public/private/supergroup/joinrequest/group)
  ✅ channel_username passed through the entire chain
  ✅ invite_link stored and reused for private channels
  ✅ Cache with TTL to prevent API spam
  ✅ Ban-aware
  ✅ Graceful degradation on errors
"""
import html
from typing import List, Dict, Optional, Any

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.config import config
from core.database import (
    db_get_channels,
    db_add_channel,
    db_update_channel_invite_link,
    db_is_banned
)
from core.cache import channel_cache, membership_cache


# ══════════════════════════════════════════════════════════════
#                 SMART CHANNEL LINK BUILDER
# ══════════════════════════════════════════════════════════════

def build_channel_link(
    bot,
    channel_id: str,
    channel_username: Optional[str],
    channel_type: str,
    stored_invite_link: Optional[str]
) -> str:
    """
    Build the correct join URL for ANY channel type.
    
    Priority Order:
      1. Stored @username → https://t.me/username ✅ (FASTEST, BEST UX)
      2. Stored invite_link → Use as-is ✅ (For private channels)
      3. API: get_chat().username → https://t.me/username ✅
      4. API: get_chat().invite_link → Use it ✅  
      5. API: export_chat_invite_link() → Generate + STORE it ✅
      6. FALLBACK: https://t.me/c/XXXXX ❌ (last resort)
    
    Channel Types Handled:
      • public          → Has @username, t.me/username works
      • private         → No username, needs invite link
      • supergroup      → Can have @username or be private
      • channel         → Can have @username or be private
      • joinrequest     → Join request enabled, needs special handling
      • group           → Legacy basic groups (rare)
    
    Args:
        bot: TeleBot instance
        channel_id: Telegram channel ID
        channel_username: Stored @username (from DB)
        channel_type: Channel type string
        stored_invite_link: Stored invite link (from DB, for private)
    
    Returns:
        str: Valid join URL
    """
    
    # ─── PRIORITY 1: Use stored @username (fastest, best UX) ───
    if channel_username:
        clean_username = channel_username.lstrip("@")
        if clean_username and not clean_username.startswith("-"):
            return f"https://t.me/{clean_username}"
    
    # ─── PRIORITY 2: Use stored invite link (for private channels) ───
    if stored_invite_link:
        return stored_invite_link
    
    # ─── PRIORITY 3: Fetch fresh from Telegram API ───
    try:
        chat = bot.get_chat(channel_id)
        
        # A) Username found → use it
        if chat.username:
            url = f"https://t.me/{chat.username}"
            # Update DB with username if we didn't have it
            if not channel_username:
                try:
                    db_add_channel(
                        channel_id=str(chat.id),
                        channel_name=chat.title or "Channel",
                        channel_username=chat.username,
                        channel_type=chat.type or channel_type
                    )
                except Exception:
                    pass
            return url
        
        # B) Chat already has an invite link → use it
        if hasattr(chat, 'invite_link') and chat.invite_link:
            try:
                db_update_channel_invite_link(channel_id, chat.invite_link)
            except Exception:
                pass
            return chat.invite_link
        
        # C) No invite link, export one
        try:
            invite_link = bot.export_chat_invite_link(channel_id)
            if invite_link:
                try:
                    db_update_channel_invite_link(channel_id, invite_link)
                except Exception:
                    pass
                return invite_link
        except Exception as export_error:
            print(f"Failed to export invite link for {channel_id}: {export_error}")
        
        # D) Last resort for supergroups — internal link format
        if str(channel_id).startswith("-100"):
            numeric_id = str(channel_id)[4:]
            return f"https://t.me/c/{numeric_id}"
        
        # E) Unknown format fallback
        return f"https://t.me/{channel_id}"
    
    except Exception as e:
        print(f"build_channel_link error for {channel_id}: {e}")
        
        # ─── EMERGENCY FALLBACKS ───
        if str(channel_id).startswith("-100"):
            numeric_id = str(channel_id)[4:]
            return f"https://t.me/c/{numeric_id}"
        elif str(channel_id).startswith("@"):
            return f"https://t.me/{channel_id[1:]}"
        else:
            return f"https://t.me/{channel_id}"


# ══════════════════════════════════════════════════════════════
#                  CHANNEL CACHE HELPERS
# ══════════════════════════════════════════════════════════════

def _get_cached_channels() -> List[Dict]:
    """Get channels with TTL cache."""
    cached = channel_cache.get("required_channels")
    if cached is not None:
        return cached
    
    channels = db_get_channels()
    channel_cache.set("required_channels", channels, ttl=config.CHANNEL_CACHE_TTL)
    return channels


def refresh_channel_cache() -> List[Dict]:
    """Force refresh the channel list cache."""
    channel_cache.delete("required_channels")
    return _get_cached_channels()


def invalidate_membership_cache(user_id: int = None) -> None:
    """
    Manually invalidate membership cache.
    Call after user joins channel or when channels change.
    """
    if user_id:
        membership_cache.delete(f"member_check_{user_id}")
    else:
        membership_cache.clear()


# ══════════════════════════════════════════════════════════════
#                  MEMBERSHIP CHECK (CACHED)
# ══════════════════════════════════════════════════════════════

def check_user_membership(user_id: int, bot) -> Dict[str, Any]:
    """
    Check if user is member of ALL required channels.
    
    ✅ CACHED: Results cached for 5 minutes to prevent API spam.
    ✅ Passes channel_username through the entire chain.
    ✅ Handles all error cases gracefully.
    ✅ Ban-aware.
    
    Returns:
        {
            "is_member": bool,
            "missing_channels": List[channel dicts],
            "channels": List[channel dicts],
            "is_banned": bool
        }
    """
    
    # ─── Check ban status first ───
    if db_is_banned(user_id):
        return {
            "is_member": False,
            "missing_channels": [],
            "channels": [],
            "is_banned": True
        }
    
    # ─── Check cache ───
    cache_key = f"member_check_{user_id}"
    cached = membership_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # ─── Fetch channels (also cached) ───
    channels = _get_cached_channels()
    
    # ─── No channels configured = everyone passes ───
    if not channels:
        result = {
            "is_member": True,
            "missing_channels": [],
            "channels": [],
            "is_banned": False
        }
        membership_cache.set(cache_key, result, ttl=config.MEMBERSHIP_CACHE_TTL)
        return result
    
    # ─── Check each channel ───
    missing = []
    all_checked = []
    
    for channel in channels:
        channel_id = channel.get("channel_id", "")
        channel_name = channel.get("channel_name") or "Channel"
        channel_type = channel.get("channel_type") or "public"
        channel_username = channel.get("channel_username")  # ✅ THIS GOES THROUGH
        invite_link = channel.get("invite_link")  # ✅ THIS GOES THROUGH
        
        is_member = False
        error_occurred = False
        
        try:
            member = bot.get_chat_member(channel_id, user_id)
            status = member.status
            
            # Determine membership status
            is_member = status in ("member", "administrator", "creator")
            
            # Handle restricted/join-request users
            if not is_member and status == "restricted":
                is_member = getattr(member, 'is_member', False)
            
            # Handle left/kicked members
            if status in ("left", "kicked"):
                is_member = False
        
        except Exception as e:
            print(f"Membership check error for {channel_id}: {e}")
            error_occurred = True
            is_member = False
        
        # Build channel data with ALL fields
        channel_data = {
            "channel_id": channel_id,
            "channel_name": html.escape(channel_name),
            "channel_type": channel_type,
            "channel_username": channel_username,  # ✅ PASSED THROUGH
            "invite_link": invite_link,  # ✅ PASSED THROUGH
            "is_member": is_member
        }
        
        all_checked.append(channel_data)
        
        if not is_member:
            missing.append(channel_data)  # ✅ channel_username IS HERE NOW
    
    result = {
        "is_member": len(missing) == 0,
        "missing_channels": missing,
        "channels": all_checked,
        "is_banned": False
    }
    
    # ─── Cache the result ───
    membership_cache.set(cache_key, result, ttl=config.MEMBERSHIP_CACHE_TTL)
    
    return result


# ══════════════════════════════════════════════════════════════
#                 JOIN BUTTON BUILDER (THE DISPLAY FIX)
# ══════════════════════════════════════════════════════════════

def create_join_markup(
    channels: List[Dict],
    include_verify: bool = True,
    bot = None
) -> InlineKeyboardMarkup:
    """
    Create beautifully styled join channel buttons.
    
    ✅ Uses channel_username FIRST (from DB → passed through → used here)
    ✅ Falls back to invite_link for private channels
    ✅ Generates fresh links only when absolutely needed
    ✅ Colorful, styled buttons with proper links
    
    Args:
        channels: List of channel dicts (must have channel_username!)
        include_verify: Add the verification button
        bot: TeleBot instance for API fallback
    
    Returns:
        InlineKeyboardMarkup with join buttons
    """
    markup = InlineKeyboardMarkup()
    
    # Colorful emojis for visual variety
    color_emojis = ["🔵", "🟢", "🟣", "🟠", "🔴", "🟡", "⚪", "🟤"]
    
    for idx, channel in enumerate(channels):
        
        # ─── Extract all channel info (including username!) ───
        channel_id = channel.get("channel_id", "")
        channel_name = channel.get("channel_name") or "Channel"
        channel_username = channel.get("channel_username")  # ✅ THE KEY FIELD
        channel_type = channel.get("channel_type") or "public"
        stored_invite_link = channel.get("invite_link")  # ✅ FOR PRIVATE CHANNELS
        
        emoji = color_emojis[idx % len(color_emojis)]
        
        # ─── Build the correct URL ───
        if bot:
            url = build_channel_link(
                bot=bot,
                channel_id=channel_id,
                channel_username=channel_username,
                channel_type=channel_type,
                stored_invite_link=stored_invite_link
            )
        else:
            # Fallback if bot instance not passed
            if channel_username:
                url = f"https://t.me/{channel_username.lstrip('@')}"
            elif stored_invite_link:
                url = stored_invite_link
            elif str(channel_id).startswith("@"):
                url = f"https://t.me/{channel_id[1:]}"
            elif str(channel_id).startswith("-100"):
                url = f"https://t.me/c/{channel_id[4:]}"
            else:
                url = f"https://t.me/{channel_id}"
        
        # ─── Smart button text based on channel type ───
        type_indicator = {
            "public": "🔗",
            "private": "🔒",
            "supergroup": "👥",
            "channel": "📢",
            "joinrequest": "📩",
            "join_request": "📩",
            "group": "👥"
        }.get(channel_type, "🔗")
        
        # Clean channel name for button
        clean_name = channel_name[:20] + "..." if len(channel_name) > 20 else channel_name
        button_text = f"{emoji} {type_indicator} ᴊᴏɪɴ {clean_name.upper()}"
        
        markup.add(InlineKeyboardButton(
            text=button_text,
            url=url
        ))
    
    # ─── Verify button ───
    if include_verify:
        markup.add(InlineKeyboardButton(
            text="✅ ᴄʜᴇᴄᴋ ᴍᴇᴍʙᴇʀꜱʜɪᴘ ✅",
            callback_data="verify_join"
        ))
    
    return markup


# ══════════════════════════════════════════════════════════════
#                 CHANNEL LINK DISPLAY HELPER
# ══════════════════════════════════════════════════════════════

def get_channel_display_link(channel: Dict, bot=None) -> str:
    """
    Get a display-friendly link for a channel.
    Used in admin panels and channel listings.
    """
    channel_username = channel.get("channel_username")
    invite_link = channel.get("invite_link")
    channel_id = channel.get("channel_id", "")
    
    if channel_username:
        return f"https://t.me/{channel_username.lstrip('@')}"
    elif invite_link:
        return invite_link
    elif bot:
        return build_channel_link(
            bot=bot,
            channel_id=channel_id,
            channel_username=None,
            channel_type=channel.get("channel_type", "public"),
            stored_invite_link=None
        )
    else:
        return f"ID: {channel_id}"
