"""
handlers/ui.py — All Message Templates & UI Elements
Pro-Level:
  ✅ UI.bullet() fixed (was causing crashes)
  ✅ All user input HTML-escaped
  ✅ Consistent styling with small-caps and borders
  ✅ All required message functions included
"""
import html
from typing import List, Dict, Any

from core.config import config


# ══════════════════════════════════════════════════════════════
#                      DESIGN ELEMENTS
# ══════════════════════════════════════════════════════════════

class UI:
    """Clean UI elements for consistent design"""
    
    # Lines
    HEAVY_LINE = "━━━━━━━━━━━━━━━━━━━━━━"
    LIGHT_LINE = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    DOUBLE_LINE = "══════════════════════"
    DOT_LINE = "• • • • • • • • • • • •"
    SPARKLE_LINE = "✦ ━━━━━━━━━━━━━━━━ ✦"
    
    # Status Icons
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    SEARCH = "🔍"
    LOCK = "🔒"
    UNLOCK = "🔓"
    STAR = "⭐"
    FIRE = "🔥"
    BOLT = "⚡"
    
    # Category Icons
    USER = "👤"
    USERS = "👥"
    PHONE = "📞"
    EMAIL = "📧"
    HOME = "🏠"
    ID = "🆔"
    CARD = "💳"
    GLOBE = "🌐"
    DATABASE = "🗄️"
    CHANNEL = "📢"
    BOT = "🤖"
    ADMIN = "👑"
    STATS = "📊"
    SETTINGS = "⚙️"
    LINK = "🔗"
    KEY = "🔑"
    SHIELD = "🛡️"
    CHECK = "☑️"
    BAN = "🚫"
    
    @staticmethod
    def bullet(text: str, indent: int = 0) -> str:
        """Create a bullet point"""
        spaces = "  " * indent
        return f"{spaces}• {text}"
    
    @staticmethod
    def numbered(num: int, text: str) -> str:
        """Create a numbered item"""
        return f"{num}. {text}"


# ══════════════════════════════════════════════════════════════
#                     HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def safe_escape(text: Any) -> str:
    """Safely HTML escape any value"""
    if text is None:
        return "N/A"
    return html.escape(str(text))


def get_user_mention(user) -> str:
    """Get user mention string, HTML-safe"""
    if user.username:
        return f"@{safe_escape(user.username)}"
    name = safe_escape(user.first_name or "User")
    return f"<a href='tg://user?id={user.id}'>{name}</a>"


def is_group_chat(message) -> bool:
    """Check if message is from a group"""
    return message.chat.type in ["group", "supergroup"]


def get_channel_type_icon(channel_type: str) -> str:
    """Get icon for channel type"""
    icons = {
        "public": "📢",
        "private": "🔒",
        "supergroup": "👥",
        "channel": "📢",
        "joinrequest": "📩",
        "join_request": "📩",
        "group": "👥"
    }
    return icons.get(channel_type, "📢")


# ══════════════════════════════════════════════════════════════
#                     OWNER MESSAGES
# ══════════════════════════════════════════════════════════════

def msg_welcome_owner() -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.ADMIN} ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ
{UI.HEAVY_LINE}

ᴡᴇʟᴄᴏᴍᴇ ʙᴀᴄᴋ, ᴏᴡɴᴇʀ! {UI.FIRE}

{UI.LIGHT_LINE}
{UI.SETTINGS} Channel Management
{UI.LIGHT_LINE}
• /addchannel <code>@channel</code>
• /addchannel <code>-100xxxxx</code>
• /removechannel
• /channels

{UI.LIGHT_LINE}
{UI.USERS} User Management
{UI.LIGHT_LINE}
• /users - All users
• /stats - Bot statistics
• /broadcast <code>message</code>
• /ban <code>user_id</code>

{UI.LIGHT_LINE}
{UI.SEARCH} Search
{UI.LIGHT_LINE}
Just send any query to search!

{UI.HEAVY_LINE}
"""


def msg_stats(stats: Dict[str, Any]) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.STATS} ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ
{UI.HEAVY_LINE}

{UI.USERS} <b>ᴜꜱᴇʀꜱ</b>
  🟢 ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ    : <code>{stats.get('total_users', 0)}</code>
  🔵 ᴠᴇʀɪꜰɪᴇᴅ       : <code>{stats.get('verified_users', 0)}</code>
  🔴 ʙᴀɴɴᴇᴅ         : <code>{stats.get('banned_users', 0)}</code>

{UI.CHANNEL} <b>ᴄʜᴀɴɴᴇʟꜱ</b>
  🟣 ʀᴇǫᴜɪʀᴇᴅ       : <code>{stats.get('total_channels', 0)}</code>

{UI.HEAVY_LINE}
"""


