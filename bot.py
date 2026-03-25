#!/usr/bin/env python3
"""
bot.py — LeakOSINT Bot Main Module
Pro-Level:
  ✅ Case-insensitive bot mention matching
  ✅ Ban check on ALL message types
  ✅ Graceful startup with config validation
  ✅ Periodic cache cleanup thread
  ✅ Compatible with run.py debug runner
  ✅ Compatible with direct execution
"""
import time
import threading
from datetime import datetime

# ─── Core Imports ───
from core.config import config
from core.database import db_add_user, db_is_banned
from core.cache import (
    membership_cache,
    channel_cache,
    report_cache,
    cooldown_cache,
    rate_limit_cache,
    global_report_cache
)

# ─── Handler Imports ───
from handlers.commands import (
    cmd_start,
    cmd_help,
    cmd_channels,
    cmd_add_channel,
    cmd_remove_channel,
    cmd_stats,
    cmd_users,
    cmd_broadcast,
    cmd_ban,
    init_channels as _init_channels
)
from handlers.search import process_search
from handlers.callbacks import handle_callback
from handlers.ui import (
    UI,
    is_group_chat,
    msg_welcome_user,
    msg_banned,
    msg_help_group
)

# ─── Telebot ───
import telebot
from telebot.types import Message, CallbackQuery


# ══════════════════════════════════════════════════════════════
#                  BOT INSTANCE
# ══════════════════════════════════════════════════════════════

bot = telebot.TeleBot(config.BOT_TOKEN)

# Bot info (populated on init)
BOT_USERNAME = None
BOT_NAME = None


# ══════════════════════════════════════════════════════════════
#                  CACHE CLEANUP THREAD
# ══════════════════════════════════════════════════════════════

_cleanup_started = False


def _cache_cleanup_worker():
    """Background thread to clean expired cache entries every 5 minutes."""
    while True:
        time.sleep(300)  # 5 minutes
        try:
            m = membership_cache.cleanup_expired()
            c = channel_cache.cleanup_expired()
            r = report_cache.cleanup_expired()
            cd = cooldown_cache.cleanup_expired()
            rl = rate_limit_cache.cleanup_expired()
            
            # Also clean global report cache (remove old entries)
            now = time.time()
            expired_keys = []
            for key in list(global_report_cache.keys()):
                # Reports older than 30 min
                try:
                    report_entry = report_cache.get(f"report_{key}")
                    if report_entry is None:
                        expired_keys.append(key)
                except Exception:
                    pass
            
            for key in expired_keys:
                global_report_cache.pop(key, None)
            
            total = m + c + r + cd + rl + len(expired_keys)
            if total > 0:
                print(f"[Cache Cleanup] Cleared {total} expired entries")
        
        except Exception as e:
            print(f"[Cache Cleanup Error]: {e}")


def _start_cleanup_thread():
    """Start cache cleanup thread (only once)."""
    global _cleanup_started
    if not _cleanup_started:
        cleanup_thread = threading.Thread(target=_cache_cleanup_worker, daemon=True)
        cleanup_thread.start()
        _cleanup_started = True
        print(f"  {UI.SUCCESS} Cache cleanup thread started")


# ══════════════════════════════════════════════════════════════
#                  BOT INITIALIZATION
# ══════════════════════════════════════════════════════════════

def init_bot():
    """
    Initialize bot and fetch bot info.
    Called by run.py or directly.
    """
    global BOT_USERNAME, BOT_NAME
    
    try:
        bot_info = bot.get_me()
        BOT_USERNAME = bot_info.username
        BOT_NAME = bot_info.first_name
        
        print(f"""
{UI.HEAVY_LINE}
        {UI.BOT} BOT INITIALIZED
{UI.HEAVY_LINE}

  {UI.bullet(f"Bot Name     : {BOT_NAME}")}
  {UI.bullet(f"Username     : @{BOT_USERNAME}")}
  {UI.bullet(f"Owner ID     : {config.OWNER_ID}")}
  {UI.bullet(f"API          : LeakOSINT")}
  {UI.bullet(f"Database     : Supabase")}
  {UI.bullet(f"Rate Limit   : {config.SEARCH_LIMIT_PER_MINUTE}/min")}
  {UI.bullet(f"Cache TTL    : Ch={config.CHANNEL_CACHE_TTL}s Mem={config.MEMBERSHIP_CACHE_TTL}s")}

{UI.HEAVY_LINE}
""")
    except Exception as e:
        print(f"{UI.ERROR} Failed to initialize bot: {e}")
        raise


