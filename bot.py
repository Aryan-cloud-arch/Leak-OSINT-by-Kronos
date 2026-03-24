import os
import requests
from random import randint
from datetime import datetime
from supabase import create_client, Client

try:
    import telebot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
except ModuleNotFoundError:
    print("Missing required library. Run: pip install pyTelegramBotAPI")
    exit()

# ══════════════════════════════════════════════════════════════
#                        CONFIGURATION
# ══════════════════════════════════════════════════════════════

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_TOKEN = os.environ.get("API_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# LeakOSINT API Config
API_URL = "https://leakosintapi.com/"
LANG = os.environ.get("LANG", "en")
LIMIT = int(os.environ.get("LIMIT", "300"))

# Initial channels from env (comma-separated)
INITIAL_CHANNELS = os.environ.get("REQUIRED_CHANNELS", "").split(",")
INITIAL_CHANNELS = [ch.strip() for ch in INITIAL_CHANNELS if ch.strip()]

# Bot info (fetched on startup)
BOT_USERNAME = None
BOT_NAME = None

# ══════════════════════════════════════════════════════════════
#                     DESIGN ELEMENTS
# ══════════════════════════════════════════════════════════════

class UI:
    """Clean UI elements for consistent design"""
    
    # Lines
    HEAVY_LINE = "━━━━━━━━━━━━━━━━━━━━━━"
    LIGHT_LINE = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
    DOUBLE_LINE = "══════════════════════"
    DOT_LINE = "• • • • • • • • • • • •"
    SPARKLE_LINE = "✦ ━━━━━━━━━━━━━━━━ ✦"
    
    # Small caps alphabet mapping
    SMALL_CAPS = str.maketrans(
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ'
    )
    
    @staticmethod
    def small_caps(text: str) -> str:
        """Convert text to small caps"""
        return text.translate(UI.SMALL_CAPS)
    
    # Corners & Borders
    TOP_LEFT = "┏"
    TOP_RIGHT = "┓"
    BOT_LEFT = "┗"
    BOT_RIGHT = "┛"
    VERT = "┃"
    
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
    
    @staticmethod
    def header(title: str, emoji: str = ""):
        """Create a styled header"""
        return f"""
{UI.HEAVY_LINE}
        {emoji} {title}
{UI.HEAVY_LINE}"""

    @staticmethod
    def section(title: str, emoji: str = ""):
        """Create a section header"""
        return f"""
{UI.LIGHT_LINE}
{emoji} {title}
{UI.LIGHT_LINE}"""

    @staticmethod
    def mini_section(title: str, emoji: str = ""):
        """Create a mini section"""
        return f"\n{emoji} <b>{title}</b>"

    @staticmethod
    def footer():
        """Create a footer line"""
        return f"\n{UI.HEAVY_LINE}"

    @staticmethod
    def item(label: str, value: str, indent: int = 0):
        """Create a formatted item"""
        spaces = "  " * indent
        return f"{spaces}• {label}: {value}"

    @staticmethod
    def bullet(text: str, indent: int = 0):
        """Create a bullet point"""
        spaces = "  " * indent
        return f"{spaces}• {text}"

    @staticmethod
    def numbered(num: int, text: str):
        """Create a numbered item"""
        return f"{num}. {text}"


# ══════════════════════════════════════════════════════════════
#                      VALIDATION
# ══════════════════════════════════════════════════════════════

if not all([BOT_TOKEN, API_TOKEN, OWNER_ID, SUPABASE_URL, SUPABASE_KEY]):
    print(f"""
{UI.HEAVY_LINE}
{UI.ERROR} CONFIGURATION ERROR
{UI.HEAVY_LINE}

Missing required environment variables:

{UI.bullet("BOT_TOKEN")}     : {'✓' if BOT_TOKEN else '✗ Missing'}
{UI.bullet("API_TOKEN")}     : {'✓' if API_TOKEN else '✗ Missing'}
{UI.bullet("OWNER_ID")}      : {'✓' if OWNER_ID else '✗ Missing'}
{UI.bullet("SUPABASE_URL")}  : {'✓' if SUPABASE_URL else '✗ Missing'}
{UI.bullet("SUPABASE_KEY")}  : {'✓' if SUPABASE_KEY else '✗ Missing'}

{UI.HEAVY_LINE}
""")
    exit(1)

# ══════════════════════════════════════════════════════════════
#                     SUPABASE CLIENT
# ══════════════════════════════════════════════════════════════

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ══════════════════════════════════════════════════════════════
#                   DATABASE FUNCTIONS
# ══════════════════════════════════════════════════════════════

def db_add_user(user_id: int, username: str = None, first_name: str = None):
    """Add or update user in database"""
    try:
        data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "is_verified": False,
            "last_seen": datetime.now().isoformat()
        }
        supabase.table("users").upsert(data, on_conflict="user_id").execute()
        return True
    except Exception as e:
        print(f"DB Error (add_user): {e}")
        return False

