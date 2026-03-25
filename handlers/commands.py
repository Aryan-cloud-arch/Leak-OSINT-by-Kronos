"""
handlers/commands.py — All Command Handlers
Pro-Level:
  ✅ Ban checks on ALL commands
  ✅ Owner-only commands protected
  ✅ HTML-escaped output
  ✅ Error handling
  ✅ Bot is admin check when adding channels
  ✅ Generates & stores invite links for private channels
  ✅ Broadcast with batching to prevent flood bans
"""
import html
import time
from typing import Optional

import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.config import config
from core.database import (
    db_add_user,
    db_get_user,
    db_set_verified,
    db_is_banned,
    db_toggle_ban,
    db_get_channels,
    db_add_channel,
    db_remove_channel,
    db_get_all_users,
    db_get_active_users,
    db_get_stats
)
from core.cache import membership_cache
from handlers.membership import (
    check_user_membership,
    create_join_markup,
    refresh_channel_cache,
    invalidate_membership_cache
)
from handlers.ui import (
    UI,
    is_group_chat,
    msg_welcome_owner,
    msg_welcome_user,
    msg_join_required,
    msg_banned,
    msg_stats,
    msg_channels_list,
    msg_add_channel_help,
    msg_channel_added,
    msg_channel_add_error,
    msg_bot_not_admin,
    msg_remove_channel_prompt,
    msg_users_list,
    msg_broadcast_complete,
    msg_broadcast_progress,
    msg_user_banned,
    msg_user_unbanned,
    msg_user_not_found,
    msg_owner_only,
    msg_help_group
)


# ══════════════════════════════════════════════════════════════
#                  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def is_owner(user_id: int) -> bool:
    """Check if user is the bot owner."""
    return user_id == config.OWNER_ID


def owner_only(func):
    """Decorator to restrict command to owner only."""
    def wrapper(message: Message, bot):
        if not is_owner(message.from_user.id):
            bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
            return
        return func(message, bot)
    return wrapper


# ══════════════════════════════════════════════════════════════
#                  /start COMMAND
# ══════════════════════════════════════════════════════════════

def cmd_start(message: Message, bot) -> None:
    """Handle /start command."""
    user = message.from_user
    user_id = user.id
    
    # Save user to database
    db_add_user(user_id, user.username, user.first_name)
    
    # Ban check
    if db_is_banned(user_id):
        bot.reply_to(message, msg_banned(), parse_mode="HTML")
        return
    
    # Owner gets admin panel
    if is_owner(user_id):
        bot.reply_to(message, msg_welcome_owner(), parse_mode="HTML")
        return
    
    # Check channel membership
    membership = check_user_membership(user_id, bot)
    
    if membership.get("is_banned"):
        bot.reply_to(message, msg_banned(), parse_mode="HTML")
        return
    
    if membership.get("is_member"):
        db_set_verified(user_id, True)
        bot.reply_to(message, msg_welcome_user(True), parse_mode="HTML")
    else:
        db_set_verified(user_id, False)
        markup = create_join_markup(membership["missing_channels"], bot=bot)
        bot.reply_to(
            message,
            msg_join_required(membership["missing_channels"]),
            parse_mode="HTML",
            reply_markup=markup
        )


# ══════════════════════════════════════════════════════════════
#                  /help COMMAND
# ══════════════════════════════════════════════════════════════

