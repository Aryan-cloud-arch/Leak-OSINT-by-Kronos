#!/usr/bin/env python3
"""
LeakOSINT Bot Runner
Loads environment variables from .env file and starts the bot
"""

import os
import sys

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    
    # Load from .env file
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print("✅ Loaded environment from .env file")
    else:
        print("⚠️ No .env file found, using system environment variables")
        
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables")
    print("   Install with: pip install python-dotenv")

# Now import and run the bot
if __name__ == "__main__":
    try:
        import bot
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
