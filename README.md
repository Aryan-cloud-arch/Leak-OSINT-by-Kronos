# 🔍 LeakOSINT Telegram Bot

A Telegram bot for searching leaked databases with **Force Join** channel verification system.

## ✨ Features

- 🔐 **Force Join System** - Users must join required channels to use the bot
- 📢 **Multiple Channels** - Support for public, private, and join-request channels
- 🛠️ **Dynamic Management** - Add/remove channels via commands
- 💾 **Supabase Storage** - Persistent storage for users and channels
- ⚡ **Environment Config** - Most settings via `.env` file
- 👑 **Admin Controls** - Full admin panel with stats and broadcast

## 📋 Requirements

- Python 3.8+
- Telegram Bot Token (from @BotFather)
- LeakOSINT API Token
- Supabase Account (free tier works)

## 🚀 Quick Setup

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/leakosint-bot.git
cd leakosint-bot
pip install -r requirements.txt
```

### 2. Setup Supabase

1. Create account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to **SQL Editor** > **New Query**
4. Paste contents of `supabase_setup.sql` and run
5. Go to **Settings** > **API** to get your URL and anon key

### 3. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your values
```

Fill in:
- `BOT_TOKEN` - From @BotFather
- `API_TOKEN` - Your LeakOSINT API token
- `ADMIN_ID` - Your Telegram user ID (get from @userinfobot)
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon/public key

### 4. Run the Bot

```bash
python bot.py
```

## 📖 Commands

### Admin Commands

| Command | Description |
|---------|-------------|
| `/addchannel @channel` | Add a required channel |
| `/removechannel` | Remove a channel (shows list) |
| `/channels` | List all required channels |
| `/users` | View all bot users |
| `/stats` | Bot statistics |
| `/broadcast <message>` | Send message to all users |
| `/help` | Show help |

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help |

## 📢 Adding Channels

### Via Command (Recommended)

```
/addchannel @your_channel
/addchannel -1001234567890
```

### Via Environment Variable

In `.env`:
```
REQUIRED_CHANNELS=@channel1,@channel2,-1001234567890
```

## ⚠️ Important Notes

1. **Bot must be admin** in all required channels
2. Bot needs these admin permissions:
   - Read messages
   - Invite users via link (for private channels)
3. For **private channels**, use the channel ID (starts with `-100`)
4. For **join-request channels**, bot will check pending requests

## 🔧 Channel Types Support

| Type | How to Add | Notes |
|------|------------|-------|
| Public | `@channel_username` | Bot needs to be member |
| Private | `-100xxxxxxxxxx` | Bot must be admin |
| Join Request | `-100xxxxxxxxxx` | Bot must be admin to check requests |

## 📁 Project Structure

```
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── supabase_setup.sql  # Database setup SQL
└── README.md           # This file
```

## 🐛 Troubleshooting

### "Bot is not admin in channel"
Make sure the bot is added as admin in the channel with proper permissions.

### "Could not find channel"
- Check channel username/ID is correct
- Ensure bot is a member of the channel
- For private channels, use the numeric ID

### "Missing environment variables"
Copy `.env.example` to `.env` and fill in all required values.

## 📄 License

MIT License - feel free to modify and use!

## 🤝 Support

For issues or questions, contact: @your_support_username
