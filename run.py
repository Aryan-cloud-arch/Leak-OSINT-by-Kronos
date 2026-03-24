#!/usr/bin/env python3
"""
LeakOSINT Bot Runner
Loads environment variables from .env file and starts the bot
"""

import os
import sys
import time

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print("✅ Loaded environment from .env file")
    else:
        print("⚠️ No .env file found, using system environment variables")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables")

# Now import and run the bot
if __name__ == "__main__":
    try:
        from bot import bot, init_bot, init_channels, UI
        
        init_bot()
        init_channels()
        
        while True:
            try:
                bot.polling(none_stop=True, timeout=60)
            except Exception as e:
                print(f"❌ Polling error: {e}")
                print("🔄 Restarting in 5 seconds...")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
