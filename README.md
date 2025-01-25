# Telegram Media Bot

This bot monitors a `links.txt` file for media URLs, downloads them, and forwards them to specified Telegram chats.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure the bot:
   - Replace `YOUR_API_ID` with your Telegram API ID
   - Replace `YOUR_API_HASH` with your Telegram API Hash
   - Replace `YOUR_PHONE_NUMBER` with your phone number
   - Update `DESTINATION_CHATS` with your target chat IDs

3. Create a `links.txt` file in the same directory as the script.

4. Run the bot:
```bash
python telegram_bot.py
```

## Features

- Monitors `links.txt` for new URLs
- Rate limiting to avoid Telegram restrictions
- Logging to both file and console
- Queue system for media processing
- Automatic retry on failures
- Duplicate URL detection

## Usage

1. Add URLs to `links.txt`, one per line
2. The bot will automatically process new URLs
3. Media will be sent to all configured destination chats
4. Check `bot.log` for detailed operation logs