def cmd_help(message: Message, bot) -> None:
    """Handle /help command."""
    user_id = message.from_user.id
    
    # In groups, show group help
    if is_group_chat(message):
        bot.reply_to(message, msg_help_group(), parse_mode="HTML")
        return
    
    # Ban check
    if db_is_banned(user_id):
        bot.reply_to(message, msg_banned(), parse_mode="HTML")
        return
    
    # Owner gets admin panel
    if is_owner(user_id):
        bot.reply_to(message, msg_welcome_owner(), parse_mode="HTML")
        return
    
    # Regular users
    membership = check_user_membership(user_id, bot)
    bot.reply_to(message, msg_welcome_user(membership.get("is_member", False)), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#                  /channels COMMAND (Owner Only)
# ══════════════════════════════════════════════════════════════

def cmd_channels(message: Message, bot) -> None:
    """Handle /channels command — owner only."""
    if not is_owner(message.from_user.id):
        bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
        return
    
    channels = db_get_channels(include_inactive=False)
    bot.reply_to(message, msg_channels_list(channels), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#                  /addchannel COMMAND (Owner Only)
# ══════════════════════════════════════════════════════════════

def cmd_add_channel(message: Message, bot) -> None:
    """Handle /addchannel command — owner only."""
    if not is_owner(message.from_user.id):
        bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
        return
    
    # Parse input
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise ValueError("No channel provided")
        channel_input = parts[1].strip()
    except (IndexError, ValueError):
        bot.reply_to(message, msg_add_channel_help(), parse_mode="HTML")
        return
    
    if not channel_input:
        bot.reply_to(message, msg_add_channel_help(), parse_mode="HTML")
        return
    
    try:
        # Fetch channel info from Telegram
        chat = bot.get_chat(channel_input)
        
        channel_id = str(chat.id)
        channel_title = chat.title or channel_input
        chat_type = chat.type or "channel"
        chat_username = chat.username or None
        
        # Check if bot is admin
        try:
            bot_member = bot.get_chat_member(chat.id, bot.get_me().id)
            if bot_member.status not in ("administrator", "creator"):
                bot.reply_to(message, msg_bot_not_admin(channel_title), parse_mode="HTML")
                return
        except Exception as admin_err:
            print(f"Admin check warning: {admin_err}")
            # Continue anyway - might still work
        
        # Generate invite link for private channels
        invite_link = None
        
        if chat_username:
            # Public channel - username is the link
            invite_link = f"https://t.me/{chat_username}"
        else:
            # Private channel - needs invite link
            try:
                invite_link = bot.export_chat_invite_link(chat.id)
            except Exception as link_err:
                print(f"Could not generate invite link: {link_err}")
                # Try to get existing invite link
                if hasattr(chat, 'invite_link') and chat.invite_link:
                    invite_link = chat.invite_link
        
        # Save to database
        success = db_add_channel(
            channel_id=channel_id,
            channel_name=channel_title,
            channel_username=chat_username,
            channel_type=chat_type,
            invite_link=invite_link
        )
        
        if not success:
            bot.reply_to(message, msg_channel_add_error("Database error"), parse_mode="HTML")
            return
        
        # Refresh cache
        refresh_channel_cache()
        invalidate_membership_cache()
        
        # Success message
        bot.reply_to(
            message,
            msg_channel_added(
                channel_title=channel_title,
                channel_id=channel_id,
                channel_type=chat_type,
                username=chat_username,
                invite_link=invite_link
            ),
            parse_mode="HTML"
        )
    
    except Exception as e:
        print(f"Add channel error: {e}")
        bot.reply_to(message, msg_channel_add_error(str(e)), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#                  /removechannel COMMAND (Owner Only)
# ══════════════════════════════════════════════════════════════

def cmd_remove_channel(message: Message, bot) -> None:
    """Handle /removechannel command — owner only."""
    if not is_owner(message.from_user.id):
        bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
        return
    
    channels = db_get_channels(include_inactive=False)
    
    if not channels:
        bot.reply_to(message, f"{UI.WARNING} No channels to remove.", parse_mode="HTML")
        return
    
    markup = InlineKeyboardMarkup()
    color_emojis = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
    
    for idx, ch in enumerate(channels):
        emoji = color_emojis[idx % len(color_emojis)]
        title = ch.get("channel_name") or "Channel"
        # Truncate long names
        if len(title) > 25:
            title = title[:22] + "..."
        
        markup.add(InlineKeyboardButton(
            f"{emoji} ʀᴇᴍᴏᴠᴇ {html.escape(title)}",
            callback_data=f"rmch_{ch['channel_id']}"
        ))
    
    markup.add(InlineKeyboardButton("✖️ ᴄᴀɴᴄᴇʟ", callback_data="cancel_remove"))
    
    bot.reply_to(
        message,
        msg_remove_channel_prompt(len(channels)),
        parse_mode="HTML",
        reply_markup=markup
    )


# ══════════════════════════════════════════════════════════════
#                  /stats COMMAND (Owner Only)
# ══════════════════════════════════════════════════════════════

def cmd_stats(message: Message, bot) -> None:
    """Handle /stats command — owner only."""
    if not is_owner(message.from_user.id):
        bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
        return
    
    stats = db_get_stats()
    bot.reply_to(message, msg_stats(stats), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#                  /users COMMAND (Owner Only)
# ══════════════════════════════════════════════════════════════

def cmd_users(message: Message, bot) -> None:
    """Handle /users command — owner only."""
    if not is_owner(message.from_user.id):
        bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
        return
    
    users = db_get_all_users(limit=50)
    total = len(users)
    
    if not users:
        bot.reply_to(message, f"{UI.WARNING} No users yet.", parse_mode="HTML")
        return
    
    bot.reply_to(message, msg_users_list(users, total), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#                  /broadcast COMMAND (Owner Only)
# ══════════════════════════════════════════════════════════════

def cmd_broadcast(message: Message, bot) -> None:
    """
    Handle /broadcast command — owner only.
    Sends with delays to prevent flood bans.
    """
    if not is_owner(message.from_user.id):
        bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
        return
    
    # Parse broadcast message
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise ValueError("No message")
        broadcast_text = parts[1].strip()
    except (IndexError, ValueError):
        bot.reply_to(
            message,
            f"{UI.INFO} Usage: /broadcast <code>your message here</code>",
            parse_mode="HTML"
        )
        return
    
    if not broadcast_text:
        bot.reply_to(message, f"{UI.ERROR} Broadcast message cannot be empty.", parse_mode="HTML")
        return
    
    # Truncate if too long
    if len(broadcast_text) > config.MAX_BROADCAST_LENGTH:
        broadcast_text = broadcast_text[:config.MAX_BROADCAST_LENGTH]
    
    # Format broadcast
    formatted_broadcast = f"""
{UI.HEAVY_LINE}
        {UI.CHANNEL} ʙʀᴏᴀᴅᴄᴀꜱᴛ
{UI.HEAVY_LINE}

{broadcast_text}

{UI.HEAVY_LINE}
"""
    
    # Get active users
    users = db_get_active_users()
    
    if not users:
        bot.reply_to(message, f"{UI.WARNING} No active users to broadcast to.", parse_mode="HTML")
        return
    
    # Send status message
    status_msg = bot.reply_to(
        message,
        f"{UI.LOADING} Broadcasting to {len(users)} users...",
        parse_mode="HTML"
    )
    
    success = 0
    failed = 0
    blocked = 0
    
    # Broadcast in batches with delays
    for idx, user in enumerate(users):
        try:
            bot.send_message(user["user_id"], formatted_broadcast, parse_mode="HTML")
            success += 1
        
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 403:
                # User blocked bot
                blocked += 1
            else:
                failed += 1
            print(f"Broadcast error for {user.get('user_id')}: {e}")
        
        except Exception as e:
            failed += 1
            print(f"Broadcast error: {e}")
        
        # Update progress every batch
        if (idx + 1) % config.BROADCAST_BATCH_SIZE == 0:
            try:
                bot.edit_message_text(
                    msg_broadcast_progress(idx + 1, len(users), success, failed),
                    status_msg.chat.id,
                    status_msg.message_id,
                    parse_mode="HTML"
                )
            except Exception:
                pass
            
            # Delay between batches
            time.sleep(config.BROADCAST_DELAY)
    
    # Final status
    try:
        bot.edit_message_text(
            msg_broadcast_complete(success, failed, blocked),
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
    except Exception:
        bot.reply_to(message, msg_broadcast_complete(success, failed, blocked), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#                  /ban COMMAND (Owner Only)
# ══════════════════════════════════════════════════════════════

def cmd_ban(message: Message, bot) -> None:
    """Handle /ban <user_id> command — owner only. Toggles ban status."""
    if not is_owner(message.from_user.id):
        bot.reply_to(message, msg_owner_only(), parse_mode="HTML")
        return
    
    # Parse user ID
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise ValueError("No user ID")
        target_id = int(parts[1].strip())
    except (IndexError, ValueError):
        bot.reply_to(
            message,
            f"{UI.INFO} Usage: /ban <code>user_id</code>",
            parse_mode="HTML"
        )
        return
    
    # Toggle ban
    new_status = db_toggle_ban(target_id)
    
    if new_status is None:
        bot.reply_to(message, msg_user_not_found(), parse_mode="HTML")
        return
    
    # Invalidate membership cache for banned user
    invalidate_membership_cache(target_id)
    
    if new_status:
        bot.reply_to(message, msg_user_banned(target_id), parse_mode="HTML")
    else:
        bot.reply_to(message, msg_user_unbanned(target_id), parse_mode="HTML")


# ══════════════════════════════════════════════════════════════
#                  CHANNEL INITIALIZATION
# ══════════════════════════════════════════════════════════════

def init_channels(bot) -> None:
    """Initialize channels from config on bot startup."""
    if not config.INITIAL_CHANNELS:
        print(f"{UI.INFO} No initial channels configured.")
        return
    
    print(f"{UI.INFO} Initializing {len(config.INITIAL_CHANNELS)} channels...")
    
    for channel_input in config.INITIAL_CHANNELS:
        channel_input = channel_input.strip()
        if not channel_input:
            continue
        
        try:
            chat = bot.get_chat(channel_input)
            
            channel_id = str(chat.id)
            channel_title = chat.title or channel_input
            chat_type = chat.type or "channel"
            chat_username = chat.username or None
            
            # Generate invite link
            invite_link = None
            if chat_username:
                invite_link = f"https://t.me/{chat_username}"
            else:
                try:
                    invite_link = bot.export_chat_invite_link(chat.id)
                except Exception:
                    if hasattr(chat, 'invite_link') and chat.invite_link:
                        invite_link = chat.invite_link
            
            db_add_channel(
                channel_id=channel_id,
                channel_name=channel_title,
                channel_username=chat_username,
                channel_type=chat_type,
                invite_link=invite_link
            )
            
            print(f"  {UI.SUCCESS} Added: {channel_title} ({chat_type})")
        
        except Exception as e:
            print(f"  {UI.WARNING} Could not add {channel_input}: {e}")
    
    # Refresh cache after initialization
    refresh_channel_cache()