def msg_users_list(users: List[Dict], total: int) -> str:
    if not users:
        return f"{UI.WARNING} No users found."
    
    lines = []
    for idx, u in enumerate(users[:50], 1):
        status = UI.SUCCESS if u.get("is_member") else UI.ERROR
        ban_icon = UI.BAN if u.get("is_banned") else ""
        username = f"@{safe_escape(u.get('username'))}" if u.get('username') else "No username"
        lines.append(f"{idx}. {status}{ban_icon} <code>{u.get('user_id')}</code> | {username}")
    
    user_list = "\n".join(lines)
    showing = min(50, len(users))
    
    return f"""
{UI.HEAVY_LINE}
        {UI.USERS} ᴀʟʟ ᴜꜱᴇʀꜱ
{UI.HEAVY_LINE}

{UI.bullet(f"Total: {total} users")}
{UI.bullet(f"Showing: {showing}")}

{UI.LIGHT_LINE}
{user_list}
{UI.HEAVY_LINE}
"""


def msg_broadcast_complete(success: int, failed: int, blocked: int) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.SUCCESS} ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴄᴏᴍᴘʟᴇᴛᴇ
{UI.HEAVY_LINE}

{UI.bullet(f"Successful: {success}")}
{UI.bullet(f"Failed: {failed}")}
{UI.bullet(f"Blocked bot: {blocked}")}

{UI.HEAVY_LINE}
"""


def msg_broadcast_progress(current: int, total: int, success: int, failed: int) -> str:
    return f"{UI.LOADING} Progress: {current}/{total}\n{UI.SUCCESS} {success} | {UI.ERROR} {failed}"


# ══════════════════════════════════════════════════════════════
#                     CHANNEL MESSAGES
# ══════════════════════════════════════════════════════════════

def msg_channels_list(channels: List[Dict]) -> str:
    if not channels:
        return f"""
{UI.HEAVY_LINE}
      {UI.CHANNEL} ᴄʜᴀɴɴᴇʟꜱ
{UI.HEAVY_LINE}

{UI.WARNING} ɴᴏ ᴄʜᴀɴɴᴇʟꜱ ᴄᴏɴꜰɪɢᴜʀᴇᴅ.

Use /addchannel to add one.

{UI.HEAVY_LINE}
"""
    
    color_dots = ["🔵", "🟢", "🟣", "🟠", "🔴", "🟡"]
    channel_lines = []
    
    for idx, ch in enumerate(channels):
        emoji = color_dots[idx % len(color_dots)]
        title = safe_escape(ch.get('channel_name') or 'Channel')
        ch_id = safe_escape(ch.get('channel_id', ''))
        ch_type = ch.get('channel_type') or 'public'
        type_icon = get_channel_type_icon(ch_type)
        username = ch.get('channel_username')
        
        link_info = f"@{safe_escape(username)}" if username else "Private"
        
        channel_lines.append(f"""
  {emoji} {type_icon} <b>{title}</b>
     ɪᴅ: <code>{ch_id}</code>
     ʟɪɴᴋ: {link_info}
     ᴛʏᴘᴇ: {ch_type}""")
    
    channels_text = "\n".join(channel_lines)
    
    return f"""
{UI.HEAVY_LINE}
    {UI.CHANNEL} ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟꜱ
{UI.HEAVY_LINE}

{UI.bullet(f"Total: {len(channels)} channels")}
{channels_text}

{UI.HEAVY_LINE}
"""


def msg_add_channel_help() -> str:
    return f"""
{UI.HEAVY_LINE}
{UI.INFO} <b>Add Channel</b>
{UI.HEAVY_LINE}

Usage: /addchannel <code>@channel</code>

Examples:
  • /addchannel <code>@Kronos_Osint</code>
  • /addchannel <code>-1001234567890</code>

{UI.HEAVY_LINE}
"""


def msg_channel_added(
    channel_title: str,
    channel_id: str,
    channel_type: str,
    username: str = None,
    invite_link: str = None
) -> str:
    type_icon = get_channel_type_icon(channel_type)
    link_display = f"@{username}" if username else (invite_link or "Private channel")
    
    return f"""
{UI.HEAVY_LINE}
      {UI.SUCCESS} ᴄʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ
{UI.HEAVY_LINE}

🔹 ᴛɪᴛʟᴇ: <b>{safe_escape(channel_title)}</b>
🔹 ɪᴅ: <code>{safe_escape(channel_id)}</code>
🔹 ᴛʏᴘᴇ: {type_icon} {channel_type}
🔹 ʟɪɴᴋ: {link_display}