def db_get_user(user_id: int):
    """Get user from database"""
    try:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"DB Error (get_user): {e}")
        return None

def db_set_verified(user_id: int, verified: bool):
    """Set user verification status"""
    try:
        supabase.table("users").update({
            "is_verified": verified,
            "last_seen": datetime.now().isoformat()
        }).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"DB Error (set_verified): {e}")
        return False

def db_get_all_users():
    """Get all users"""
    try:
        result = supabase.table("users").select("*").execute()
        return result.data
    except Exception as e:
        print(f"DB Error (get_all_users): {e}")
        return []

def db_get_channels():
    """Get all required channels"""
    try:
        result = supabase.table("channels").select("*").eq("is_active", True).execute()
        return result.data
    except Exception as e:
        print(f"DB Error (get_channels): {e}")
        return []

def db_add_channel(channel_id: str, channel_title: str, channel_type: str = "public"):
    """Add a required channel"""
    try:
        data = {
            "channel_id": channel_id,
            "channel_title": channel_title,
            "channel_type": channel_type,
            "is_active": True,
            "added_at": datetime.now().isoformat()
        }
        supabase.table("channels").upsert(data, on_conflict="channel_id").execute()
        return True
    except Exception as e:
        print(f"DB Error (add_channel): {e}")
        return False

def db_remove_channel(channel_id: str):
    """Remove a channel"""
    try:
        supabase.table("channels").delete().eq("channel_id", channel_id).execute()
        return True
    except Exception as e:
        print(f"DB Error (remove_channel): {e}")
        return False

def db_get_stats():
    """Get bot statistics"""
    try:
        users = supabase.table("users").select("*", count="exact").execute()
        verified = supabase.table("users").select("*", count="exact").eq("is_verified", True).execute()
        channels = supabase.table("channels").select("*", count="exact").eq("is_active", True).execute()
        
        return {
            "total_users": users.count or 0,
            "verified_users": verified.count or 0,
            "total_channels": channels.count or 0
        }
    except Exception as e:
        print(f"DB Error (get_stats): {e}")
        return {"total_users": 0, "verified_users": 0, "total_channels": 0}

def db_log_search(user_id: int, query: str, results_count: int):
    """Log a search query"""
    try:
        data = {
            "user_id": user_id,
            "query": query[:500],
            "results_count": results_count,
            "searched_at": datetime.now().isoformat()
        }
        supabase.table("search_logs").insert(data).execute()
        return True
    except Exception as e:
        print(f"DB Error (log_search): {e}")
        return False

# ══════════════════════════════════════════════════════════════
#                    BOT INITIALIZATION
# ══════════════════════════════════════════════════════════════

bot = telebot.TeleBot(BOT_TOKEN)

def init_bot():
    """Initialize bot and fetch bot info"""
    global BOT_USERNAME, BOT_NAME
    try:
        bot_info = bot.get_me()
        BOT_USERNAME = bot_info.username
        BOT_NAME = bot_info.first_name
        print(f"""
{UI.HEAVY_LINE}
        {UI.BOT} BOT INITIALIZED
{UI.HEAVY_LINE}

{UI.bullet("Bot Name")}     : {BOT_NAME}
{UI.bullet("Username")}     : @{BOT_USERNAME}
{UI.bullet("Owner ID")}     : {OWNER_ID}
{UI.bullet("API")}          : LeakOSINT
{UI.bullet("Database")}     : Supabase

{UI.HEAVY_LINE}
{UI.SUCCESS} Bot is running!
{UI.HEAVY_LINE}
""")
    except Exception as e:
        print(f"{UI.ERROR} Failed to initialize bot: {e}")
        exit(1)

def init_channels():
    """Initialize channels from environment variable"""
    for channel in INITIAL_CHANNELS:
        if channel:
            try:
                chat = bot.get_chat(channel)
                db_add_channel(str(chat.id), chat.title or channel, "public")
                print(f"{UI.SUCCESS} Added initial channel: {chat.title or channel}")
            except Exception as e:
                print(f"{UI.WARNING} Could not add channel {channel}: {e}")

