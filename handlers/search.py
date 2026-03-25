"""
handlers/search.py — Search Processing with All Fixes
Pro-Level:
  ✅ Rate limiting per user
  ✅ HTML escaping on ALL API data
  ✅ Safe HTML truncation (no broken tags)
  ✅ Cache cleanup
  ✅ Cooldown management
  ✅ Ban-aware
  ✅ Response time tracking
  ✅ Input validation
"""
import html
import time
import re
from typing import Tuple, List, Optional, Dict, Any
from random import randint

import requests
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.config import config
from core.database import db_add_user, db_log_search, db_is_banned, db_set_verified
from core.cache import cooldown_cache, rate_limit_cache, report_cache, global_report_cache
from handlers.membership import check_user_membership, create_join_markup
from handlers.ui import (
    UI,
    msg_searching,
    msg_no_results,
    msg_error,
    msg_rate_limited,
    msg_validation_error,
    msg_join_required,
    msg_banned
)


# ══════════════════════════════════════════════════════════════
#                 RATE LIMITING
# ══════════════════════════════════════════════════════════════

def is_rate_limited(user_id: int) -> Tuple[bool, int]:
    """
    Check if user is rate limited.
    
    Returns: (is_limited, seconds_remaining)
    """
    # Check cooldown first
    cooldown_key = f"cooldown_{user_id}"
    cooldown_time = cooldown_cache.get(cooldown_key)
    
    if cooldown_time is not None:
        elapsed = time.time() - cooldown_time
        remaining = config.SEARCH_COOLDOWN - int(elapsed)
        if remaining > 0:
            return True, remaining
    
    # Check rate limit (searches per minute)
    rate_key = f"ratelimit_{user_id}"
    current_count = rate_limit_cache.get(rate_key) or 0
    
    if current_count >= config.SEARCH_LIMIT_PER_MINUTE:
        return True, config.SEARCH_COOLDOWN
    
    return False, 0


def set_cooldown(user_id: int) -> None:
    """Set search cooldown for user."""
    cooldown_cache.set(f"cooldown_{user_id}", time.time(), ttl=config.SEARCH_COOLDOWN)
    
    # Increment rate limit counter
    rate_key = f"ratelimit_{user_id}"
    current_count = rate_limit_cache.get(rate_key) or 0
    rate_limit_cache.set(rate_key, current_count + 1, ttl=60)


# ══════════════════════════════════════════════════════════════
#                 INPUT VALIDATION
# ══════════════════════════════════════════════════════════════

def validate_search_query(query: str) -> Tuple[bool, str]:
    """
    Validate and sanitize search query.
    
    Returns: (is_valid, sanitized_query_or_error_message)
    """
    if not query or not query.strip():
        return False, "Query cannot be empty."
    
    cleaned = query.strip()
    
    if len(cleaned) < 2:
        return False, "Query too short. Minimum 2 characters."
    
    if len(cleaned) > config.MAX_QUERY_LENGTH:
        return False, f"Query too long. Maximum {config.MAX_QUERY_LENGTH} characters."
    
    # Check for gibberish (only repeated chars like "aaaaaaa")
    if len(cleaned) > 3 and re.match(r'^(.)\1+$', cleaned):
        return False, "Invalid query pattern."
    
    # Check for only special characters
    if re.match(r'^[^a-zA-Z0-9@.+]+$', cleaned):
        return False, "Query must contain letters or numbers."
    
    return True, cleaned


# ══════════════════════════════════════════════════════════════
#                 HTML HELPERS
# ══════════════════════════════════════════════════════════════

def safe_value(value: Any) -> str:
    """Convert any value to HTML-safe string."""
    if value is None:
        return "N/A"
    return html.escape(str(value))


def strip_html(text: str) -> str:
    """Remove all HTML tags for fallback plain text sending."""
    return re.sub(r'<[^>]+>', '', text)