def init_channels():
    """
    Initialize channels from config.
    Wrapper for commands.init_channels(bot).
    Called by run.py or directly.
    """
    _init_channels(bot)


# ══════════════════════════════════════════════════════════════
#                  MESSAGE HANDLERS
# ══════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def handle_start(message: Message):
    cmd_start(message, bot)


@bot.message_handler(commands=["help"])
def handle_help(message: Message):
    cmd_help(message, bot)


@bot.message_handler(commands=["channels"])
def handle_channels(message: Message):
    cmd_channels(message, bot)


@bot.message_handler(commands=["addchannel"])
def handle_addchannel(message: Message):
    cmd_add_channel(message, bot)


@bot.message_handler(commands=["removechannel"])
def handle_removechannel(message: Message):
    cmd_remove_channel(message, bot)


@bot.message_handler(commands=["stats"])
def handle_stats(message: Message):
    cmd_stats(message, bot)


@bot.message_handler(commands=["users"])
def handle_users(message: Message):
    cmd_users(message, bot)


@bot.message_handler(commands=["broadcast"])
def handle_broadcast(message: Message):
    cmd_broadcast(message, bot)


@bot.message_handler(commands=["ban"])
def handle_ban(message: Message):
    cmd_ban(message, bot)


# ══════════════════════════════════════════════════════════════
#                  GROUP MENTION HANDLER
# ══════════════════════════════════════════════════════════════

@bot.message_handler(
    func=lambda m: (
        is_group_chat(m)
        and m.text
        and BOT_USERNAME
        and f"@{BOT_USERNAME.lower()}" in m.text.lower()
    )
)
def handle_group_mention(message: Message):
    """Handle bot mentions in groups. Case-insensitive matching."""
    
    if not BOT_USERNAME:
        return
    
    # Extract query (case-insensitive removal of mention)
    text = message.text
    text_lower = text.lower()
    mention_lower = f"@{BOT_USERNAME.lower()}"
    
    # Find and remove the mention
    idx = text_lower.find(mention_lower)
    if idx != -1:
        query = (text[:idx] + text[idx + len(mention_lower):]).strip()
    else:
        query = text.strip()
    
    if not query:
        bot.reply_to(message, msg_help_group(), parse_mode="HTML")
        return
    
    process_search(message, query, bot)


# ══════════════════════════════════════════════════════════════
#                  PRIVATE MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════

@bot.message_handler(
    func=lambda m: (
        not is_group_chat(m)
        and m.content_type == "text"
    )
)
def handle_private_message(message: Message):
    """Handle private messages as search queries."""
    
    # Ignore commands (already handled above)
    if message.text and message.text.strip().startswith("/"):
        return
    
    query = message.text.strip() if message.text else ""
    
    if not query:
        return
    
    process_search(message, query, bot)


# ══════════════════════════════════════════════════════════════
#                  CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call: CallbackQuery):
    handle_callback(call, bot)


# ══════════════════════════════════════════════════════════════
#                  DIRECT EXECUTION
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Initialize
    init_bot()
    init_channels()
    
    # Start cache cleanup
    _start_cleanup_thread()
    
    print(f"""
{UI.HEAVY_LINE}
  {UI.SUCCESS} Bot is running! Press Ctrl+C to stop.
{UI.HEAVY_LINE}
""")
    
    # Polling loop with auto-restart
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except KeyboardInterrupt:
            print(f"\n{UI.WARNING} Bot stopped by user (Ctrl+C)")
            break
        except Exception as e:
            print(f"{UI.ERROR} Polling error: {e}")
            print(f"{UI.LOADING} Restarting in 10 seconds...")
            time.sleep(10)