# ══════════════════════════════════════════════════════════════
#                  MEMBERSHIP VERIFICATION
# ══════════════════════════════════════════════════════════════

def check_user_membership(user_id: int) -> dict:
    """Check if user is member of all required channels"""
    channels = db_get_channels()
    
    if not channels:
        return {"is_member": True, "missing_channels": [], "channels": []}
    
    missing = []
    channel_info = []
    
    for channel in channels:
        channel_id = channel["channel_id"]
        try:
            member = bot.get_chat_member(channel_id, user_id)
            status = member.status
            
            is_member = status in ["member", "administrator", "creator"]
            
            # Handle join request channels
            if not is_member and status == "restricted":
                is_member = member.is_member if hasattr(member, 'is_member') else False
            
            channel_info.append({
                "id": channel_id,
                "title": channel["channel_title"],
                "type": channel["channel_type"],
                "is_member": is_member
            })
            
            if not is_member:
                missing.append(channel)
                
        except Exception as e:
            print(f"Membership check error for {channel_id}: {e}")
            missing.append(channel)
            channel_info.append({
                "id": channel_id,
                "title": channel["channel_title"],
                "type": channel["channel_type"],
                "is_member": False
            })
    
    return {
        "is_member": len(missing) == 0,
        "missing_channels": missing,
        "channels": channel_info
    }

def create_join_markup(channels: list, include_verify: bool = True) -> InlineKeyboardMarkup:
    """Create join channels keyboard with colorful design"""
    markup = InlineKeyboardMarkup()
    
    # Colorful circle emojis for visual variety
    color_emojis = ["🔵", "🟢", "🟣", "🟠", "🔴", "🟡", "⚪", "🟤"]
    
    for idx, channel in enumerate(channels):
        channel_id = channel["channel_id"]
        title = channel["channel_title"]
        emoji = color_emojis[idx % len(color_emojis)]
        
        if channel_id.startswith("-100"):
            url = f"https://t.me/c/{channel_id[4:]}"
        elif channel_id.startswith("@"):
            url = f"https://t.me/{channel_id[1:]}"
        else:
            try:
                chat = bot.get_chat(channel_id)
                if chat.username:
                    url = f"https://t.me/{chat.username}"
                else:
                    invite = bot.export_chat_invite_link(channel_id)
                    url = invite
            except:
                url = f"https://t.me/{channel_id}"
        
        markup.add(InlineKeyboardButton(
            text=f"{emoji} ᴊᴏɪɴ {title.upper()} →",
            url=url
        ))
    
    if include_verify:
        markup.add(InlineKeyboardButton(
            text="✅ ᴄʜᴇᴄᴋ ᴍᴇᴍʙᴇʀꜱʜɪᴘ ✅",
            callback_data="verify_join"
        ))
    
    return markup

# ══════════════════════════════════════════════════════════════
#                      HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_group_chat(message) -> bool:
    return message.chat.type in ["group", "supergroup"]

def get_user_mention(user) -> str:
    """Get user mention string"""
    if user.username:
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

# ══════════════════════════════════════════════════════════════
#                    REPORT GENERATION
# ══════════════════════════════════════════════════════════════

cash_reports = {}

def categorize_data(data_list: list) -> dict:
    """Categorize data fields intelligently"""
    categories = {
        "identity": [],
        "contact": [],
        "address": [],
        "account": [],
        "financial": [],
        "other": []
    }
    
    identity_fields = ["name", "fname", "lname", "firstname", "lastname", "fullname", 
                       "username", "login", "dob", "birth", "age", "gender", "sex"]
    contact_fields = ["phone", "mobile", "email", "mail", "tel", "cell"]
    address_fields = ["address", "city", "state", "country", "zip", "postal", "street", "house"]
    account_fields = ["password", "pass", "hash", "token", "ip", "useragent", "user_agent"]
    financial_fields = ["card", "cvv", "bank", "account", "iban", "swift", "payment"]
    
    for item in data_list:
        for key, value in item.items():
            key_lower = key.lower()
            entry = (key, value)
            
            if any(f in key_lower for f in identity_fields):
                categories["identity"].append(entry)
            elif any(f in key_lower for f in contact_fields):
                categories["contact"].append(entry)
            elif any(f in key_lower for f in address_fields):
                categories["address"].append(entry)
            elif any(f in key_lower for f in account_fields):
                categories["account"].append(entry)
            elif any(f in key_lower for f in financial_fields):
                categories["financial"].append(entry)
            else:
                categories["other"].append(entry)
    
    return categories