def safe_truncate_html(text: str, max_length: int = None) -> str:
    """
    Safely truncate HTML text without breaking tags.
    
    ✅ Prevents broken HTML that Telegram rejects
    """
    if max_length is None:
        max_length = config.HTML_TRUNCATE_SAFE
    
    if len(text) <= max_length:
        return text
    
    # Find all open tags in the portion we're keeping
    open_tags = []
    tag_pattern = re.compile(r'<(/?)([\w]+)[^>]*>')
    
    # Truncate first
    truncated = text[:max_length]
    
    # Find the last complete line/word
    last_newline = truncated.rfind('\n')
    if last_newline > max_length - 200:
        truncated = truncated[:last_newline]
    
    # Find all tags in truncated portion
    for match in tag_pattern.finditer(truncated):
        is_close = match.group(1) == '/'
        tag_name = match.group(2).lower()
        
        if is_close:
            if open_tags and open_tags[-1] == tag_name:
                open_tags.pop()
        else:
            # Self-closing tags don't need closing
            if tag_name not in ('br', 'hr', 'img', 'input', 'meta', 'link'):
                open_tags.append(tag_name)
    
    # Close remaining tags in reverse order
    for tag in reversed(open_tags):
        truncated += f"</{tag}>"
    
    truncated += f"\n\n{UI.WARNING} <i>... Output truncated</i>"
    
    return truncated


# ══════════════════════════════════════════════════════════════
#                 DATA CATEGORIZER
# ══════════════════════════════════════════════════════════════

def categorize_data(data_list: List[dict]) -> Dict[str, List]:
    """Categorize data fields intelligently. All values HTML-escaped."""
    
    categories = {
        "identity": [],
        "contact": [],
        "address": [],
        "account": [],
        "financial": [],
        "other": []
    }
    
    identity_keywords = ["name", "fname", "lname", "firstname", "lastname", "fullname",
                         "username", "login", "dob", "birth", "age", "gender", "sex"]
    contact_keywords = ["phone", "mobile", "email", "mail", "tel", "cell"]
    address_keywords = ["address", "city", "state", "country", "zip", "postal", "street", "house"]
    account_keywords = ["password", "pass", "hash", "token", "ip", "useragent", "user_agent"]
    financial_keywords = ["card", "cvv", "bank", "account", "iban", "swift", "payment"]
    
    for item in data_list:
        if not isinstance(item, dict):
            continue
            
        for key, value in item.items():
            if not key:
                continue
                
            key_lower = str(key).lower()
            entry = (safe_value(key), safe_value(value))
            
            if any(kw in key_lower for kw in identity_keywords):
                categories["identity"].append(entry)
            elif any(kw in key_lower for kw in contact_keywords):
                categories["contact"].append(entry)
            elif any(kw in key_lower for kw in address_keywords):
                categories["address"].append(entry)
            elif any(kw in key_lower for kw in account_keywords):
                categories["account"].append(entry)
            elif any(kw in key_lower for kw in financial_keywords):
                categories["financial"].append(entry)
            else:
                categories["other"].append(entry)
    
    return categories


# ══════════════════════════════════════════════════════════════
#                 REPORT FORMATTING
# ══════════════════════════════════════════════════════════════

def format_report_page(database_name: str, data: List[dict], info_leak: str) -> str:
    """
    Format a single report page with safe HTML.
    ✅ All values HTML-escaped
    ✅ Safe truncation
    ✅ No broken tags
    """
    
    text = f"""
{UI.HEAVY_LINE}
      {UI.DATABASE} ᴅᴀᴛᴀʙᴀꜱᴇ ʀᴇꜱᴜʟᴛꜱ
{UI.HEAVY_LINE}

🔹 ꜱᴏᴜʀᴄᴇ: <b>{safe_value(database_name)}</b>
🔹 ɪɴꜰᴏ: {safe_value(info_leak)}
"""
    
    if not data:
        text += f"""
{UI.LIGHT_LINE}
{UI.WARNING} ɴᴏ ᴅᴀᴛᴀ ɪɴ ᴛʜɪꜱ ꜱᴏᴜʀᴄᴇ
{UI.LIGHT_LINE}
"""
        return text
    
    # Process data entries (limit to prevent huge messages)
    for idx, entry in enumerate(data[:10]):  # Max 10 entries per page
        if idx > 0:
            text += f"\n{UI.DOT_LINE}\n"
        
        if not isinstance(entry, dict):
            continue
        
        categories = categorize_data([entry])
        
        if categories["identity"]:
            text += f"\n{UI.USER} <b>ɪᴅᴇɴᴛɪᴛʏ</b>\n"
            for key, value in categories["identity"][:8]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        if categories["contact"]:
            text += f"\n{UI.PHONE} <b>ᴄᴏɴᴛᴀᴄᴛ</b>\n"
            for key, value in categories["contact"][:8]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        if categories["address"]:
            text += f"\n{UI.HOME} <b>ᴀᴅᴅʀᴇꜱꜱ</b>\n"
            for key, value in categories["address"][:8]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        if categories["account"]:
            text += f"\n{UI.KEY} <b>ᴀᴄᴄᴏᴜɴᴛ</b>\n"
            for key, value in categories["account"][:8]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        if categories["financial"]:
            text += f"\n{UI.CARD} <b>ꜰɪɴᴀɴᴄɪᴀʟ</b>\n"
            for key, value in categories["financial"][:8]:
                text += f"  • {key}: <code>{value}</code>\n"
        
        if categories["other"]:
            text += f"\n{UI.GLOBE} <b>ᴏᴛʜᴇʀ</b>\n"
            for key, value in categories["other"][:10]:
                text += f"  • {key}: <code>{value}</code>\n"
    
    if len(data) > 10:
        text += f"\n{UI.INFO} <i>Showing 10 of {len(data)} entries</i>\n"
    
    text += f"\n{UI.HEAVY_LINE}"
    
    # Safe truncation
    return safe_truncate_html(text)