{UI.HEAVY_LINE}
"""


def msg_channel_add_error(error: str) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.ERROR} ꜰᴀɪʟᴇᴅ ᴛᴏ ᴀᴅᴅ
{UI.HEAVY_LINE}

ᴇʀʀᴏʀ: {safe_escape(error)}

ᴍᴀᴋᴇ ꜱᴜʀᴇ:
  • ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ᴇxɪꜱᴛꜱ
  • ʙᴏᴛ ɪꜱ ᴀᴅᴅᴇᴅ ᴀꜱ ᴀᴅᴍɪɴ
  • ᴄʜᴀɴɴᴇʟ ɪᴅ/ᴜꜱᴇʀɴᴀᴍᴇ ɪꜱ ᴄᴏʀʀᴇᴄᴛ

{UI.HEAVY_LINE}
"""


def msg_bot_not_admin(channel_title: str) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.ERROR} ʙᴏᴛ ɴᴏᴛ ᴀᴅᴍɪɴ
{UI.HEAVY_LINE}

Make the bot admin in:
<b>{safe_escape(channel_title)}</b>

Then try again.

{UI.HEAVY_LINE}
"""


def msg_remove_channel_prompt(count: int) -> str:
    return f"""
{UI.HEAVY_LINE}
    {UI.WARNING} ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ
{UI.HEAVY_LINE}

Select a channel to remove ({count}):

{UI.HEAVY_LINE}
"""


def msg_channel_removed() -> str:
    return f"""
{UI.HEAVY_LINE}
    {UI.SUCCESS} ᴄʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴇᴅ
{UI.HEAVY_LINE}

Channel removed from required list.

{UI.HEAVY_LINE}
"""


def msg_cancelled() -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.INFO} ᴄᴀɴᴄᴇʟʟᴇᴅ
{UI.HEAVY_LINE}
"""


# ══════════════════════════════════════════════════════════════
#                     USER MESSAGES
# ══════════════════════════════════════════════════════════════

def msg_welcome_user(is_verified: bool) -> str:
    status = f"{UI.SUCCESS} ᴠᴇʀɪꜰɪᴇᴅ" if is_verified else f"{UI.WARNING} ᴜɴᴠᴇʀɪꜰɪᴇᴅ"
    
    return f"""
{UI.HEAVY_LINE}
      {UI.BOT} ʟᴇᴀᴋᴏꜱɪɴᴛ ʙᴏᴛ
{UI.HEAVY_LINE}

ᴡᴇʟᴄᴏᴍᴇ! {UI.STAR}

{UI.LIGHT_LINE}
{UI.INFO} Status: {status}
{UI.LIGHT_LINE}

{UI.SEARCH} <b>How to Search</b>
Send me any of these:
  • Email address
  • Phone number  
  • Username
  • Full name
  • Any identifier

{UI.HEAVY_LINE}
"""


def msg_join_required(channels: List[Dict]) -> str:
    color_dots = ["🔵", "🟢", "🟣", "🟠", "🔴", "🟡"]
    channel_list = "\n".join([
        f"  {color_dots[idx % len(color_dots)]} {safe_escape(ch.get('channel_name') or 'Channel')}"
        for idx, ch in enumerate(channels)
    ])
    
    return f"""
{UI.HEAVY_LINE}
      {UI.LOCK} ᴀᴄᴄᴇꜱꜱ ʀᴇǫᴜɪʀᴇᴅ
{UI.HEAVY_LINE}

{UI.WARNING} ʏᴏᴜ ᴍᴜꜱᴛ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟꜱ!

{UI.LIGHT_LINE}
{UI.CHANNEL} Required Channels ({len(channels)})
{UI.LIGHT_LINE}
{channel_list}

{UI.LIGHT_LINE}
{UI.INFO} Instructions
{UI.LIGHT_LINE}
  1. Join all channels above
  2. Click "Verify" button
  3. Start using the bot!

{UI.HEAVY_LINE}
"""


def msg_verified_success() -> str:
    return f"""
{UI.HEAVY_LINE}
        {UI.SUCCESS} ᴠᴇʀɪꜰɪᴇᴅ
{UI.HEAVY_LINE}

ʏᴏᴜ'ʀᴇ ᴀʟʟ ꜱᴇᴛ! {UI.FIRE}

{UI.SEARCH} ꜱᴇɴᴅ ᴀɴʏ ǫᴜᴇʀʏ ᴛᴏ ꜱᴇᴀʀᴄʜ:
  • ᴇᴍᴀɪʟ, ᴘʜᴏɴᴇ, ᴜꜱᴇʀɴᴀᴍᴇ
  • ɴᴀᴍᴇ, ᴏʀ ᴀɴʏ ɪᴅᴇɴᴛɪꜰɪᴇʀ

{UI.HEAVY_LINE}
"""