def format_report_page(database_name: str, data: list, info_leak: str) -> str:
    """Format a single report page with clean UI"""
    
    # Header
    text = f"""
{UI.HEAVY_LINE}
      {UI.DATABASE} ᴅᴀᴛᴀʙᴀꜱᴇ ʀᴇꜱᴜʟᴛꜱ
{UI.HEAVY_LINE}

🔹 ꜱᴏᴜʀᴄᴇ: <b>{database_name}</b>
🔹 ɪɴꜰᴏ: {info_leak}
"""
    
    if database_name == "No results found":
        text += f"""
{UI.LIGHT_LINE}
{UI.WARNING} ɴᴏ ᴅᴀᴛᴀ ꜰᴏᴜɴᴅ ꜰᴏʀ ᴛʜɪꜱ ǫᴜᴇʀʏ
{UI.LIGHT_LINE}
"""
        return text
    
    # Process data entries
    for idx, entry in enumerate(data):
        if idx > 0:
            text += f"\n{UI.DOT_LINE}\n"
        
        categories = categorize_data([entry])
        
        # Identity Section
        if categories["identity"]:
            text += f"\n{UI.USER} <b>ɪᴅᴇɴᴛɪᴛʏ</b>\n"
            for key, value in categories["identity"]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        # Contact Section
        if categories["contact"]:
            text += f"\n{UI.PHONE} <b>ᴄᴏɴᴛᴀᴄᴛ</b>\n"
            for key, value in categories["contact"]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        # Address Section  
        if categories["address"]:
            text += f"\n{UI.HOME} <b>ᴀᴅᴅʀᴇꜱꜱ</b>\n"
            for key, value in categories["address"]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        # Account Section
        if categories["account"]:
            text += f"\n{UI.KEY} <b>ᴀᴄᴄᴏᴜɴᴛ</b>\n"
            for key, value in categories["account"]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        # Financial Section
        if categories["financial"]:
            text += f"\n{UI.CARD} <b>ꜰɪɴᴀɴᴄɪᴀʟ</b>\n"
            for key, value in categories["financial"]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        # Other Section
        if categories["other"]:
            text += f"\n{UI.GLOBE} <b>ᴏᴛʜᴇʀ</b>\n"
            for key, value in categories["other"]:
                text += f"  • {key}: <code>{value}</code>\n"
    
    text += f"\n{UI.HEAVY_LINE}"
    
    # Truncate if too long
    if len(text) > 3800:
        text = text[:3800] + f"\n\n{UI.WARNING} <i>Some data truncated...</i>"
    
    return text

def generate_report(query: str, query_id: int) -> list:
    """Generate OSINT report"""
    global cash_reports
    
    data = {
        "token": API_TOKEN,
        "request": query.split("\n")[0],
        "limit": LIMIT,
        "lang": LANG
    }
    
    try:
        response = requests.post(API_URL, json=data, timeout=30).json()
    except Exception as e:
        print(f"API Error: {e}")
        return None
    
    if "Error code" in response:
        print(f"API Error: {response['Error code']}")
        return None
    
    cash_reports[str(query_id)] = []
    total_results = 0
    
    for database_name in response["List"].keys():
        info_leak = response["List"][database_name].get("InfoLeak", "")
        data_list = response["List"][database_name].get("Data", [])
        total_results += len(data_list)
        
        formatted = format_report_page(database_name, data_list, info_leak)
        cash_reports[str(query_id)].append(formatted)
    
    return cash_reports[str(query_id)], total_results

def create_pagination_keyboard(query_id: int, page_id: int, total_pages: int) -> InlineKeyboardMarkup:
    """Create pagination keyboard with colorful design"""
    markup = InlineKeyboardMarkup()
    
    if total_pages <= 1:
        return markup
    
    # Normalize page_id
    if page_id < 0:
        page_id = total_pages - 1
    elif page_id >= total_pages:
        page_id = 0
    
    markup.row(
        InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"page_{query_id}_{page_id-1}"),
        InlineKeyboardButton(f"📑 {page_id+1}/{total_pages}", callback_data="current_page"),
        InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"page_{query_id}_{page_id+1}")
    )
    
    # Add jump buttons for many pages
    if total_pages > 5:
        markup.row(
            InlineKeyboardButton("⏮️ ꜰɪʀꜱᴛ", callback_data=f"page_{query_id}_0"),
            InlineKeyboardButton("⏭️ ʟᴀꜱᴛ", callback_data=f"page_{query_id}_{total_pages-1}")
        )
    
    return markup

