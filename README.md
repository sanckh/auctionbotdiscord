# Discord Auction Bot

A Discord bot for running silent auctions with support for multiple currency denominations.

## Features

- Silent auctions with private bidding
- Support for multiple currency denominations (Mithril, Platinum, Gold, Silver)
- Automatic bid validation and currency conversion
- DM notifications for bid status and outbids
- Auction time extensions when outbid near the end

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Discord bot token:
```bash
# Windows
set DISCORD_TOKEN=your_token_here

# Linux/Mac
export DISCORD_TOKEN=your_token_here
```

3. Run the bot:
```bash
python auctionbot.py
```

## Usage

### Start an Auction
```
!auction "Item Name" 5m
```
Duration can be specified in minutes (m) or hours (h)

### Place a Bid
```
!bid 1m 50p 100g 500s
```

Supported currency formats:
- Mithril: `1m`, `1mith`, `1mithril`
- Platinum: `50p`, `50plat`, `50platinum`
- Gold: `100g`, `100gold`
- Silver: `500s`, `500sil`, `500silver`

## Project Structure

- `auctionbot.py` - Main entry point
- `bot/auction_bot.py` - Core bot class and message handling
- `cogs/auction_cog.py` - Auction commands and bid handling
- `utils/bid_parser.py` - Bid parsing utilities
- `utils/time_parser.py` - Time/duration parsing utilities