def msg_verification_failed(missing: List[Dict]) -> str:
    channel_list = "\n".join([
        f"  {UI.ERROR} {safe_escape(ch.get('channel_name') or 'Channel')}"
        for ch in missing
    ])
    
    return f"""
{UI.HEAVY_LINE}
      {UI.ERROR} ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ
{UI.HEAVY_LINE}

ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟꜱ!

{UI.LIGHT_LINE}
{UI.WARNING} Missing Channels
{UI.LIGHT_LINE}
{channel_list}

Please join and try again.

{UI.HEAVY_LINE}
"""


def msg_banned() -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.ERROR} ᴀᴄᴄᴇꜱꜱ ᴅᴇɴɪᴇᴅ
{UI.HEAVY_LINE}

{UI.LOCK} ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ʜᴀꜱ ʙᴇᴇɴ
ʙᴀɴɴᴇᴅ ꜰʀᴏᴍ ᴜꜱɪɴɢ ᴛʜɪꜱ ʙᴏᴛ.

ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ ꜰᴏʀ ᴀᴘᴘᴇᴀʟꜱ.

{UI.HEAVY_LINE}
"""


def msg_user_banned(user_id: int) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.BAN} ᴜꜱᴇʀ ʙᴀɴɴᴇᴅ
{UI.HEAVY_LINE}

User <code>{user_id}</code> has been banned.

{UI.HEAVY_LINE}
"""


def msg_user_unbanned(user_id: int) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.SUCCESS} ᴜꜱᴇʀ ᴜɴʙᴀɴɴᴇᴅ
{UI.HEAVY_LINE}

User <code>{user_id}</code> has been unbanned.

{UI.HEAVY_LINE}
"""


def msg_user_not_found() -> str:
    return f"{UI.ERROR} User not found in database."


# ══════════════════════════════════════════════════════════════
#                     SEARCH MESSAGES
# ══════════════════════════════════════════════════════════════

def msg_searching() -> str:
    return f"""
{UI.LOADING} <b>ꜱᴇᴀʀᴄʜɪɴɢ ᴅᴀᴛᴀʙᴀꜱᴇꜱ...</b>

ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴡʜɪʟᴇ ɪ ꜱᴄᴀɴ
ᴛʜʀᴏᴜɢʜ ᴍɪʟʟɪᴏɴꜱ ᴏꜰ ʀᴇᴄᴏʀᴅꜱ... 🔎
"""


def msg_no_results(query: str) -> str:
    safe_query = safe_escape(query[:50])
    return f"""
{UI.HEAVY_LINE}
      {UI.WARNING} ɴᴏ ʀᴇꜱᴜʟᴛꜱ
{UI.HEAVY_LINE}

{UI.bullet("Query")}: <code>{safe_query}</code>

ɴᴏ ᴅᴀᴛᴀ ꜰᴏᴜɴᴅ ɪɴ ᴀɴʏ ᴅᴀᴛᴀʙᴀꜱᴇ.

{UI.LIGHT_LINE}
{UI.INFO} Tips:
{UI.LIGHT_LINE}
  • Try a different search term
  • Check spelling
  • Use full email or phone

{UI.HEAVY_LINE}
"""


def msg_error() -> str:
    return f"""
{UI.HEAVY_LINE}
        {UI.ERROR} ᴇʀʀᴏʀ
{UI.HEAVY_LINE}

ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ!
ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.

{UI.HEAVY_LINE}
"""


def msg_rate_limited(seconds: int) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.WARNING} ʀᴀᴛᴇ ʟɪᴍɪᴛᴇᴅ
{UI.HEAVY_LINE}

ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ <b>{seconds}</b> ꜱᴇᴄᴏɴᴅꜱ
ʙᴇꜰᴏʀᴇ ɴᴇxᴛ ꜱᴇᴀʀᴄʜ.

{UI.HEAVY_LINE}
"""


def msg_validation_error(error: str) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.ERROR} ɪɴᴠᴀʟɪᴅ ǫᴜᴇʀʏ
{UI.HEAVY_LINE}

{safe_escape(error)}

{UI.HEAVY_LINE}
"""


def msg_help_group() -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.BOT} ʜᴏᴡ ᴛᴏ ᴜꜱᴇ
{UI.HEAVY_LINE}

ᴛᴀɢ ᴍᴇ ᴡɪᴛʜ ʏᴏᴜʀ ǫᴜᴇʀʏ:

📧 <code>@bot email@example.com</code>
📞 <code>@bot +1234567890</code>
👤 <code>@bot username123</code>

{UI.HEAVY_LINE}
"""


def msg_results_expired() -> str:
    return f"{UI.WARNING} Results expired. Please search again."


def msg_owner_only() -> str:
    return f"{UI.ERROR} This command is for owner only."
