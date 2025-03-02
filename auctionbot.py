import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
AUCTION_RESULTS_CHANNEL_ID = int(os.getenv('AUCTION_RESULTS_CHANNEL_ID', 0))

class AuctionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.active_auctions = {}

    async def setup_hook(self):
        """Initialize bot settings and start background tasks"""
        await self.add_cog(Auction(self))  # Load cog during setup
        self.check_auctions.start()

    async def on_ready(self):
        """Called when the bot is ready to start receiving events"""
        print(f"{self.user} has connected to Discord!")

    @tasks.loop(seconds=1)
    async def check_auctions(self):
        """Check for ended auctions and process them"""
        current_time = datetime.now()
        ended_auctions = [(channel_id, auction) 
                         for channel_id, auction in list(self.active_auctions.items())  # Create a copy to avoid modification during iteration
                         if current_time >= auction['end_time']]
        
        for channel_id, auction in ended_auctions:
            if channel_id in self.active_auctions:  # Double check it's still active
                await self.process_auction_end(channel_id, auction)
                del self.active_auctions[channel_id]

    async def process_auction_end(self, channel_id: int, auction: dict):
        """Process an ended auction and announce results"""
        channel = self.get_channel(channel_id)
        if not channel:
            return

        if not auction['bids']:
            await self.send_no_bids_message(channel, auction['item'])
            return

        winner_id, winning_bid = max(auction['bids'].items(), key=lambda x: x[1])
        winner = channel.guild.get_member(winner_id)
        if winner:
            await self.send_winner_messages(channel, auction['item'], winner, winning_bid)

    async def send_formatted_message(self, destination, header: str, header_color: str, content: list, footer: list = None):
        """Send a formatted message with consistent styling"""
        message = [
            "```ansi",
            f"\u001b[1;{header_color}m{header}\u001b[0m",
            "```",
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        message.extend(content)
        message.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        if footer:
            message.extend(footer)
        
        try:
            await destination.send('\n'.join(message))
        except discord.Forbidden:
            pass

    async def send_no_bids_message(self, channel, item: str):
        """Send message for auction with no bids"""
        content = [
            f"📦 **Item:** `{item}`",
            "❌ **Result:** No bids were placed."
        ]
        await self.send_formatted_message(channel, "🏁 AUCTION ENDED! 🏁", "31", content)
        
        if results_channel := channel.guild.get_channel(AUCTION_RESULTS_CHANNEL_ID):
            await self.send_formatted_message(results_channel, "🏁 AUCTION ENDED! 🏁", "31", content)

    async def send_winner_messages(self, channel, item: str, winner: discord.Member, winning_bid: float):
        """Send winner announcement messages"""
        # Public channel message (without bid amount)
        public_content = [
            f"📦 **Item:** `{item}`",
            f"👑 **Winner:** `{winner.display_name}`"
        ]
        await self.send_formatted_message(channel, "🎉 AUCTION ENDED! 🎉", "32", public_content)

        # Results channel message (with bid amount)
        if results_channel := channel.guild.get_channel(AUCTION_RESULTS_CHANNEL_ID):
            results_content = public_content + [f"💰 **Winning Bid:** `{winning_bid:.2f}`"]
            await self.send_formatted_message(results_channel, "🎉 AUCTION ENDED! 🎉", "32", results_content)

        # Winner DM
        winner_content = [
            "You won the auction for:",
            f"📦 **Item:** `{item}`",
            f"💰 **Your winning bid:** `{winning_bid:.2f}`"
        ]
        await self.send_formatted_message(winner, "🎊 CONGRATULATIONS! 🎊", "33", winner_content)

    async def send_bid_confirmation(self, destination, item: str, bid_amount: float, denomination: str):
        """Send bid confirmation message"""
        confirm_content = [
            f"📦 **Item:** `{item}`",
            f"💰 **Your bid:** `{bid_amount:.2f}{denomination}`",
            f"📊 **Current Status:** {'You are the highest bidder!' if bid_amount > max(self.active_auctions[destination.channel.id]['bids'].values()) else 'You have been outbid.'}"
        ]
        try:
            await self.send_formatted_message(destination, "✅ BID PLACED SUCCESSFULLY! ✅", "32", confirm_content)
        except discord.Forbidden:
            try:
                await destination.send("✅ Bid received!", delete_after=3)
            except:
                pass

class Auction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        """Delete any messages that look like bids to maintain auction privacy"""
        if message.author.bot or message.channel.id not in self.bot.active_auctions:
            return

        content = message.content.lower()
        if content.startswith('!bid') or any(x in content for x in ['p ', 'g ', 's ', 'm ', 'plat', 'gold', 'silver', 'mith']):
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

    @commands.command(name='auction')
    async def start_auction(self, ctx, item: str, duration: str):
        """Start a new auction"""
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        if ctx.channel.id in self.bot.active_auctions:
            await ctx.author.send("❌ An auction is already running in this channel!")
            return

        if not (duration_delta := parse_duration(duration)):
            await ctx.author.send("❌ Invalid duration format. Use: `5m` for 5 minutes or `2h` for 2 hours")
            return

        end_time = datetime.now() + max(duration_delta, timedelta(seconds=10))
        
        self.bot.active_auctions[ctx.channel.id] = {
            'item': item,
            'end_time': end_time,
            'bids': {}
        }

        content = [
            f"📦 **Item:** `{item}`",
            f"⏳ **Duration:** `{duration}`",
            "",
            "**💰 How to Bid:**",
            "Type `!bid` followed by your amount:",
            "",
            "**Mithril**",
            "• `!bid 1m` or `1mith` or `1mithril`",
            "",
            "**Platinum**",
            "• `!bid 50p` or `50plat` or `50platinum`",
            "",
            "**Gold**",
            "• `!bid 100g` or `100gold`",
            "",
            "**Silver**",
            "• `!bid 500s` or `500sil` or `500silver`",
            "",
            "**Mix Currencies:**",
            "• `!bid 1m 50p 100g 500s`",
            "",
            "**🔔 Rules:**",
            "• Silent auction - bids are private",
            "• Bid confirmations sent via DM",
            "• 15s extension when outbid"
        ]
        
        await self.bot.send_formatted_message(ctx, "🔨 SILENT AUCTION STARTED! 🔨", "33", content)

    @commands.command(name='bid')
    async def place_bid(self, ctx, bid: str):
        """Place a bid in the current auction"""
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        if ctx.channel.id not in self.bot.active_auctions:
            await ctx.author.send("❌ No active auction in this channel!")
            return

        auction = self.bot.active_auctions[ctx.channel.id]
        if datetime.now() >= auction['end_time']:
            await ctx.author.send("❌ This auction has ended!")
            return

        if not (bid_amount, denomination := parse_bid(bid)):
            await ctx.author.send("❌ Invalid bid format. Check auction post for valid formats.")
            return

        current_bid = auction['bids'].get(ctx.author.id, 0)
        if bid_amount <= current_bid:
            await ctx.author.send("❌ Your new bid must be higher than your previous bid!")
            return

        highest_bid = max(auction['bids'].values()) if auction['bids'] else 0
        if bid_amount <= highest_bid:
            await ctx.author.send("❌ Your bid must be higher than the current highest bid!")
            return

        # Check for auction extension
        time_remaining = auction['end_time'] - datetime.now()
        current_highest_bidder = max(auction['bids'].items(), key=lambda x: x[1])[0] if auction['bids'] else None
        
        if time_remaining.total_seconds() <= 15 and current_highest_bidder and current_highest_bidder != ctx.author.id:
            auction['end_time'] = datetime.now() + timedelta(seconds=15)
            extension_content = [
                f"📦 **Item:** `{auction['item']}`",
                "⏳ **Extension:** `15 seconds`"
            ]
            
            if previous_bidder := ctx.guild.get_member(current_highest_bidder):
                await self.bot.send_formatted_message(previous_bidder, "⏰ AUCTION EXTENDED! ⏰", "33", extension_content)
            await self.bot.send_formatted_message(ctx.author, "⏰ AUCTION EXTENDED! ⏰", "33", extension_content)

        # Update bid and send confirmation
        auction['bids'][ctx.author.id] = bid_amount
        await self.bot.send_bid_confirmation(ctx.author, auction['item'], bid_amount, denomination)

def parse_bid(bid_str: str) -> tuple[float, str]:
    """Parse bid string into total amount and appropriate denomination"""
    bid_str = bid_str.lower()
    # Handle full names and abbreviations
    replacements = {
        'mithril': 'm', 'mith': 'm',
        'platinum': 'p', 'plat': 'p',
        'gold': 'g',
        'silver': 's', 'sil': 's'
    }
    for full, short in replacements.items():
        bid_str = bid_str.replace(full, short)
    
    total_amount = 0
    for part in bid_str.split():
        if not (match := re.match(r'^(\d+(?:\.\d+)?)([mgps])$', part)):
            return None, None
            
        amount, unit = match.groups()
        amount = float(amount)
        
        multipliers = {
            'm': 1000000,
            'p': 10000,
            'g': 100,
            's': 1
        }
        total_amount += amount * multipliers[unit]
    
    # Convert to most appropriate denomination with decimals
    if total_amount >= 1000000:
        return total_amount / 1000000, 'm'
    elif total_amount >= 10000:
        return total_amount / 10000, 'p'
    elif total_amount >= 100:
        return total_amount / 100, 'g'
    else:
        return float(total_amount), 's'

def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string into timedelta"""
    if match := re.match(r'^(\d+)([mh])$', duration_str.lower()):
        amount, unit = match.groups()
        amount = int(amount)
        return timedelta(minutes=amount) if unit == 'm' else timedelta(hours=amount)
    return None

def main():
    """Initialize and run the bot"""
    bot = AuctionBot()
    bot.run(TOKEN)

if __name__ == "__main__":
    main()