# ══════════════════════════════════════════════════════════════
#                 API CALL
# ══════════════════════════════════════════════════════════════

def generate_report(query: str, query_id: int = None) -> Tuple[Optional[List[str]], int]:
    """
    Generate OSINT report from LeakOSINT API.
    
    ✅ Handles all error cases
    ✅ Caches results
    ✅ Tracks response time
    
    Returns: (list_of_pages, total_results) or (None, 0) on error
    """
    
    if query_id is None:
        query_id = randint(100000, 9999999)
    
    # ─── Check cache ───
    cache_key = f"report_{query_id}"
    cached = report_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # ─── API request ───
    data = {
        "token": config.API_TOKEN,
        "request": query.split("\n")[0][:config.MAX_QUERY_LENGTH],
        "limit": config.API_LIMIT,
        "lang": config.API_LANG
    }
    
    try:
        response = requests.post(
            config.API_URL,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
    
    except requests.Timeout:
        print(f"API Timeout for query: {query[:50]}")
        return None, 0
    
    except requests.RequestException as e:
        print(f"API Request Error: {e}")
        return None, 0
    
    except ValueError as e:
        print(f"API JSON Parse Error: {e}")
        return None, 0
    
    # ─── Handle API errors ───
    if result.get("Error code") or result.get("Error"):
        error_msg = result.get('Error code') or result.get('Error')
        print(f"API Error: {error_msg}")
        return None, 0
    
    # ─── Check results ───
    if "List" not in result or not result["List"]:
        # No results found
        no_results_page = f"""
{UI.HEAVY_LINE}
        {UI.SEARCH} ɴᴏ ʀᴇꜱᴜʟᴛꜱ
{UI.HEAVY_LINE}

{UI.WARNING} ɴᴏ ᴅᴀᴛᴀ ꜰᴏᴜɴᴅ ꜰᴏʀ ᴛʜɪꜱ ǫᴜᴇʀʏ.

{UI.LIGHT_LINE}
{UI.INFO} Tips:
{UI.LIGHT_LINE}
  • Try a different search term
  • Check spelling
  • Use full email or phone number

{UI.HEAVY_LINE}
"""
        pages = [no_results_page]
        report_cache.set(cache_key, (pages, 0), ttl=config.REPORT_CACHE_TTL)
        global_report_cache[str(query_id)] = pages
        return pages, 0
    
    # ─── Format results ───
    pages = []
    total_results = 0
    
    for database_name, db_data in result["List"].items():
        if not isinstance(db_data, dict):
            continue
            
        info_leak = db_data.get("InfoLeak", "")
        data_list = db_data.get("Data", [])
        
        if not isinstance(data_list, list):
            data_list = [data_list] if data_list else []
        
        total_results += len(data_list)
        
        if data_list:
            formatted = format_report_page(database_name, data_list, info_leak)
            pages.append(formatted)
    
    # Limit pages
    if len(pages) > config.MAX_REPORT_PAGES:
        pages = pages[:config.MAX_REPORT_PAGES]
        pages.append(f"{UI.INFO} Results truncated to {config.MAX_REPORT_PAGES} pages.")
    
    # ─── Cache the result ───
    if pages:
        report_cache.set(cache_key, (pages, total_results), ttl=config.REPORT_CACHE_TTL)
        global_report_cache[str(query_id)] = pages
    
    return pages if pages else None, total_results


# ══════════════════════════════════════════════════════════════
#                 PAGINATION BUILDER
# ══════════════════════════════════════════════════════════════

def create_pagination_keyboard(query_id: int, page_id: int, total_pages: int) -> InlineKeyboardMarkup:
    """Create pagination keyboard with safe bounds checking."""
    
    markup = InlineKeyboardMarkup()
    
    if total_pages <= 1:
        return markup
    
    # Normalize page ID
    page_id = max(0, min(page_id, total_pages - 1))
    
    # Calculate prev/next with wrapping
    prev_page = page_id - 1 if page_id > 0 else total_pages - 1
    next_page = page_id + 1 if page_id < total_pages - 1 else 0
    
    markup.row(
        InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"page_{query_id}_{prev_page}"),
        InlineKeyboardButton(f"📑 {page_id + 1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"page_{query_id}_{next_page}")
    )
    
    # Jump buttons for many pages
    if total_pages > 5:
        markup.row(
            InlineKeyboardButton("⏮️ ꜰɪʀꜱᴛ", callback_data=f"page_{query_id}_0"),
            InlineKeyboardButton("⏭️ ʟᴀꜱᴛ", callback_data=f"page_{query_id}_{total_pages - 1}")
        )
    
    return markup


# ══════════════════════════════════════════════════════════════
#                 MAIN SEARCH PROCESSOR
# ══════════════════════════════════════════════════════════════

def process_search(message: Message, query: str, bot) -> None:
    """
    Process a search query end-to-end.
    
    Pipeline:
      1. Validate input
      2. Save/update user
      3. Ban check
      4. Rate limit check
      5. Membership check
      6. API search
      7. Cache report
      8. Send result with pagination
      9. Log search
    """
    user = message.from_user
    user_id = user.id
    
    # ─── 1. Validate input ───
    is_valid, result = validate_search_query(query)
    if not is_valid:
        bot.reply_to(message, msg_validation_error(result), parse_mode="HTML")
        return
    
    clean_query = result
    
    # ─── 2. Save/update user ───
    db_add_user(user_id, user.username, user.first_name)
    
    # ─── 3. Ban check ───
    if db_is_banned(user_id):
        bot.reply_to(message, msg_banned(), parse_mode="HTML")
        return
    
    # ─── 4. Rate limit check ───
    is_limited, wait_seconds = is_rate_limited(user_id)
    if is_limited:
        bot.reply_to(message, msg_rate_limited(wait_seconds), parse_mode="HTML")
        return
    
    # ─── 5. Membership check (skip for owner) ───
    if user_id != config.OWNER_ID:
        membership = check_user_membership(user_id, bot)
        
        if membership.get("is_banned"):
            bot.reply_to(message, msg_banned(), parse_mode="HTML")
            return
        
        if not membership.get("is_member"):
            db_set_verified(user_id, False)
            markup = create_join_markup(membership["missing_channels"], bot=bot)
            bot.reply_to(
                message,
                msg_join_required(membership["missing_channels"]),
                parse_mode="HTML",
                reply_markup=markup
            )
            return
        else:
            db_set_verified(user_id, True)
    
    # ─── 6. Send searching message ───
    searching_msg = bot.reply_to(message, msg_searching(), parse_mode="HTML")
    
    # ─── 7. Generate report ───
    query_id = randint(100000, 9999999)
    start_time = time.time()
    
    report_pages, total_results = generate_report(clean_query, query_id)
    
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # ─── 8. Delete searching message ───
    try:
        bot.delete_message(message.chat.id, searching_msg.message_id)
    except Exception:
        pass
    
    # ─── 9. Handle errors ───
    if report_pages is None:
        bot.reply_to(message, msg_error(), parse_mode="HTML")
        db_log_search(user_id, clean_query, 0, response_time_ms)
        return
    
    if not report_pages or total_results == 0:
        bot.reply_to(message, msg_no_results(clean_query), parse_mode="HTML")
        db_log_search(user_id, clean_query, 0, response_time_ms)
        return
    
    # ─── 10. Log the search ───
    db_log_search(user_id, clean_query, total_results, response_time_ms)
    
    # ─── 11. Set cooldown ───
    set_cooldown(user_id)
    
    # ─── 12. Send first page with pagination ───
    markup = create_pagination_keyboard(query_id, 0, len(report_pages))
    
    try:
        bot.reply_to(message, report_pages[0], parse_mode="HTML", reply_markup=markup)
    except Exception as html_error:
        print(f"HTML parse error, sending plain: {html_error}")
        # Strip HTML and send plain
        clean_text = strip_html(report_pages[0])
        try:
            bot.reply_to(message, clean_text, reply_markup=markup)
        except Exception as e:
            print(f"Failed to send report: {e}")
            bot.reply_to(message, msg_error(), parse_mode="HTML")
