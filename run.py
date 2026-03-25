#!/usr/bin/env python3
"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        LeakOSINT Bot - Debug Runner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import os
import traceback

print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("        🤖 LeakOSINT Bot - Starting...")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()

# Step 1: Load dotenv
print("[1/9] 📦 Loading python-dotenv...")
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
        print("      ✅ Loaded .env file")
    else:
        print("      ⚠️  No .env file found!")
        print("      📁 Current directory:", os.getcwd())
        print("      📄 Files here:", os.listdir('.'))
except ImportError:
    print("      ⚠️  python-dotenv not installed (using system env vars)")

# Step 2: Check environment variables
print()
print("[2/9] 🔑 Checking environment variables...")
required_vars = ['BOT_TOKEN', 'OWNER_ID', 'API_TOKEN', 'SUPABASE_URL', 'SUPABASE_KEY']
missing = []
for var in required_vars:
    val = os.environ.get(var)
    if val:
        masked = val[:5] + "..." + val[-3:] if len(val) > 10 else "***"
        print(f"      ✅ {var} = {masked}")
    else:
        print(f"      ❌ {var} = MISSING!")
        missing.append(var)

optional_vars = ['REQUIRED_CHANNELS', 'API_LANG', 'API_LIMIT']
for var in optional_vars:
    val = os.environ.get(var)
    if val:
        masked = val[:20] + "..." if len(val) > 20 else val
        print(f"      ℹ️  {var} = {masked}")
    else:
        print(f"      ℹ️  {var} = (not set, using default)")

if missing:
    print()
    print(f"      ❌ FATAL: Missing variables: {', '.join(missing)}")
    print("      Please set environment variables or create .env file!")
    sys.exit(1)

# Step 3: Import telebot
print()
print("[3/9] 📦 Importing telebot...")
try:
    import telebot
    print(f"      ✅ telebot v{telebot.__version__} imported")
except ImportError as e:
    print(f"      ❌ Failed: {e}")
    print("      Run: pip install pyTelegramBotAPI")
    sys.exit(1)

# Step 4: Import supabase
print()
print("[4/9] 📦 Importing supabase...")
try:
    from supabase import create_client, Client
    print("      ✅ supabase imported")
except ImportError as e:
    print(f"      ❌ Failed: {e}")
    print("      Run: pip install supabase")
    sys.exit(1)

# Step 5: Import requests
print()
print("[5/9] 📦 Importing requests...")
try:
    import requests
    print(f"      ✅ requests v{requests.__version__} imported")
except ImportError as e:
    print(f"      ❌ Failed: {e}")
    print("      Run: pip install requests")
    sys.exit(1)

# Step 6: Test Supabase connection
print()
print("[6/9] 🗄️  Testing Supabase connection...")
try:
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    test_client: Client = create_client(supabase_url, supabase_key)
    
    # Test users table
    result = test_client.table('users').select('user_id').limit(1).execute()
    print("      ✅ Users table accessible")
    
    # Test channels table
    result2 = test_client.table('required_channels').select('channel_id').limit(1).execute()
    print("      ✅ Channels table accessible")
    
    # Test search_logs table
    result3 = test_client.table('search_logs').select('id').limit(1).execute()
    print("      ✅ Search logs table accessible")
    
    # Check if invite_link column exists
    try:
        result4 = test_client.table('required_channels').select('invite_link').limit(1).execute()
        print("      ✅ invite_link column exists")
    except Exception:
        print("      ⚠️  invite_link column missing!")
        print("      Run this SQL in Supabase:")
        print("      ALTER TABLE required_channels ADD COLUMN IF NOT EXISTS invite_link TEXT;")
    
    print("      ✅ Supabase connected!")

except Exception as e:
    print(f"      ❌ Supabase error: {e}")
    print()
    print("      Possible issues:")
    print("      1. Wrong SUPABASE_URL or SUPABASE_KEY")
    print("      2. Tables not created (run SQL in Supabase)")
    print("      3. Network/firewall issue")
    traceback.print_exc()
    sys.exit(1)

# Step 7: Test Telegram Bot Token
print()
print("[7/9] 🤖 Testing Telegram Bot Token...")
try:
    bot_token = os.environ.get('BOT_TOKEN')
    test_bot = telebot.TeleBot(bot_token)
    bot_info = test_bot.get_me()
    print("      ✅ Bot connected!")
    print(f"      📛 Bot Name: {bot_info.first_name}")
    print(f"      🆔 Bot Username: @{bot_info.username}")
    print(f"      🔢 Bot ID: {bot_info.id}")
    del test_bot  # Clean up test instance
except Exception as e:
    print(f"      ❌ Telegram error: {e}")
    print()
    print("      Possible issues:")
    print("      1. Invalid BOT_TOKEN")
    print("      2. Bot deleted or revoked")
    print("      3. Network issue")
    traceback.print_exc()
    sys.exit(1)

# Step 8: Import bot module
print()
print("[8/9] 📦 Importing bot module...")
try:
    # Import core modules first to catch errors early
    print("      📦 Loading core.config...")
    from core.config import config
    print("      ✅ Config loaded")
    
    print("      📦 Loading core.cache...")
    from core.cache import channel_cache, membership_cache
    print("      ✅ Cache system loaded")
    
    print("      📦 Loading core.database...")
    from core.database import db_get_stats
    print("      ✅ Database module loaded")
    
    print("      📦 Loading handlers.ui...")
    from handlers.ui import UI
    print("      ✅ UI module loaded")
    
    print("      📦 Loading handlers.membership...")
    from handlers.membership import check_user_membership
    print("      ✅ Membership module loaded")
    
    print("      📦 Loading handlers.search...")
    from handlers.search import process_search
    print("      ✅ Search module loaded")
    
    print("      📦 Loading handlers.commands...")
    from handlers.commands import cmd_start
    print("      ✅ Commands module loaded")
    
    print("      📦 Loading handlers.callbacks...")
    from handlers.callbacks import handle_callback
    print("      ✅ Callbacks module loaded")
    
    print("      📦 Loading bot.py...")
    import bot as bot_module
    print("      ✅ bot.py imported successfully")

except Exception as e:
    print(f"      ❌ Failed to import: {e}")
    print()
    print("      Full traceback:")
    traceback.print_exc()
    sys.exit(1)

# Step 9: Initialize and start
print()
print("[9/9] 🚀 Initializing bot...")
try:
    # Initialize bot info
    print("      🔧 Calling init_bot()...")
    bot_module.init_bot()
    print("      ✅ init_bot() done")
    
    # Initialize channels
    print("      🔧 Calling init_channels()...")
    bot_module.init_channels()
    print("      ✅ init_channels() done")
    
    # Start cache cleanup thread
    print("      🔧 Starting cache cleanup thread...")
    bot_module._start_cleanup_thread()
    
    # Quick stats check
    try:
        stats = db_get_stats()
        print(f"      📊 Users: {stats.get('total_users', 0)} | Channels: {stats.get('total_channels', 0)}")
    except Exception:
        pass

except Exception as e:
    print(f"      ❌ Initialization error: {e}")
    traceback.print_exc()
    sys.exit(1)

print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("        ✅ ALL CHECKS PASSED!")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()
print("🟢 Bot is now running! Press Ctrl+C to stop.")
print()

try:
    bot_module.bot.infinity_polling(timeout=60, long_polling_timeout=60)
except KeyboardInterrupt:
    print()
    print("🛑 Bot stopped by user (Ctrl+C)")
except Exception as e:
    print()
    print(f"❌ POLLING ERROR: {e}")
    print()
    print("Full traceback:")
    traceback.print_exc()
    sys.exit(1)
