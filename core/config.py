"""
core/config.py — Configuration + Environment Validation
Pro-Level: Validates EVERYTHING on startup, fails fast with clear errors.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BotConfig:
    """Centralized configuration with validation."""
    
    # ─── Required Credentials ───
    BOT_TOKEN: str
    API_TOKEN: str
    OWNER_ID: int
    
    # ─── Supabase ───
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # ─── API Settings ───
    API_URL: str = "https://leakosintapi.com/"
    API_LANG: str = "en"
    API_LIMIT: int = 300
    
    # ─── Caching (TTL in seconds) ───
    CHANNEL_CACHE_TTL: int = 600       # 10 min — channel list rarely changes
    MEMBERSHIP_CACHE_TTL: int = 300    # 5 min — balance freshness vs speed
    REPORT_CACHE_TTL: int = 1800      # 30 min — report pages expire
    
    # ─── Rate Limiting ───
    SEARCH_COOLDOWN: int = 10         # seconds between searches per user
    SEARCH_LIMIT_PER_MINUTE: int = 5  # max searches per minute per user
    BROADCAST_BATCH_SIZE: int = 30    # messages per batch
    BROADCAST_DELAY: float = 1.0      # seconds between batches
    
    # ─── Safety ───
    MAX_QUERY_LENGTH: int = 500
    MAX_BROADCAST_LENGTH: int = 4096
    MAX_REPORT_PAGES: int = 50        # cap pagination
    HTML_TRUNCATE_SAFE: int = 3700    # safe margin before hard limit
    
    # ─── Initial Channels ───
    INITIAL_CHANNELS: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load and validate all config from environment variables."""
        errors = []
        warnings = []
        
        # ─── REQUIRED FIELDS ───
        BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
        if not BOT_TOKEN:
            errors.append("BOT_TOKEN is required")
        elif not re.match(r"^\d+:[A-Za-z0-9_-]+$", BOT_TOKEN):
            errors.append("BOT_TOKEN format is invalid")
        
        API_TOKEN = os.environ.get("API_TOKEN", "").strip()
        if not API_TOKEN:
            errors.append("API_TOKEN is required")
        
        OWNER_ID_STR = os.environ.get("OWNER_ID", "").strip()
        if not OWNER_ID_STR:
            errors.append("OWNER_ID is required")
        else:
            try:
                OWNER_ID = int(OWNER_ID_STR)
            except ValueError:
                errors.append("OWNER_ID must be a valid integer")
                OWNER_ID = 0
            else:
                OWNER_ID = int(OWNER_ID_STR)
        
        SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
        if not SUPABASE_URL:
            errors.append("SUPABASE_URL is required")
        elif not SUPABASE_URL.startswith(("http://", "https://")):
            errors.append("SUPABASE_URL must be a valid URL")
        
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
        if not SUPABASE_KEY:
            errors.append("SUPABASE_KEY is required")
        
        # ─── OPTIONAL FIELDS ───
        API_URL = os.environ.get("API_URL", "https://leakosintapi.com/").strip()
        if not API_URL.endswith("/"):
            API_URL += "/"
        
        try:
            API_LANG = os.environ.get("API_LANG", "en").strip().lower()
        except ValueError:
            warnings.append("Invalid API_LANG, defaulting to 'en'")
            API_LANG = "en"
        
        try:
            API_LIMIT = int(os.environ.get("API_LIMIT", "300"))
            if API_LIMIT < 1:
                API_LIMIT = 1
            elif API_LIMIT > 1000:
                warnings.append("API_LIMIT capped at 1000")
                API_LIMIT = 1000
        except ValueError:
            warnings.append("Invalid API_LIMIT, defaulting to 300")
            API_LIMIT = 300
        
        # Parse initial channels
        raw_channels = os.environ.get("REQUIRED_CHANNELS", "").strip()
        if raw_channels:
            INITIAL_CHANNELS = [ch.strip() for ch in raw_channels.split(",") if ch.strip()]
        else:
            INITIAL_CHANNELS = []
        
        # ─── FAIL FAST if errors ───
        if errors:
            error_msg = "\n" + "=" * 50 + "\n" + \
                       "❌ CONFIGURATION ERROR\n" + \
                       "=" * 50 + "\n\n"
            for err in errors:
                error_msg += f"  🔴 {err}\n"
            
            if warnings:
                error_msg += "\n  ⚠️  WARNINGS:\n"
                for warn in warnings:
                    error_msg += f"     {warn}\n"
            
            error_msg += "\n" + "=" * 50 + "\n"
            print(error_msg)
            exit(1)
        
        if warnings:
            warn_msg = "\n⚠️  WARNINGS:\n"
            for w in warnings:
                warn_msg += f"  • {w}\n"
            print(warn_msg)
        
        return cls(
            BOT_TOKEN=BOT_TOKEN,
            API_TOKEN=API_TOKEN,
            OWNER_ID=OWNER_ID,
            SUPABASE_URL=SUPABASE_URL,
            SUPABASE_KEY=SUPABASE_KEY,
            API_URL=API_URL,
            API_LANG=API_LANG,
            API_LIMIT=API_LIMIT,
            INITIAL_CHANNELS=INITIAL_CHANNELS
        )


# ══════════════════════════════════════════════════════════════
#                     GLOBAL CONFIG INSTANCE
# ══════════════════════════════════════════════════════════════

try:
    config = BotConfig.from_env()
except Exception as e:
    print(f"❌ Fatal config error: {e}")
    exit(1)