# ══════════════════════════════════════════════════════════════
#                     MESSAGE TEMPLATES
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
• /removechannel
• /channels

{UI.LIGHT_LINE}
{UI.USERS} User Management  
{UI.LIGHT_LINE}
• /users - All users
• /stats - Bot statistics
• /broadcast <code>message</code>

{UI.LIGHT_LINE}
{UI.SEARCH} Search
{UI.LIGHT_LINE}
Just send any query to search!

{UI.HEAVY_LINE}
"""

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

{UI.LIGHT_LINE}
{UI.CHANNEL} Group Usage
{UI.LIGHT_LINE}
Tag me: <code>@{BOT_USERNAME} query</code>

{UI.HEAVY_LINE}
"""

def msg_join_required(channels: list) -> str:
    color_dots = ["🔵", "🟢", "🟣", "🟠", "🔴", "🟡"]
    channel_list = "\n".join([f"  {color_dots[idx % len(color_dots)]} {ch['channel_title']}" for idx, ch in enumerate(channels)])
    
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

def msg_verification_failed(missing: list) -> str:
    channel_list = "\n".join([f"  {UI.ERROR} {ch['channel_title']}" for ch in missing])
    
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

def msg_searching() -> str:
    return f"""
{UI.LOADING} <b>ꜱᴇᴀʀᴄʜɪɴɢ ᴅᴀᴛᴀʙᴀꜱᴇꜱ...</b>

ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴡʜɪʟᴇ ɪ ꜱᴄᴀɴ ᴛʜʀᴏᴜɢʜ
ᴍɪʟʟɪᴏɴꜱ ᴏꜰ ʀᴇᴄᴏʀᴅꜱ... 🔎
"""

def msg_no_results(query: str) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.WARNING} ɴᴏ ʀᴇꜱᴜʟᴛꜱ
{UI.HEAVY_LINE}

{UI.bullet("Query")}: <code>{query[:50]}</code>

ɴᴏ ᴅᴀᴛᴀ ꜰᴏᴜɴᴅ ɪɴ ᴀɴʏ ᴅᴀᴛᴀʙᴀꜱᴇ.
ᴛʀʏ ᴀ ᴅɪꜰꜰᴇʀᴇɴᴛ ǫᴜᴇʀʏ ꜰᴏʀᴍᴀᴛ.

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

def msg_channels_list(channels: list) -> str:
    if not channels:
        return f"""
{UI.HEAVY_LINE}
      {UI.CHANNEL} ᴄʜᴀɴɴᴇʟꜱ
{UI.HEAVY_LINE}

{UI.WARNING} ɴᴏ ᴄʜᴀɴɴᴇʟꜱ ᴄᴏɴꜰɪɢᴜʀᴇᴅ.

ᴜꜱᴇ /addchannel ᴛᴏ ᴀᴅᴅ ᴏɴᴇ.

{UI.HEAVY_LINE}
"""
    
    color_dots = ["🔵", "🟢", "🟣", "🟠", "🔴", "🟡"]
    channel_list = ""
    for idx, ch in enumerate(channels):
        emoji = color_dots[idx % len(color_dots)]
        channel_list += f"""
  {emoji} <b>{ch['channel_title']}</b>
     ɪᴅ: <code>{ch['channel_id']}</code>
     ᴛʏᴘᴇ: {ch['channel_type']}
"""
    
    return f"""
{UI.HEAVY_LINE}
    {UI.CHANNEL} ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟꜱ
{UI.HEAVY_LINE}

{UI.bullet("Total")}: {len(channels)} ᴄʜᴀɴɴᴇʟꜱ
{channel_list}
{UI.HEAVY_LINE}
"""

def msg_stats(stats: dict) -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.STATS} ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ
{UI.HEAVY_LINE}

{UI.USERS} <b>ᴜꜱᴇʀꜱ</b>
  🟢 ᴛᴏᴛᴀʟ ᴜꜱᴇʀꜱ    : <code>{stats['total_users']}</code>
  🔵 ᴠᴇʀɪꜰɪᴇᴅ       : <code>{stats['verified_users']}</code>
  🔴 ᴜɴᴠᴇʀɪꜰɪᴇᴅ     : <code>{stats['total_users'] - stats['verified_users']}</code>

{UI.CHANNEL} <b>ᴄʜᴀɴɴᴇʟꜱ</b>
  🟣 ʀᴇǫᴜɪʀᴇᴅ       : <code>{stats['total_channels']}</code>

