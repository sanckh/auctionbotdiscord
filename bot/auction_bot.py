import discord
from discord.ext import commands, tasks
from datetime import datetime
import os

class AuctionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Enable member intent to get member objects
        super().__init__(command_prefix='!', intents=intents)
        self.active_auctions = {}
        self.results_channel_id = int(os.getenv('AUCTION_RESULTS_CHANNEL_ID', 0))

    async def setup_hook(self):
        """Initialize bot settings and start background tasks"""
        self.check_auctions.start()

    async def on_ready(self):
        """Called when the bot is ready to start receiving events"""
        print(f'Logged in as {self.user} (ID: {self.user.id})')

    @tasks.loop(seconds=1.0)
    async def check_auctions(self):
        """Check for ended auctions and process them"""
        current_time = datetime.now()
        ended_auctions = [(channel_id, auction) 
                         for channel_id, auction in list(self.active_auctions.items())
                         if current_time >= auction['end_time']]
        
        for channel_id, auction in ended_auctions:
            if channel_id in self.active_auctions:
                await self.process_auction_end(channel_id, auction)
                del self.active_auctions[channel_id]

    async def process_auction_end(self, channel_id: int, auction: dict):
        """Process an ended auction and announce results"""
        if channel := self.get_channel(channel_id):
            if not auction['bids']:
                await self.send_no_bids_message(channel, auction['item'])
                return
                
            winner_id, winning_bid = max(auction['bids'].items(), key=lambda x: x[1])
            if winner := channel.guild.get_member(winner_id):
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
        
        if results_channel := channel.guild.get_channel(self.results_channel_id):
            await self.send_formatted_message(results_channel, "🏁 AUCTION ENDED! 🏁", "31", content)

    async def send_winner_messages(self, channel, item: str, winner: discord.Member, winning_bid):
        """Send winner announcement messages"""
        # Public channel message (without bid amount)
        public_content = [
            f"📦 **Item:** `{item}`",
            f"👑 **Winner:** `{winner.display_name}`"
        ]
        await self.send_formatted_message(channel, "🎉 AUCTION ENDED! 🎉", "32", public_content)

        # Results channel message (with bid amount)
        if results_channel := channel.guild.get_channel(self.results_channel_id):
            results_content = public_content + [f"💰 **Winning Bid:** `{winning_bid}`"]
            await self.send_formatted_message(results_channel, "🎉 AUCTION ENDED! 🎉", "32", results_content)

        # Winner DM
        winner_content = [
            "You won the auction for:",
            f"📦 **Item:** `{item}`",
            f"💰 **Your winning bid:** `{winning_bid}`"
        ]
        await self.send_formatted_message(winner, "🎊 CONGRATULATIONS! 🎊", "33", winner_content)

    async def send_bid_confirmation(self, destination, item: str, bid_amount: int, denomination: str, channel_id: int):
        """Send bid confirmation message"""
        current_bids = self.active_auctions[channel_id]['bids'].values()
        is_highest = not current_bids or bid_amount > max(current_bids)
        
        confirm_content = [
            f"📦 **Item:** `{item}`",
            f"💰 **Your bid:** `{denomination}`",
            f"📊 **Current Status:** {'You are the highest bidder!' if is_highest else 'You have been outbid.'}"
        ]
        try:
            await self.send_formatted_message(destination, "✅ BID PLACED SUCCESSFULLY! ✅", "32", confirm_content)
        except discord.Forbidden:
            try:
                await destination.send("✅ Bid received!", delete_after=3)
            except:
                pass
