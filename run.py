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
print("[1/8] 📦 Loading python-dotenv...")
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
    print("      ❌ python-dotenv not installed")
    print("      Run: pip install python-dotenv")
    sys.exit(1)

# Step 2: Check environment variables
print()
print("[2/8] 🔑 Checking environment variables...")
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

if missing:
    print()
    print(f"      ❌ FATAL: Missing variables: {', '.join(missing)}")
    print("      Please check your .env file!")
    sys.exit(1)

# Step 3: Import telebot
print()
print("[3/8] 📦 Importing telebot...")
try:
    import telebot
    print("      ✅ telebot imported successfully")
except ImportError as e:
    print(f"      ❌ Failed: {e}")
    print("      Run: pip install pyTelegramBotAPI")
    sys.exit(1)

# Step 4: Import supabase
print()
print("[4/8] 📦 Importing supabase...")
try:
    from supabase import create_client, Client
    print("      ✅ supabase imported")
except ImportError as e:
    print(f"      ❌ Failed: {e}")
    print("      Run: pip install supabase")
    sys.exit(1)

# Step 5: Test Supabase connection
print()
print("[5/8] 🗄️  Testing Supabase connection...")
try:
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    supabase: Client = create_client(supabase_url, supabase_key)
    
    result = supabase.table('users').select('user_id').limit(1).execute()
    print("      ✅ Supabase connected!")
    print("      📊 Users table accessible")
except Exception as e:
    print(f"      ❌ Supabase error: {e}")
    print()
    print("      Possible issues:")
    print("      1. Wrong SUPABASE_URL or SUPABASE_KEY")
    print("      2. Tables not created (run SQL in Supabase)")
    print("      3. Network/firewall issue")
    traceback.print_exc()
    sys.exit(1)

# Step 6: Test Telegram Bot Token
print()
print("[6/8] 🤖 Testing Telegram Bot Token...")
try:
    bot_token = os.environ.get('BOT_TOKEN')
    bot = telebot.TeleBot(bot_token)
    bot_info = bot.get_me()
    print("      ✅ Bot connected!")
    print(f"      📛 Bot Name: {bot_info.first_name}")
    print(f"      🆔 Bot Username: @{bot_info.username}")
    print(f"      🔢 Bot ID: {bot_info.id}")
except Exception as e:
    print(f"      ❌ Telegram error: {e}")
    print()
    print("      Possible issues:")
    print("      1. Invalid BOT_TOKEN")
    print("      2. Bot deleted or revoked")
    print("      3. Network issue")
    traceback.print_exc()
    sys.exit(1)

# Step 7: Import bot module
print()
print("[7/8] 📦 Importing bot.py module...")
try:
    import bot as bot_module
    print("      ✅ bot.py imported successfully")
except Exception as e:
    print(f"      ❌ Failed to import bot.py: {e}")
    print()
    print("      Full traceback:")
    traceback.print_exc()
    sys.exit(1)

# Step 8: Initialize and start
print()
print("[8/8] 🚀 Initializing bot...")
try:
    if hasattr(bot_module, 'init_bot'):
        print("      🔧 Calling init_bot()...")
        bot_module.init_bot()
        print("      ✅ init_bot() done")
    
    if hasattr(bot_module, 'init_channels'):
        print("      🔧 Calling init_channels()...")
        bot_module.init_channels()
        print("      ✅ init_channels() done")
    
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