{UI.HEAVY_LINE}
"""

def msg_help_group() -> str:
    return f"""
{UI.HEAVY_LINE}
      {UI.BOT} ʜᴏᴡ ᴛᴏ ᴜꜱᴇ
{UI.HEAVY_LINE}

ᴛᴀɢ ᴍᴇ ᴡɪᴛʜ ʏᴏᴜʀ ǫᴜᴇʀʏ:

📧 <code>@{BOT_USERNAME} email@example.com</code>
📞 <code>@{BOT_USERNAME} +1234567890</code>
👤 <code>@{BOT_USERNAME} username123</code>

{UI.HEAVY_LINE}
"""

# ══════════════════════════════════════════════════════════════
#                    COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    user_id = user.id
    
    # Save user to database
    db_add_user(user_id, user.username, user.first_name)
    
    # Owner gets special panel
    if is_owner(user_id):
        bot.reply_to(message, msg_welcome_owner(), parse_mode="HTML")
        return
    
    # Check channel membership
    membership = check_user_membership(user_id)
    
    if membership["is_member"]:
        db_set_verified(user_id, True)
        bot.reply_to(message, msg_welcome_user(True), parse_mode="HTML")
    else:
        db_set_verified(user_id, False)
        markup = create_join_markup(membership["missing_channels"])
        bot.reply_to(message, msg_join_required(membership["missing_channels"]), 
                    parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    if is_group_chat(message):
        bot.reply_to(message, msg_help_group(), parse_mode="HTML")
    else:
        bot.reply_to(message, msg_welcome_user(True), parse_mode="HTML")

@bot.message_handler(commands=["channels"])
def cmd_channels(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, f"{UI.ERROR} Owner only command.")
        return
    
    channels = db_get_channels()
    bot.reply_to(message, msg_channels_list(channels), parse_mode="HTML")

@bot.message_handler(commands=["addchannel"])
def cmd_add_channel(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, f"{UI.ERROR} Owner only command.")
        return
    
    try:
        channel_input = message.text.split(maxsplit=1)[1].strip()
    except IndexError:
        bot.reply_to(message, f"""
{UI.HEAVY_LINE}
{UI.INFO} <b>Add Channel</b>
{UI.HEAVY_LINE}

Usage: /addchannel <code>@channel</code>

Examples:
  • /addchannel @mychannel
  • /addchannel -1001234567890

{UI.HEAVY_LINE}
""", parse_mode="HTML")
        return
    
    try:
        chat = bot.get_chat(channel_input)
        channel_id = str(chat.id)
        channel_title = chat.title or channel_input
        channel_type = chat.type
        
        # Check if bot is admin
        try:
            bot_member = bot.get_chat_member(chat.id, bot.get_me().id)
            if bot_member.status not in ["administrator", "creator"]:
                bot.reply_to(message, f"""
{UI.ERROR} <b>Bot is not admin!</b>

Make the bot admin in <b>{channel_title}</b>
then try again.
""", parse_mode="HTML")
                return
        except:
            pass
        
        db_add_channel(channel_id, channel_title, channel_type)
        
        bot.reply_to(message, f"""
{UI.HEAVY_LINE}
      {UI.SUCCESS} ᴄʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ
{UI.HEAVY_LINE}

🔹 ᴛɪᴛʟᴇ: <b>{channel_title}</b>
🔹 ɪᴅ: <code>{channel_id}</code>
🔹 ᴛʏᴘᴇ: {channel_type}

{UI.HEAVY_LINE}
""", parse_mode="HTML")
        
    except Exception as e:
        bot.reply_to(message, f"""
{UI.HEAVY_LINE}
      {UI.ERROR} ꜰᴀɪʟᴇᴅ ᴛᴏ ᴀᴅᴅ
{UI.HEAVY_LINE}

ᴇʀʀᴏʀ: {str(e)}

ᴍᴀᴋᴇ ꜱᴜʀᴇ:
  • ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ᴇxɪꜱᴛꜱ
  • ʙᴏᴛ ɪꜱ ᴀᴅᴅᴇᴅ ᴀꜱ ᴀᴅᴍɪɴ
  • ᴄʜᴀɴɴᴇʟ ɪᴅ/ᴜꜱᴇʀɴᴀᴍᴇ ɪꜱ ᴄᴏʀʀᴇᴄᴛ
{UI.HEAVY_LINE}
""", parse_mode="HTML")

@bot.message_handler(commands=["removechannel"])
def cmd_remove_channel(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, f"{UI.ERROR} Owner only command.")
        return
    
    channels = db_get_channels()
    
    if not channels:
        bot.reply_to(message, f"{UI.WARNING} No channels to remove.")
        return
    
    markup = InlineKeyboardMarkup()
    for idx, ch in enumerate(channels):
        color_emojis = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
        emoji = color_emojis[idx % len(color_emojis)]
        markup.add(InlineKeyboardButton(
            f"{emoji} ʀᴇᴍᴏᴠᴇ {ch['channel_title']}",
            callback_data=f"rmch_{ch['channel_id']}"
        ))
    markup.add(InlineKeyboardButton("✖️ ᴄᴀɴᴄᴇʟ", callback_data="cancel_remove"))
    
    bot.reply_to(message, f"""
{UI.HEAVY_LINE}
    {UI.WARNING} ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ
{UI.HEAVY_LINE}

ꜱᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ʀᴇᴍᴏᴠᴇ:

{UI.HEAVY_LINE}
""", parse_mode="HTML", reply_markup=markup)

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, f"{UI.ERROR} Owner only command.")
        return
    
    stats = db_get_stats()
    bot.reply_to(message, msg_stats(stats), parse_mode="HTML")

@bot.message_handler(commands=["users"])
def cmd_users(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, f"{UI.ERROR} Owner only command.")
        return
    
    users = db_get_all_users()
    
    if not users:
        bot.reply_to(message, f"{UI.WARNING} No users yet.")
        return
    
    text = f"""
{UI.HEAVY_LINE}
        {UI.USERS} ALL USERS
{UI.HEAVY_LINE}

{UI.bullet("Total")}: {len(users)} users

{UI.LIGHT_LINE}
"""
    
    for idx, u in enumerate(users[:50], 1):  # Limit to 50
        status = UI.SUCCESS if u.get("is_verified") else UI.ERROR
        username = f"@{u['username']}" if u.get('username') else "No username"
        text += f"\n{idx}. {status} <code>{u['user_id']}</code>\n   {username}"
    
    if len(users) > 50:
        text += f"\n\n{UI.INFO} Showing first 50 users..."
    
    text += f"\n\n{UI.HEAVY_LINE}"
    
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, f"{UI.ERROR} Owner only command.")
        return
    
    try:
        broadcast_text = message.text.split(maxsplit=1)[1]
    except IndexError:
        bot.reply_to(message, f"""
{UI.INFO} Usage: /broadcast <code>message</code>
""", parse_mode="HTML")
        return
    
    users = db_get_all_users()
    success = 0
    failed = 0
    
    status_msg = bot.reply_to(message, f"{UI.LOADING} Broadcasting...")
    
    formatted_broadcast = f"""
{UI.HEAVY_LINE}
        {UI.CHANNEL} BROADCAST
{UI.HEAVY_LINE}

{broadcast_text}

{UI.HEAVY_LINE}
"""
    
    for user in users:
        try:
            bot.send_message(user["user_id"], formatted_broadcast, parse_mode="HTML")
            success += 1
        except:
            failed += 1
    
    bot.edit_message_text(f"""
{UI.HEAVY_LINE}
        {UI.SUCCESS} BROADCAST SENT
{UI.HEAVY_LINE}

{UI.bullet("Successful")}: {success}
{UI.bullet("Failed")}: {failed}

