"""
handlers/callbacks.py — All Callback Query Handlers
Pro-Level:
  ✅ Ban-aware
  ✅ Invalidates membership cache on verify
  ✅ Proper error handling
  ✅ All imports correct
"""
from telebot.types import CallbackQuery

from core.config import config
from core.database import db_remove_channel, db_set_verified
from core.cache import global_report_cache
from handlers.membership import (
    check_user_membership,
    create_join_markup,
    invalidate_membership_cache,
    refresh_channel_cache
)
from handlers.search import create_pagination_keyboard, strip_html
from handlers.ui import (
    UI,
    msg_verified_success,
    msg_verification_failed,
    msg_banned,
    msg_channel_removed,
    msg_cancelled,
    msg_results_expired,
    msg_owner_only
)


# ══════════════════════════════════════════════════════════════
#                  MAIN CALLBACK ROUTER
# ══════════════════════════════════════════════════════════════

def handle_callback(call: CallbackQuery, bot) -> None:
    """Route all callback queries to their handlers."""
    
    user_id = call.from_user.id
    data = call.data
    
    try:
        # ─── Verify join ───
        if data == "verify_join":
            handle_verify_join(call, bot)
            return
        
        # ─── Remove channel ───
        if data.startswith("rmch_"):
            handle_remove_channel(call, bot)
            return
        
        # ─── Cancel remove ───
        if data == "cancel_remove":
            handle_cancel_remove(call, bot)
            return
        
        # ─── Page navigation ───
        if data.startswith("page_"):
            handle_page_navigation(call, bot)
            return
        
        # ─── No-op (current page indicator) ───
        if data == "noop":
            bot.answer_callback_query(call.id)
            return
        
        # ─── Unknown callback ───
        bot.answer_callback_query(call.id, "Unknown action")
    
    except Exception as e:
        print(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "An error occurred", show_alert=True)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#                  VERIFY MEMBERSHIP
# ══════════════════════════════════════════════════════════════

def handle_verify_join(call: CallbackQuery, bot) -> None:
    """Handle the 'Check Membership' button."""
    
    user_id = call.from_user.id
    
    # Invalidate cache to get fresh status
    invalidate_membership_cache(user_id)
    
    # Check membership
    membership = check_user_membership(user_id, bot)
    
    # Handle banned users
    if membership.get("is_banned"):
        bot.answer_callback_query(call.id, "🚫 You are banned!", show_alert=True)
        try:
            bot.edit_message_text(
                msg_banned(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML"
            )
        except Exception:
            pass
        return
    
    if membership.get("is_member"):
        # ─── SUCCESS ───
        db_set_verified(user_id, True)
        
        try:
            bot.edit_message_text(
                msg_verified_success(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Edit message error: {e}")
        
        bot.answer_callback_query(call.id, "✅ Verified successfully!")
    
    else:
        # ─── STILL MISSING CHANNELS ───
        db_set_verified(user_id, False)
        
        markup = create_join_markup(membership["missing_channels"], bot=bot)
        
        try:
            bot.edit_message_text(
                msg_verification_failed(membership["missing_channels"]),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            print(f"Edit message error: {e}")
        
        bot.answer_callback_query(call.id, "❌ Please join all channels!", show_alert=True)


# ══════════════════════════════════════════════════════════════
#                  REMOVE CHANNEL
# ══════════════════════════════════════════════════════════════

def handle_remove_channel(call: CallbackQuery, bot) -> None:
    """Handle channel removal confirmation."""
    
    user_id = call.from_user.id
    
    # Owner only check
    if user_id != config.OWNER_ID:
        bot.answer_callback_query(call.id, "❌ Owner only!", show_alert=True)
        return
    
    # Extract channel ID from callback data
    channel_id = call.data.replace("rmch_", "")
    
    # Remove from database
    success = db_remove_channel(channel_id)
    
    if success:
        # Refresh caches
        refresh_channel_cache()
        invalidate_membership_cache()  # Clear all user caches
        
        try:
            bot.edit_message_text(
                msg_channel_removed(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Edit message error: {e}")
        
        bot.answer_callback_query(call.id, "✅ Channel removed!")
    
    else:
        bot.answer_callback_query(call.id, "❌ Failed to remove!", show_alert=True)


# ══════════════════════════════════════════════════════════════
#                  CANCEL REMOVE
# ══════════════════════════════════════════════════════════════

def handle_cancel_remove(call: CallbackQuery, bot) -> None:
    """Handle cancel channel removal."""
    
    try:
        bot.edit_message_text(
            msg_cancelled(),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Edit message error: {e}")
    
    bot.answer_callback_query(call.id, "Cancelled")


# ══════════════════════════════════════════════════════════════
#                  PAGE NAVIGATION
# ══════════════════════════════════════════════════════════════

def handle_page_navigation(call: CallbackQuery, bot) -> None:
    """Handle pagination of search results."""
    
    # Parse callback data: page_{query_id}_{page_num}
    parts = call.data.split("_")
    
    if len(parts) < 3:
        bot.answer_callback_query(call.id, "⚠️ Invalid page data", show_alert=True)
        return
    
    query_id = parts[1]
    
    try:
        page_id = int(parts[2])
    except ValueError:
        bot.answer_callback_query(call.id, "⚠️ Invalid page number", show_alert=True)
        return
    
    # Get report from cache
    if query_id not in global_report_cache:
        bot.answer_callback_query(call.id, msg_results_expired(), show_alert=True)
        return
    
    report = global_report_cache[query_id]
    total_pages = len(report)
    
    if total_pages == 0:
        bot.answer_callback_query(call.id, "⚠️ No pages available", show_alert=True)
        return
    
    # Normalize page (wrap around)
    if page_id < 0:
        page_id = total_pages - 1
    elif page_id >= total_pages:
        page_id = 0
    
    # Build pagination keyboard
    markup = create_pagination_keyboard(int(query_id), page_id, total_pages)
    
    # Update message
    try:
        bot.edit_message_text(
            report[page_id],
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    
    except Exception as e:
        print(f"Page navigation error: {e}")
        
        # Try without HTML parsing (fallback)
        try:
            clean_text = strip_html(report[page_id])
            bot.edit_message_text(
                clean_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
        
        except Exception as e2:
            print(f"Fallback page error: {e2}")
            bot.answer_callback_query(call.id, "⚠️ Could not load page", show_alert=True)
