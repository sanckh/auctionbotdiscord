import discord
from discord.ext import commands
from datetime import datetime, timedelta
from ..utils.bid_parser import parse_bid
from ..utils.time_parser import parse_duration

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
    async def place_bid(self, ctx, *, bid: str):
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

        # Validate bid format and parse amount
        if not (result := parse_bid(bid)):
            error_content = [
                "❌ **Invalid bid format!**",
                "",
                "**Correct formats:**",
                "• Mithril: `1m` or `1mith` or `1mithril`",
                "• Platinum: `50p` or `50plat` or `50platinum`",
                "• Gold: `100g` or `100gold`",
                "• Silver: `500s` or `500sil` or `500silver`",
                "",
                "**Mix currencies (must be in this order):**",
                "• `!bid 1m 50p 100g 500s`",
                "",
                "**Common mistakes:**",
                "• Wrong order (e.g., `!bid 100g 1m`)",
                "• Invalid currency",
                "• Missing amount (e.g., `!bid m`)",
                "• Extra spaces or symbols"
            ]
            await self.bot.send_formatted_message(ctx.author, "❌ INCORRECT BID FORMAT! ❌", "31", error_content)
            return

        bid_amount, denomination = result

        # Check if this is the highest bid before adding it
        current_bids = auction['bids'].values()
        is_highest = not current_bids or bid_amount > max(current_bids)

        # Get current highest bidder before updating
        current_highest_bidder = None
        if auction['bids']:
            current_highest_bidder = max(auction['bids'].items(), key=lambda x: x[1])[0]

        # Update bid and send confirmation
        auction['bids'][ctx.author.id] = bid_amount
        
        # Send confirmation to the bidder
        confirm_content = [
            f"📦 **Item:** `{auction['item']}`",
            f"💰 **Your bid:** `{denomination}`",
            f"📊 **Current Status:** {'You are the highest bidder!' if is_highest else 'You have been outbid.'}"
        ]
        await self.bot.send_formatted_message(ctx.author, "✅ BID PLACED SUCCESSFULLY! ✅", "32", confirm_content)
        
        # Notify previous highest bidder if they were outbid
        if is_highest and current_highest_bidder and current_highest_bidder != ctx.author.id:
            if bidder := ctx.guild.get_member(current_highest_bidder):
                their_bid = auction['bids'][current_highest_bidder]
                outbid_content = [
                    f"📦 **Item:** `{auction['item']}`",
                    f"💰 **Your bid:** `{parse_bid(str(their_bid))[1]}`",
                    "📊 **Current Status:** You have been outbid!",
                    "",
                    "Place a new bid to stay in the auction!"
                ]
                try:
                    await self.bot.send_formatted_message(bidder, "⚠️ OUTBID ALERT! ⚠️", "31", outbid_content)
                except discord.Forbidden:
                    print(f"Could not send DM to {bidder.name} (ID: {bidder.id}) - DMs may be disabled")
                    # Try to notify in channel that user needs to enable DMs
                    try:
                        await ctx.channel.send(f"⚠️ {bidder.mention} I couldn't send you a DM! Please enable DMs to receive outbid notifications.", delete_after=10)
                    except:
                        pass
                except Exception as e:
                    print(f"Error sending DM to {bidder.name} (ID: {bidder.id}): {str(e)}")