{UI.HEAVY_LINE}
""", status_msg.chat.id, status_msg.message_id, parse_mode="HTML")

# ══════════════════════════════════════════════════════════════
#                     SEARCH HANDLER
# ══════════════════════════════════════════════════════════════

def process_search(message, query: str):
    """Process a search query"""
    user = message.from_user
    user_id = user.id
    
    # Save/update user
    db_add_user(user_id, user.username, user.first_name)
    
    # Owner bypasses checks
    if not is_owner(user_id):
        # Check membership
        membership = check_user_membership(user_id)
        
        if not membership["is_member"]:
            db_set_verified(user_id, False)
            markup = create_join_markup(membership["missing_channels"])
            bot.reply_to(message, msg_join_required(membership["missing_channels"]),
                        parse_mode="HTML", reply_markup=markup)
            return
        else:
            db_set_verified(user_id, True)
    
    # Send searching message
    searching_msg = bot.reply_to(message, msg_searching(), parse_mode="HTML")
    
    # Generate report
    query_id = randint(100000, 9999999)
    result = generate_report(query, query_id)
    
    # Delete searching message
    try:
        bot.delete_message(message.chat.id, searching_msg.message_id)
    except:
        pass
    
    if result is None:
        bot.reply_to(message, msg_error(), parse_mode="HTML")
        return
    
    report, total_results = result
    
    if not report:
        bot.reply_to(message, msg_no_results(query), parse_mode="HTML")
        return
    
    # Log the search
    db_log_search(user_id, query, total_results)
    
    # Send first page
    markup = create_pagination_keyboard(query_id, 0, len(report))
    
    try:
        bot.reply_to(message, report[0], parse_mode="HTML", reply_markup=markup)
    except:
        # Fallback without HTML
        clean_text = report[0].replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace("<i>", "").replace("</i>", "")
        bot.reply_to(message, clean_text, reply_markup=markup)

# ══════════════════════════════════════════════════════════════
#                   GROUP MENTION HANDLER
# ══════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: is_group_chat(m) and m.text and f"@{BOT_USERNAME}" in m.text if BOT_USERNAME else False)
def handle_group_mention(message):
    """Handle bot mentions in groups"""
    text = message.text
    
    # Extract query after mention
    query = text.replace(f"@{BOT_USERNAME}", "").strip()
    
    if not query:
        bot.reply_to(message, msg_help_group(), parse_mode="HTML")
        return
    
    process_search(message, query)

# ══════════════════════════════════════════════════════════════
#                  PRIVATE MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: not is_group_chat(m) and m.content_type == "text")
def handle_private_message(message):
    """Handle private messages as search queries"""
    query = message.text.strip()
    
    if query.startswith("/"):
        return  # Ignore unhandled commands
    
    process_search(message, query)

# ══════════════════════════════════════════════════════════════
#                   CALLBACK HANDLERS
# ══════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: CallbackQuery):
    user_id = call.from_user.id
    data = call.data
    
    # Verify join
    if data == "verify_join":
        membership = check_user_membership(user_id)
        
        if membership["is_member"]:
            db_set_verified(user_id, True)
            bot.edit_message_text(
                msg_verified_success(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "✅ Verified successfully!")
        else:
            markup = create_join_markup(membership["missing_channels"])
            bot.edit_message_text(
                msg_verification_failed(membership["missing_channels"]),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, "❌ Please join all channels!", show_alert=True)
        return
    
    # Remove channel (owner only)
    if data.startswith("rmch_"):
        if not is_owner(user_id):
            bot.answer_callback_query(call.id, "❌ Owner only!", show_alert=True)
            return
        
        channel_id = data.replace("rmch_", "")
        db_remove_channel(channel_id)
        
        bot.edit_message_text(f"""
{UI.HEAVY_LINE}
    {UI.SUCCESS} ᴄʜᴀɴɴᴇʟ ʀᴇᴍᴏᴠᴇᴅ
{UI.HEAVY_LINE}

ᴄʜᴀɴɴᴇʟ ʜᴀꜱ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ
ᴛʜᴇ ʀᴇǫᴜɪʀᴇᴅ ᴄʜᴀɴɴᴇʟꜱ ʟɪꜱᴛ.

{UI.HEAVY_LINE}
""", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        bot.answer_callback_query(call.id, "✅ ʀᴇᴍᴏᴠᴇᴅ!")
        return
    
    # Cancel remove
    if data == "cancel_remove":
        bot.edit_message_text(f"""
{UI.HEAVY_LINE}
      {UI.INFO} ᴄᴀɴᴄᴇʟʟᴇᴅ
{UI.HEAVY_LINE}
""", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        bot.answer_callback_query(call.id)
        return
    
    # Page navigation
    if data.startswith("page_"):
        parts = data.split("_")
        query_id = parts[1]
        page_id = int(parts[2])
        
        if query_id not in cash_reports:
            bot.answer_callback_query(call.id, "⚠️ Results expired!", show_alert=True)
            return
        
        report = cash_reports[query_id]
        total_pages = len(report)
        
        # Normalize page
        if page_id < 0:
            page_id = total_pages - 1
        elif page_id >= total_pages:
            page_id = 0
        
        markup = create_pagination_keyboard(int(query_id), page_id, total_pages)
        
        try:
            bot.edit_message_text(
                report[page_id],
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
        except:
            clean_text = report[page_id].replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
            bot.edit_message_text(
                clean_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        
        bot.answer_callback_query(call.id)
        return
    
    # Current page (do nothing)
    if data == "current_page":
        bot.answer_callback_query(call.id)
        return

# ══════════════════════════════════════════════════════════════
#                        MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_bot()
    init_channels()
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"{UI.ERROR} Error: {e}")
            print(f"{UI.LOADING} Restarting in 5 seconds...")
            import time
            time.sleep(5)
