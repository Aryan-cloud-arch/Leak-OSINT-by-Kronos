"""
handlers/__init__.py — Handlers Module Exports
"""
from handlers.ui import (
    UI,
    safe_escape,
    get_user_mention,
    is_group_chat,
    get_channel_type_icon,
    msg_welcome_owner,
    msg_welcome_user,
    msg_join_required,
    msg_verified_success,
    msg_verification_failed,
    msg_banned,
    msg_user_banned,
    msg_user_unbanned,
    msg_user_not_found,
    msg_rate_limited,
    msg_searching,
    msg_no_results,
    msg_error,
    msg_validation_error,
    msg_help_group,
    msg_stats,
    msg_users_list,
    msg_channels_list,
    msg_add_channel_help,
    msg_channel_added,
    msg_channel_add_error,
    msg_bot_not_admin,
    msg_remove_channel_prompt,
    msg_channel_removed,
    msg_cancelled,
    msg_broadcast_complete,
    msg_broadcast_progress,
    msg_results_expired,
    msg_owner_only
)

from handlers.membership import (
    build_channel_link,
    check_user_membership,
    create_join_markup,
    refresh_channel_cache,
    invalidate_membership_cache,
    get_channel_display_link
)

from handlers.search import (
    is_rate_limited,
    set_cooldown,
    validate_search_query,
    safe_value,
    strip_html,
    safe_truncate_html,
    categorize_data,
    format_report_page,
    generate_report,
    create_pagination_keyboard,
    process_search
)

from handlers.commands import (
    is_owner,
    cmd_start,
    cmd_help,
    cmd_channels,
    cmd_add_channel,
    cmd_remove_channel,
    cmd_stats,
    cmd_users,
    cmd_broadcast,
    cmd_ban,
    init_channels
)

from handlers.callbacks import (
    handle_callback,
    handle_verify_join,
    handle_remove_channel,
    handle_cancel_remove,
    handle_page_navigation
)

__all__ = [
    # UI Elements
    "UI",
    "safe_escape",
    "get_user_mention",
    "is_group_chat",
    "get_channel_type_icon",
    
    # UI Messages
    "msg_welcome_owner",
    "msg_welcome_user",
    "msg_join_required",
    "msg_verified_success",
    "msg_verification_failed",
    "msg_banned",
    "msg_user_banned",
    "msg_user_unbanned",
    "msg_user_not_found",
    "msg_rate_limited",
    "msg_searching",
    "msg_no_results",
    "msg_error",
    "msg_validation_error",
    "msg_help_group",
    "msg_stats",
    "msg_users_list",
    "msg_channels_list",
    "msg_add_channel_help",
    "msg_channel_added",
    "msg_channel_add_error",
    "msg_bot_not_admin",
    "msg_remove_channel_prompt",
    "msg_channel_removed",
    "msg_cancelled",
    "msg_broadcast_complete",
    "msg_broadcast_progress",
    "msg_results_expired",
    "msg_owner_only",
    
    # Membership
    "build_channel_link",
    "check_user_membership",
    "create_join_markup",
    "refresh_channel_cache",
    "invalidate_membership_cache",
    "get_channel_display_link",
    
    # Search
    "is_rate_limited",
    "set_cooldown",
    "validate_search_query",
    "safe_value",
    "strip_html",
    "safe_truncate_html",
    "categorize_data",
    "format_report_page",
    "generate_report",
    "create_pagination_keyboard",
    "process_search",
    
    # Commands
    "is_owner",
    "cmd_start",
    "cmd_help",
    "cmd_channels",
    "cmd_add_channel",
    "cmd_remove_channel",
    "cmd_stats",
    "cmd_users",
    "cmd_broadcast",
    "cmd_ban",
    "init_channels",
    
    # Callbacks
    "handle_callback",
    "handle_verify_join",
    "handle_remove_channel",
    "handle_cancel_remove",
    "handle_page_navigation"
]
